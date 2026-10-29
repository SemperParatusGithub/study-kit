"""`studykit ingest`: the Python steps of /register-new-subject (docs/architecture.md §5.4).

- `scan <folder>` (step 0) inventories a folder of lecture material without changing it:
  every PDF with its pages, text-layer share, visual and scanned pages, a guessed kind
  (from the file name, else the cover page, else the page shape) and a proposed document
  id; duplicates by sha256; office files and images that need exporting to PDF first; and
  dates near "Klausur"/"exam" in the text that may be the exam date.
- `init <folder> <course>` (step 2) copies the PDFs into `courses/<id>/sources/raw/<doc>.pdf`
  (the folder is only read), writes `sources/manifest.yaml` (`model.SourceManifest`, with
  the round-1 answers) and, for a new course, a draft `course.yaml` with the one
  placeholder topic `draft`; both must pass their schema before the command succeeds.
- `extract <course>` (step 3) writes each page's text to `sources/text/<doc>/p0001.txt`
  with `sources/text/<doc>/index.json` (per page: characters, garbled share, graphics
  share, visual and scanned flags), and the chunk plan `sources/chunks.yaml`
  (`model.ChunkPlan`): at most 20 pages per chunk, never across documents, past exams and
  their solutions whole.
- `add <course> <file|folder>` (/add-material) is init's copy for a course that exists,
  followed by extract: only new or changed documents are copied and read again.
- `round2 <course>` records the answers of step 6 in the manifest.

Everything is idempotent: a document whose sha256 is unchanged is neither copied nor
extracted again, and its chunks keep their ids. A file with the relative path of a known
document but other contents replaces that document (`updated`), so its chunks are planned
again and their notes become stale (`studykit pipeline status`).

Findings use the SK-INGEST codes (docs/content-format/errors.md) at the file they concern.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import os
import re
import shutil
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from studykit import content, model, tools, yamlio
from studykit.findings import Finding

MAX_CHUNK_PAGES = 20
MAX_ID = 48  # document ids longer than this are cut at a word boundary
TEXT_CHARS = 20  # fewer non-space characters: the page has no text layer
VISUAL_CHARS = 200  # fewer: the page is mostly a picture
GARBLED_SHARE = 0.10
GRAPHICS_SHARE = 0.25
DRAWING_SHAPES = 30  # this many drawn shapes make a figure (a circuit has 40 to 50)

OFFICE = {".ppt", ".pptx", ".pps", ".ppsx", ".key", ".odp", ".doc", ".docx", ".odt"}
OFFICE |= {".pages", ".rtf", ".xls", ".xlsx", ".ods", ".numbers"}
IMAGES = {".png", ".jpg", ".jpeg", ".heic", ".tif", ".tiff", ".gif", ".bmp", ".webp"}
ROUND1_FORMATS = ("written", "written-mc", "mc", "oral")

# Kind rules over a normalised name or cover text (ASCII, lower case, umlauts spelled out),
# first match wins.
_EXAM = r"klausur|pruefung|\bexams?\b|probeklausur|midterm|\bfinal\b"
_SOL = r"loesung|\blsg\b|solution|musterloesung"
KIND_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("exam-solutions", re.compile(rf"({_EXAM}).*({_SOL})|({_SOL}).*({_EXAM})")),
    ("exam", re.compile(_EXAM)),
    ("solutions", re.compile(_SOL)),
    (
        "exercises",
        re.compile(
            r"uebung|exercise|aufgabe|\bblatt|tutorium|tutorial|sheet|problem ?set|hausaufgabe"
            r"|homework|assignment"
        ),
    ),
    ("slides", re.compile(r"folien|slides|praesentation|presentation")),
    ("script", re.compile(r"skript|script|lecture ?notes|\bnotes\b|mitschrift|kapitel|chapter")),
    ("slides", re.compile(r"vorlesung|\bvl ?[0-9]|\bvl\b|lecture")),
]
DE_WORDS = {"der", "die", "das", "und", "ist", "mit", "für", "nicht", "eine", "wird", "von", "den"}
EN_WORDS = {"the", "and", "is", "of", "with", "for", "not", "are", "from", "this", "which", "be"}
DATE_DE = re.compile(r"\b([0-3]?[0-9])\.\s?([01]?[0-9])\.\s?(20[0-9]{2})\b")
DATE_ISO = re.compile(r"\b(20[0-9]{2})-([01][0-9])-([0-3][0-9])\b")
EXAM_WORDS = re.compile(r"klausur|prüfung|pruefung|exam|termin", re.IGNORECASE)


class IngestError(Exception):
    """A usage problem (exit code 2): unknown course, bad flag combination."""


# --- small helpers ----------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def ascii_fold(text: str) -> str:
    """Lower case ASCII with German umlauts spelled out (ä -> ae, ß -> ss)."""
    text = text.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(a, b)
    text = unicodedata.normalize("NFKD", text)
    return text.encode("ascii", "ignore").decode()


def doc_id(name: str, taken: Iterable[str] = ()) -> str:
    """A kebab-case document id from a file name, unique among `taken`."""
    stem = re.sub(r"[^a-z0-9]+", "-", ascii_fold(Path(name).stem)).strip("-")
    if len(stem) > MAX_ID:  # cut at a word boundary when there is one
        cut = stem.rfind("-", 0, MAX_ID + 1)
        stem = stem[: cut if cut >= 12 else MAX_ID].strip("-")
    stem = stem or "dokument"
    if not re.fullmatch(model.PATTERNS["doc"], stem):
        stem = "doc-" + stem
    used = set(taken)
    candidate, n = stem, 2
    while candidate in used:
        candidate, n = f"{stem}-{n}", n + 1
    return candidate


def title_of(name: str) -> str:
    stem = Path(name).stem.replace("_", " ").strip()
    stem = "".join(ch for ch in stem if ch.isprintable())
    return re.sub(r"\s+", " ", stem) or Path(name).name


def guess_kind(name: str, cover: str, landscape: bool) -> tuple[str, str]:
    """(kind, where it came from): the file name, else the cover page, else the page shape."""
    text = re.sub(r"[_\-.]+", " ", ascii_fold(Path(name).stem))
    for kind, rx in KIND_RULES:
        if rx.search(text):
            return kind, "filename"
    cover_text = re.sub(r"\s+", " ", ascii_fold(cover))[:500]
    for kind, rx in KIND_RULES:
        if rx.search(cover_text):
            return kind, "cover"
    if landscape:
        return "slides", "layout"
    return "other", "none"


def guess_lang(texts: Iterable[str]) -> str | None:
    de = en = 0
    for text in texts:
        for word in re.findall(r"[a-zäöüß]+", text.lower()):
            de += word in DE_WORDS
            en += word in EN_WORDS
    if de == en == 0:
        return None
    return "de" if de >= en else "en"


def _q(text: str) -> str:
    """A single-quoted YAML scalar (the restricted loader's preferred form, §2.1)."""
    return "'" + str(text).replace("'", "''") + "'"


def _v(value: Any) -> str:
    """A YAML scalar: plain for ids, numbers, booleans, dates and null; quoted otherwise."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, dt.date):
        return value.isoformat()
    text = str(value)
    if re.fullmatch(r"[a-z][a-z0-9-]*", text) and text not in {"null", "true", "false"}:
        return text
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text):
        return text
    return _q(text)


def _flow(data: dict[str, Any]) -> str:
    parts = []
    for key, value in data.items():
        if isinstance(value, list):
            parts.append(f"{key}: [" + ", ".join(_v(v) for v in value) + "]")
        else:
            parts.append(f"{key}: {_v(value)}")
    return "{" + ", ".join(parts) + "}"


def _schema_ref(path: Path, name: str) -> str | None:
    repo = tools.repo_root().resolve()
    try:
        path.resolve().relative_to(repo)
    except ValueError:
        return None
    return Path(os.path.relpath(repo / "schemas" / name, path.parent.resolve())).as_posix()


def _write(path: Path, text: str) -> bool:
    """Write atomically, only when the content changed; True when it was written."""
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
    return True


def _finding(path: Path | str, code: str, message: str, fix: str, severity="error") -> Finding:
    shown = content.display_path(Path(path)) if isinstance(path, Path) else path
    return Finding(shown, 1, 1, code, message, fix, severity)  # type: ignore[arg-type]


# --- PDF analysis -------------------------------------------------------------------------------


@dataclass
class Page:
    n: int
    chars: int  # non-space characters of the text layer
    garbled: float  # share of those that are replacement, private-use or control characters
    graphics: float  # share of the page covered by images
    shapes: int  # drawn shapes (see _graphics)
    landscape: bool
    text: str = ""

    @property
    def scanned(self) -> bool:
        return self.chars < TEXT_CHARS

    @property
    def reasons(self) -> list[str]:
        out = []
        if self.scanned:
            out.append("no text layer")
        elif self.chars < VISUAL_CHARS:
            out.append(f"{self.chars} characters")
        if self.garbled >= GARBLED_SHARE and not self.scanned:
            out.append(f"{self.garbled:.0%} garbled glyphs")
        if self.graphics >= GRAPHICS_SHARE and not self.scanned:
            out.append(f"images over {self.graphics:.0%} of the page")
        if self.shapes >= DRAWING_SHAPES:
            out.append(f"a drawing ({self.shapes} shapes)")
        return out

    @property
    def visual(self) -> bool:
        return bool(self.reasons)

    def info(self) -> dict[str, Any]:
        return {
            "n": self.n,
            "chars": self.chars,
            "garbled": round(self.garbled, 3),
            "graphics": round(self.graphics, 3),
            "shapes": self.shapes,
            "landscape": self.landscape,
            "visual": self.visual,
            "scanned": self.scanned,
            "reasons": self.reasons,
        }


def _garbled(text: str) -> float:
    chars = [ch for ch in text if not ch.isspace()]
    if not chars:
        return 0.0
    bad = sum(
        1 for ch in chars if ch == "�" or "" <= ch <= "" or unicodedata.category(ch) == "Cc"
    )
    return bad / len(chars)


def _graphics(page: Any, width: float, height: float) -> tuple[float, int]:
    """(share of the page covered by images, number of drawn shapes).

    A shape is a path at least 2 pt wide and high: resistors, arrowheads, axes ticks and
    curves count, while rules, fraction bars and table lines (thin in one direction) do
    not, so a page of formulas is not mistaken for a drawing.
    """
    import pypdfium2.raw as pdfium_c

    area = width * height
    image_area, shapes = 0.0, 0
    for obj in page.get_objects(max_depth=4):
        if obj.type not in (pdfium_c.FPDF_PAGEOBJ_IMAGE, pdfium_c.FPDF_PAGEOBJ_PATH):
            continue
        try:
            left, bottom, right, top = obj.get_bounds()
        except Exception:  # an object without bounds draws nothing we can measure
            continue
        left, right = max(0.0, left), min(width, right)
        bottom, top = max(0.0, bottom), min(height, top)
        if right <= left or top <= bottom:
            continue
        if obj.type == pdfium_c.FPDF_PAGEOBJ_IMAGE:
            image_area += (right - left) * (top - bottom)
        elif right - left >= 2 and top - bottom >= 2:
            shapes += 1
    return (min(1.0, image_area / area) if area > 0 else 0.0), shapes


@dataclass
class PdfInfo:
    pages: list[Page] = field(default_factory=list)
    error: str | None = None

    @property
    def text_share(self) -> float:
        if not self.pages:
            return 0.0
        return sum(not p.scanned for p in self.pages) / len(self.pages)

    @property
    def landscape(self) -> bool:
        return sum(p.landscape for p in self.pages) * 2 > len(self.pages)


def analyse_pdf(path: Path, *, keep_text: bool = False) -> PdfInfo:
    """Pages of a PDF with their text-layer and graphics measures (pypdfium2)."""
    import pypdfium2 as pdfium

    try:
        doc = pdfium.PdfDocument(str(path))
    except Exception as exc:  # encrypted, damaged or not a PDF at all
        return PdfInfo(error=str(exc) or type(exc).__name__)
    info = PdfInfo()
    try:
        for i in range(len(doc)):
            page = doc[i]
            try:
                width, height = page.get_size()
                textpage = page.get_textpage()
                try:
                    text = textpage.get_text_range()
                finally:
                    textpage.close()
                text = text.replace("\r\n", "\n").replace("\r", "\n")
                graphics, shapes = _graphics(page, width, height)
                info.pages.append(
                    Page(
                        n=i + 1,
                        chars=sum(not ch.isspace() for ch in text),
                        garbled=_garbled(text),
                        graphics=graphics,
                        shapes=shapes,
                        landscape=width > height,
                        text=text if keep_text or i == 0 else "",
                    )
                )
            finally:
                page.close()
    except Exception as exc:
        info.error = str(exc) or type(exc).__name__
    finally:
        doc.close()
    if not info.pages and info.error is None:
        info.error = "the PDF has no pages"
    return info


# --- manifest -------------------------------------------------------------------------------


def manifest_path(course: Path) -> Path:
    return course / "sources" / "manifest.yaml"


def chunks_path(course: Path) -> Path:
    return course / "sources" / "chunks.yaml"


def text_dir(course: Path, doc: str) -> Path:
    return course / "sources" / "text" / doc


def page_file(course: Path, doc: str, n: int) -> Path:
    return text_dir(course, doc) / f"p{n:04d}.txt"


def vision_file(course: Path, doc: str, n: int) -> Path:
    """Where the ingester writes its transcription of a scanned or visual page."""
    return text_dir(course, doc) / f"p{n:04d}.vision.md"


def read_yaml_model(path: Path, cls: type[model.Strict]) -> tuple[Any, list[Finding]]:
    """(model or None, findings) for one YAML file; (None, []) when it does not exist."""
    if not path.is_file():
        return None, []
    doc = yamlio.load(path.read_text(encoding="utf-8"), path=content.display_path(path))
    if not doc.ok:
        return None, [f for f in doc.findings if f.is_error]
    try:
        return cls.model_validate(doc.data if doc.data is not None else {}), []
    except ValidationError as exc:
        return None, content.schema_findings(doc, exc)


def read_manifest(course: Path) -> tuple[model.SourceManifest | None, list[Finding]]:
    return read_yaml_model(manifest_path(course), model.SourceManifest)


def render_manifest(m: model.SourceManifest, path: Path) -> str:
    lines = []
    ref = _schema_ref(path, "manifest.schema.json")
    if ref:
        lines.append(f"# yaml-language-server: $schema={ref}")
    lines += [
        "# Written by `studykit ingest`; the source PDFs are in sources/raw/ (§5.4).",
        "schema: 1",
        f"course: {m.course}",
    ]
    if m.folder:
        lines.append(f"folder: {_q(m.folder)}")
    answers = {
        name: getattr(m.answers, name)
        for name in ("round1", "round2")
        if getattr(m.answers, name) is not None
    }
    if answers:
        lines.append("answers:")
        for name, value in answers.items():
            lines.append(f"  {name}: {_flow(value.model_dump(mode='json'))}")
    if not m.documents:
        lines.append("documents: []")
    else:
        lines.append("documents:")
        for d in m.documents:
            data = d.model_dump(mode="json", exclude_none=True)
            data["text_share"] = round(d.text_share, 3)
            first = True
            for key, value in data.items():
                lines.append(f"{'  - ' if first else '    '}{key}: {_v(value)}")
                first = False
    if m.skipped:
        lines.append("skipped:")
        for s in m.skipped:
            lines.append(f"  - {_flow(s.model_dump(mode='json', exclude_none=True))}")
    return "\n".join(lines) + "\n"


def write_manifest(course: Path, m: model.SourceManifest) -> bool:
    path = manifest_path(course)
    text = render_manifest(m, path)
    # the gate of §5.4 step 2: what is written must read back and validate
    model.SourceManifest.model_validate(yamlio.safe_load(text))
    return _write(path, text)


# --- scan --------------------------------------------------------------------------------------


@dataclass
class Candidate:
    """One PDF of the scanned folder."""

    path: Path
    origin: str
    sha256: str
    bytes: int
    info: PdfInfo
    id: str = ""
    kind: str = "other"
    kind_from: str = "none"
    status: str = "new"  # new | known | changed | duplicate
    duplicate_of: str | None = None

    def row(self) -> dict[str, Any]:
        pages = self.info.pages
        return {
            "origin": self.origin,
            "id": self.id,
            "title": title_of(self.origin),
            "status": self.status,
            "pages": len(pages),
            "bytes": self.bytes,
            "sha256": self.sha256,
            "kind": self.kind,
            "kind_from": self.kind_from,
            "uncertain": self.kind_from not in ("filename", "user"),
            "text_share": round(self.info.text_share, 3),
            "landscape": self.info.landscape,
            "visual_pages": [p.n for p in pages if p.visual],
            "scanned_pages": [p.n for p in pages if p.scanned],
            "chunks": len(plan_ranges(len(pages), self.kind)),
        }


@dataclass
class Scan:
    folder: Path
    candidates: list[Candidate] = field(default_factory=list)
    skipped: list[model.SkippedFile] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    lang: str | None = None
    exam_dates: list[dict[str, Any]] = field(default_factory=list)

    @property
    def documents(self) -> list[Candidate]:
        return [c for c in self.candidates if c.status != "duplicate"]

    def to_json(self) -> dict[str, Any]:
        docs = [c.row() for c in self.documents]
        return {
            "folder": str(self.folder),
            "documents": docs,
            "skipped": [s.model_dump(mode="json", exclude_none=True) for s in self.skipped],
            "totals": {
                "pdfs": len(docs),
                "pages": sum(d["pages"] for d in docs),
                "visual_pages": sum(len(d["visual_pages"]) for d in docs),
                "scanned_pages": sum(len(d["scanned_pages"]) for d in docs),
                "chunks": sum(d["chunks"] for d in docs),
                "uncertain_kinds": [d["id"] for d in docs if d["uncertain"]],
                "past_exams": [d["id"] for d in docs if d["kind"] in model.PAST_EXAM_KINDS],
            },
            "lang": self.lang,
            "exam_dates": self.exam_dates,
            "findings": [f.to_dict() for f in self.findings],
        }


def _files(folder: Path) -> list[Path]:
    if folder.is_file():
        return [folder]
    out = []
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        out += [Path(dirpath) / f for f in sorted(filenames) if not f.startswith(".")]
    return out


def _exam_dates(cands: list[Candidate], today: dt.date) -> list[dict[str, Any]]:
    """Future dates near an exam word: candidates for the exam date (round 1)."""
    found: dict[str, dict[str, Any]] = {}
    for c in cands:
        for page in c.info.pages:
            text = page.text
            for m in [*DATE_DE.finditer(text), *DATE_ISO.finditer(text)]:
                try:
                    if m.re is DATE_ISO:
                        day = dt.date(int(m[1]), int(m[2]), int(m[3]))
                    else:
                        day = dt.date(int(m[3]), int(m[2]), int(m[1]))
                except ValueError:
                    continue
                context = text[max(0, m.start() - 80) : m.end() + 40]
                if day < today or not EXAM_WORDS.search(context):
                    continue
                key = day.isoformat()
                found.setdefault(
                    key,
                    {
                        "date": key,
                        "doc": c.id,
                        "page": page.n,
                        "context": re.sub(r"\s+", " ", context).strip(),
                    },
                )
    return [found[k] for k in sorted(found)]


def scan(
    folder: Path,
    *,
    manifest: model.SourceManifest | None = None,
    kinds: dict[str, str] | None = None,
    today: dt.date | None = None,
) -> Scan:
    """Inventory `folder` (or one file); never writes. `manifest`: the course's sources, to
    tell known, changed and new documents apart; `kinds`: kinds the user decided, by id or
    by origin."""
    today = today or dt.date.today()
    folder = folder.resolve()
    result = Scan(folder)
    if not folder.exists():
        result.findings.append(
            _finding(
                folder,
                "SK-INGEST-FOLDER",
                "the folder does not exist",
                "give the folder that holds the lecture PDFs",
            )
        )
        return result
    base = folder.parent if folder.is_file() else folder
    known = {d.sha256: d for d in manifest.documents} if manifest else {}
    by_origin = {d.origin: d for d in manifest.documents} if manifest else {}
    taken = {d.id for d in manifest.documents} if manifest else set()
    seen: dict[str, Candidate] = {}
    texts: list[str] = []
    for path in _files(folder):
        origin = path.relative_to(base).as_posix()
        suffix = path.suffix.lower()
        if suffix != ".pdf":
            if suffix in OFFICE:
                reason, note = "unsupported", "export it as PDF and add the PDF"
            elif suffix in IMAGES:
                reason, note = "image", "combine the photos or scans into one PDF and add that"
            else:
                reason, note = "ignored", "not a PDF"
            result.skipped.append(model.SkippedFile(origin=origin, reason=reason, note=note))
            if reason != "ignored":
                result.findings.append(
                    _finding(
                        path,
                        "SK-INGEST-UNSUPPORTED",
                        f"{path.suffix} files are not read",
                        note,
                        "warning",
                    )
                )
            continue
        digest = sha256_file(path)
        if digest in seen:
            first = seen[digest]
            result.candidates.append(
                Candidate(
                    path,
                    origin,
                    digest,
                    path.stat().st_size,
                    first.info,
                    id=first.id,
                    status="duplicate",
                    duplicate_of=first.id,
                )
            )
            result.skipped.append(
                model.SkippedFile(
                    origin=origin,
                    reason="duplicate",
                    note=f"same content as {first.origin}",
                    duplicate_of=first.id,
                )
            )
            result.findings.append(
                _finding(
                    path,
                    "SK-INGEST-DUPLICATE",
                    f"same content as {first.origin}",
                    "nothing to do: it is read once",
                    "warning",
                )
            )
            continue
        info = analyse_pdf(path, keep_text=True)
        if info.error:
            result.skipped.append(
                model.SkippedFile(origin=origin, reason="unreadable", note=info.error[:200])
            )
            result.findings.append(
                _finding(
                    path,
                    "SK-INGEST-PDF",
                    f"pypdfium2 cannot read it: {info.error[:200]}",
                    "remove the password or re-export the PDF, then add it again",
                    "warning",
                )
            )
            continue
        cand = Candidate(path, origin, digest, path.stat().st_size, info)
        if digest in known:
            old = known[digest]
            cand.id, cand.kind, cand.kind_from, cand.status = (
                old.id,
                old.kind,
                old.kind_from,
                "known",
            )
        elif origin in by_origin:
            old = by_origin[origin]
            cand.id, cand.kind, cand.kind_from, cand.status = (
                old.id,
                old.kind,
                old.kind_from,
                "changed",
            )
        else:
            cand.id = doc_id(origin, taken)
            taken.add(cand.id)
            cover = info.pages[0].text if info.pages else ""
            cand.kind, cand.kind_from = guess_kind(origin, cover, info.landscape)
        if cand.status == "known" and digest in known and known[digest].origin != origin:
            cand.status = "duplicate"
            cand.duplicate_of = known[digest].id
            result.skipped.append(
                model.SkippedFile(
                    origin=origin,
                    reason="duplicate",
                    note=f"same content as {known[digest].origin}",
                    duplicate_of=known[digest].id,
                )
            )
            result.findings.append(
                _finding(
                    path,
                    "SK-INGEST-DUPLICATE",
                    f"same content as the course's {known[digest].id}",
                    "nothing to do: the course has it",
                    "warning",
                )
            )
        seen[digest] = cand
        result.candidates.append(cand)
        texts += [p.text for p in info.pages]
    for cand in result.documents:
        wanted = (kinds or {}).get(cand.id) or (kinds or {}).get(cand.origin)
        if wanted:
            cand.kind, cand.kind_from = wanted, "user"
    if not result.candidates:  # (duplicates of known documents are fine)
        result.findings.append(
            _finding(
                folder,
                "SK-INGEST-FOLDER",
                "the folder holds no readable PDF",
                "export slides, scripts, sheets and exams as PDF into the folder",
            )
        )
    result.lang = guess_lang(texts)
    result.exam_dates = _exam_dates(result.documents, today)
    return result


def parse_kinds(values: Iterable[str]) -> dict[str, str]:
    """`--kind DOC=KIND` values (DOC: a document id or the file's path in the folder)."""
    out = {}
    for value in values:
        doc, sep, kind = value.rpartition("=")
        if not sep or not doc or kind not in model.DOC_KINDS:
            raise IngestError(
                f"--kind {value!r}: write DOC=KIND with KIND one of {', '.join(model.DOC_KINDS)}"
            )
        out[doc] = kind
    return out


# --- copy (init and add) --------------------------------------------------------------------


@dataclass
class CopyResult:
    added: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    known: list[str] = field(default_factory=list)
    kinds: list[str] = field(default_factory=list)  # documents whose kind the user changed


def _apply(
    course: Path,
    sc: Scan,
    manifest: model.SourceManifest,
    today: dt.date,
    kinds: dict[str, str],
    write: bool,
) -> tuple[model.SourceManifest, CopyResult]:
    """Copy new and changed PDFs into sources/raw and return the updated manifest."""
    res = CopyResult()
    docs = {d.id: d for d in manifest.documents}
    order = [d.id for d in manifest.documents]
    raw = course / "sources" / "raw"
    for cand in sc.documents:
        target = raw / f"{cand.id}.pdf"
        if cand.status == "known":
            res.known.append(cand.id)
            old = docs[cand.id]
            if write and (not target.is_file() or sha256_file(target) != cand.sha256):
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(cand.path, target)  # repair a missing or edited copy
            if cand.kind_from == "user" and old.kind != cand.kind:
                docs[cand.id] = old.model_copy(update={"kind": cand.kind, "kind_from": "user"})
                res.kinds.append(cand.id)
            continue
        if write:
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_name(f".{target.name}.tmp")
            shutil.copy2(cand.path, tmp)
            os.replace(tmp, target)
        entry = model.SourceDocument(
            id=cand.id,
            title=title_of(cand.origin),
            file=target.name,
            origin=cand.origin,
            sha256=cand.sha256,
            bytes=cand.bytes,
            pages=len(cand.info.pages),
            kind=cand.kind,  # type: ignore[arg-type]
            kind_from=cand.kind_from,  # type: ignore[arg-type]
            text_share=cand.info.text_share,
            added=docs[cand.id].added if cand.id in docs else today,
            updated=today if cand.status == "changed" else None,
        )
        if cand.status == "changed":
            res.changed.append(cand.id)
        else:
            res.added.append(cand.id)
            order.append(cand.id)
        docs[cand.id] = entry
    # the user's kinds for documents not in this folder
    for key, kind in kinds.items():
        if key in docs and docs[key].kind != kind and key not in res.kinds:
            docs[key] = docs[key].model_copy(update={"kind": kind, "kind_from": "user"})
            res.kinds.append(key)
    skipped = {s.origin: s for s in manifest.skipped}
    for s in sc.skipped:
        skipped[s.origin] = s
    for origin in [o for o, s in skipped.items() if s.reason != "duplicate"]:
        if any(d.origin == origin for d in docs.values()):
            del skipped[origin]  # it was exported to PDF after all, or is readable now
    updated = manifest.model_copy(
        update={
            "folder": str(sc.folder if sc.folder.is_dir() else sc.folder.parent),
            "documents": [docs[i] for i in order],
            "skipped": sorted(skipped.values(), key=lambda s: s.origin),
        }
    )
    return model.SourceManifest.model_validate(updated.model_dump(by_alias=True)), res


def course_yaml(
    course_id: str,
    *,
    title: str,
    short: str | None,
    semester: str | None,
    round1: model.Round1,
    duration: int | None,
    points: float | None,
    start: dt.date,
    path: Path,
) -> str:
    """The draft course.yaml of §5.4 step 2, from the round-1 answers."""
    fmt = {"written": "written", "written-mc": "mixed", "mc": "mc", "oral": "oral"}
    mc = round1.exam_format in ("written-mc", "mc")
    lang = round1.lang
    draft_title = {"de": "Themen folgen nach dem Einlesen", "en": "Topics follow after reading"}
    lines = []
    ref = _schema_ref(path, "course.schema.json")
    if ref:
        lines.append(f"# yaml-language-server: $schema={ref}")
    lines += [
        "# Draft written by `studykit ingest init`: the topics follow in the synthesis step",
        "# of /register-new-subject (docs/architecture.md §5.4); status turns ready at the end.",
        "schema: 1",
        f"id: {course_id}",
        f"title: {_q(title)}",
    ]
    if short:
        lines.append(f"short: {_q(short)}")
    lines.append(f"lang: {lang}")
    if semester:
        lines.append(f"semester: {_q(semester)}")
    lines += ["status: draft", "exam:"]
    date = None if round1.exam_date == "unknown" else round1.exam_date
    lines.append(f"  date: {_v(date)}")
    if duration:
        lines.append(f"  duration_min: {duration}")
    if points:
        lines.append(f"  points: {_v(points)}")
    lines.append(f"  format: {fmt[round1.exam_format]}")
    if mc:
        lines.append(
            "  mc: {present: true, types: [single, multi, kprim], scoring: all-or-nothing, "
            "negative_marking: false}"
        )
    else:
        lines.append("  mc: {present: false}")
    pages = round1.cheatsheet_pages
    lines.append(
        f"cheatsheet: {{allowed: true, max_pages: {pages}}}"
        if pages
        else "cheatsheet: {allowed: false}"
    )
    lines.append(
        f"study: {{start: {start.isoformat()}, hours_per_week: {_v(round1.hours_per_week)}, "
        "blocked: []}"
    )
    lines += [
        "topics:",
        f"  - {{id: {model.DRAFT_TOPIC}, title: {_q(draft_title[lang])}, weight: 1, prereq: []}}",
        "focus: []",
        "skip: []",
        "targets: {exercises_per_topic: auto, mc_per_topic: auto, mock_exams: 2}",
        "retired_ids: []",
    ]
    return "\n".join(lines) + "\n"


def _course_dir(course_id: str) -> Path:
    if not re.fullmatch(model.PATTERNS["course"], course_id):
        raise IngestError(
            f"course id {course_id!r} does not match {model.PATTERNS['course']} "
            "(lowercase kebab-case, 2 to 40 characters)"
        )
    return (content.courses_dir() / course_id).resolve()


def resolve(course: str) -> Path:
    """A course given by id or directory that has a sources/manifest.yaml."""
    root = content.resolve_course(course)
    if not manifest_path(root).is_file():
        raise IngestError(
            f"no sources/manifest.yaml in {content.display_path(root)}; start with "
            "`studykit ingest init <folder> <course-id>`"
        )
    return root


def init(
    folder: Path,
    course_id: str,
    *,
    lang: str | None = None,
    title: str | None = None,
    short: str | None = None,
    semester: str | None = None,
    exam_date: str | None = None,
    exam_format: str | None = None,
    cheatsheet: int | None = None,
    hours: float | None = None,
    duration: int | None = None,
    points: float | None = None,
    start: dt.date | None = None,
    kinds: dict[str, str] | None = None,
    today: dt.date | None = None,
    dry_run: bool = False,
) -> tuple[dict[str, Any], list[Finding]]:
    """Scaffold (§5.4 step 2): copy the PDFs, write the manifest and a draft course.yaml.

    On a course that exists it resumes: new and changed PDFs are copied, given answers
    replace those recorded, course.yaml is left alone.
    """
    today = today or dt.date.today()
    kinds = kinds or {}
    course = _course_dir(course_id)
    manifest, found = read_manifest(course)
    if found:
        return {}, found
    exists = (course / "course.yaml").is_file()
    sc = scan(folder, manifest=manifest, kinds=kinds, today=today)
    errors = [f for f in sc.findings if f.is_error]
    if errors and manifest is None:
        return {"scan": sc.to_json()}, sc.findings
    old = manifest.answers.round1 if manifest else None
    given = {
        "exam_date": exam_date,
        "exam_format": exam_format,
        "cheatsheet_pages": cheatsheet,
        "hours_per_week": hours,
        "lang": lang or (old.lang if old else None) or sc.lang,
    }
    if old is None:
        missing = [k for k, v in given.items() if v is None and k != "lang"]
        if missing and not exists:
            flags = {
                "exam_date": "--exam-date",
                "exam_format": "--exam-format",
                "cheatsheet_pages": "--cheatsheet",
                "hours_per_week": "--hours-per-week",
            }
            raise IngestError(
                "a new course needs the round-1 answers: " + ", ".join(flags[k] for k in missing)
            )
    round1 = None
    data = {k: v for k, v in given.items() if v is not None}
    if old is not None or len(data) == len(given) or (data.keys() - {"lang"}):
        base = old.model_dump(mode="json") if old else {}
        merged = {**base, **data, "answered": today.isoformat()}
        merged.setdefault("lang", "de")
        try:
            round1 = model.Round1.model_validate(merged)
        except ValidationError as exc:
            raise IngestError(f"round-1 answers do not validate: {exc.errors()[0]['msg']}") from exc
        if old is not None and old.model_dump(exclude={"answered"}) == round1.model_dump(
            exclude={"answered"}
        ):
            round1 = old
    manifest = manifest or model.SourceManifest.model_validate({"schema": 1, "course": course_id})
    if round1 is not None:
        manifest = manifest.model_copy(
            update={"answers": manifest.answers.model_copy(update={"round1": round1})}
        )
    write = not dry_run
    manifest, res = _apply(course, sc, manifest, today, kinds, write)
    course_text = None
    if not exists:
        if round1 is None:
            raise IngestError("course.yaml needs the round-1 answers")
        course_text = course_yaml(
            course_id,
            title=title or course_id,
            short=short,
            semester=semester,
            round1=round1,
            duration=duration,
            points=points,
            start=start or today,
            path=course / "course.yaml",
        )
        try:
            model.validate_course(yamlio.safe_load(course_text))
        except ValidationError as exc:
            msg = exc.errors()[0]["msg"]
            return {}, [
                _finding(
                    course / "course.yaml",
                    "SK-INGEST-COURSE",
                    f"the draft course.yaml does not validate: {msg}",
                    "fix the flag that feeds it (--title, --exam-minutes, --exam-points, …)",
                )
            ]
    if write:
        write_manifest(course, manifest)
        if course_text is not None:
            _write(course / "course.yaml", course_text)
    found = list(sc.findings)
    if write:
        found += gate(course)
    result = {
        "course": course_id,
        "dir": content.display_path(course),
        "created": not exists,
        "dry_run": dry_run,
        "added": res.added,
        "changed": res.changed,
        "known": res.known,
        "kinds_changed": res.kinds,
        "skipped": [s.model_dump(mode="json", exclude_none=True) for s in sc.skipped],
        "round1": round1.model_dump(mode="json") if round1 else None,
        "scan": sc.to_json(),
        "next": f"uv run --frozen studykit ingest extract {course_id}",
    }
    return result, found


def gate(course: Path) -> list[Finding]:
    """Schema findings of the manifest and course.yaml as written (§5.4 step 2's gate)."""
    tree = content.CourseTree(course)
    out: list[Finding] = []
    for rel in ("course.yaml", "sources/manifest.yaml"):
        doc = tree.get(rel)
        if doc is None or doc.yaml is None:
            continue
        out += [f for f in doc.yaml.findings if f.is_error]
        out += doc.validated[1]
    return out


# --- extract --------------------------------------------------------------------------------


def plan_ranges(pages: int, kind: str, max_pages: int = MAX_CHUNK_PAGES) -> list[tuple[int, int]]:
    """Page ranges of a document's chunks: past exams whole, else at most `max_pages` pages
    each, as even as possible."""
    if pages <= 0:
        return []
    if kind in model.PAST_EXAM_KINDS:
        return [(1, pages)]
    n = math.ceil(pages / max_pages)
    size, extra = divmod(pages, n)
    out, first = [], 1
    for i in range(n):
        last = first + size - 1 + (1 if i < extra else 0)
        out.append((first, last))
        first = last + 1
    return out


def _read_index(course: Path, doc: str) -> dict[str, Any] | None:
    try:
        data = json.loads((text_dir(course, doc) / "index.json").read_text(encoding="utf-8"))
    except OSError, ValueError:
        return None
    return data if isinstance(data, dict) else None


def extracted(course: Path, d: model.SourceDocument) -> bool:
    """The page texts of `d` exist and belong to its current version."""
    index = _read_index(course, d.id)
    if not index or index.get("sha256") != d.sha256:
        return False
    return all(page_file(course, d.id, n).is_file() for n in range(1, d.pages + 1))


def _extract_doc(course: Path, d: model.SourceDocument) -> tuple[list[dict[str, Any]], int]:
    """Write the page texts and index of one document; (page infos, stale files removed)."""
    info = analyse_pdf(course / "sources" / "raw" / d.file, keep_text=True)
    if info.error:
        raise IngestError(f"{d.id}: pypdfium2 cannot read sources/raw/{d.file}: {info.error}")
    out = text_dir(course, d.id)
    out.mkdir(parents=True, exist_ok=True)
    old = _read_index(course, d.id)
    removed = 0
    if old is not None and old.get("sha256") != d.sha256:
        # another version: its transcriptions describe pages that changed
        for stale in out.glob("p*.vision.md"):
            stale.unlink()
            removed += 1
    for stale in out.glob("p*.txt"):
        m = re.fullmatch(r"p([0-9]{4})\.txt", stale.name)
        if not m or int(m[1]) > len(info.pages):
            stale.unlink()
    for page in info.pages:
        _write(page_file(course, d.id, page.n), page.text)
    pages = [p.info() for p in info.pages]
    index = {"schema": 1, "doc": d.id, "sha256": d.sha256, "pages": pages}
    _write(out / "index.json", json.dumps(index, ensure_ascii=False, indent=1) + "\n")
    return pages, removed


def read_chunks(course: Path) -> tuple[model.ChunkPlan | None, list[Finding]]:
    return read_yaml_model(chunks_path(course), model.ChunkPlan)


def render_chunks(plan: model.ChunkPlan, path: Path) -> str:
    lines = []
    ref = _schema_ref(path, "chunks.schema.json")
    if ref:
        lines.append(f"# yaml-language-server: $schema={ref}")
    lines += [
        "# Written by `studykit ingest extract`: one sources/notes/<id>.md per chunk (§5.4).",
        "schema: 1",
        f"max_pages: {plan.max_pages}",
    ]
    if not plan.chunks:
        lines.append("chunks: []")
    else:
        lines.append("chunks:")
        for c in plan.chunks:
            lines.append(f"  - {_flow(c.model_dump(mode='json'))}")
    return "\n".join(lines) + "\n"


def extract(course: Path) -> tuple[dict[str, Any], list[Finding]]:
    """Page text and chunk plan for every document whose text is missing or outdated."""
    manifest, found = read_manifest(course)
    if found:
        return {}, found
    if manifest is None:
        raise IngestError(f"no sources/manifest.yaml in {content.display_path(course)}")
    old_plan, found = read_chunks(course)
    if found:  # a broken plan is planned again from scratch
        old_plan = None
    old = old_plan.chunks if old_plan else []
    docs_out, chunks, removed_vision = [], [], 0
    new_ids, replanned, kept = [], [], []
    for d in manifest.documents:
        cached = extracted(course, d)
        if not cached:
            pages, removed = _extract_doc(course, d)
            removed_vision += removed
        else:
            pages = (_read_index(course, d.id) or {}).get("pages") or []
        visual = [p["n"] for p in pages if p.get("visual")]
        scanned = [p["n"] for p in pages if p.get("scanned")]
        docs_out.append(
            {
                "id": d.id,
                "kind": d.kind,
                "pages": d.pages,
                "visual": visual,
                "scanned": scanned,
                "cached": cached,
            }
        )
        previous = [c for c in old if c.doc == d.id]
        ranges = plan_ranges(d.pages, d.kind)
        if (
            previous
            and all(c.sha256 == d.sha256 and c.kind == d.kind for c in previous)
            and [(c.first, c.last) for c in previous] == ranges
        ):
            chunks += previous
            kept += [c.id for c in previous]
            continue
        for i, (first, last) in enumerate(ranges, start=1):
            chunk = model.Chunk(
                id=f"{d.id}-c{i:02d}",
                doc=d.id,
                kind=d.kind,
                first=first,
                last=last,
                flagged=[n for n in visual if first <= n <= last],
                scanned=[n for n in scanned if first <= n <= last],
                sha256=d.sha256,
            )
            chunks.append(chunk)
            (replanned if previous else new_ids).append(chunk.id)
    ids = {c.id for c in chunks}
    removed = [c.id for c in old if c.id not in ids]
    plan = model.ChunkPlan.model_validate(
        {"schema": 1, "max_pages": MAX_CHUNK_PAGES, "chunks": [c.model_dump() for c in chunks]}
    )
    text = render_chunks(plan, chunks_path(course))
    model.ChunkPlan.model_validate(yamlio.safe_load(text))
    _write(chunks_path(course), text)
    result = {
        "course": manifest.course,
        "docs": docs_out,
        "chunks": [
            {
                "id": c.id,
                "doc": c.doc,
                "kind": c.kind,
                "pages": f"{c.first}-{c.last}",
                "flagged": c.flagged,
                "scanned": c.scanned,
                "notes": f"sources/notes/{c.id}.md",
            }
            for c in chunks
        ],
        "new": new_ids,
        "replanned": replanned,
        "kept": kept,
        "removed": removed,
        "transcriptions_removed": removed_vision,
    }
    return result, gate_chunks(course)


def gate_chunks(course: Path) -> list[Finding]:
    tree = content.CourseTree(course)
    doc = tree.get("sources/chunks.yaml")
    if doc is None or doc.yaml is None:
        return []
    return [f for f in doc.yaml.findings if f.is_error] + doc.validated[1]


# --- add ------------------------------------------------------------------------------------


def add(
    course: Path,
    source: Path,
    *,
    kinds: dict[str, str] | None = None,
    today: dt.date | None = None,
    dry_run: bool = False,
) -> tuple[dict[str, Any], list[Finding]]:
    """/add-material: copy what is new or changed in `source`, then extract those documents."""
    today = today or dt.date.today()
    kinds = kinds or {}
    manifest, found = read_manifest(course)
    if found:
        return {}, found
    if manifest is None:
        raise IngestError(f"no sources/manifest.yaml in {content.display_path(course)}")
    sc = scan(source, manifest=manifest, kinds=kinds, today=today)
    errors = [f for f in sc.findings if f.is_error]
    if errors:
        return {"scan": sc.to_json()}, sc.findings
    updated, res = _apply(course, sc, manifest, today, kinds, not dry_run)
    result: dict[str, Any] = {
        "course": manifest.course,
        "dry_run": dry_run,
        "added": res.added,
        "changed": res.changed,
        "known": res.known,
        "kinds_changed": res.kinds,
        "skipped": [s.model_dump(mode="json", exclude_none=True) for s in sc.skipped],
        "scan": sc.to_json(),
    }
    if dry_run:
        return result, sc.findings
    write_manifest(course, updated)
    found = list(sc.findings) + gate(course)
    ext, ext_found = extract(course)
    result["chunks"] = {
        "new": ext.get("new", []),
        "replanned": ext.get("replanned", []),
        "removed": ext.get("removed", []),
    }
    result["read"] = [
        c
        for c in ext.get("chunks", [])
        if c["id"] in {*ext.get("new", []), *ext.get("replanned", [])}
    ]
    return result, found + ext_found


# --- round 2 ----------------------------------------------------------------------------------

MOCK_LINE = re.compile(r"^(targets:.*\bmock_exams:\s*)([0-9]+)", re.MULTILINE)


def round2(
    course: Path, *, mock_exams: int, scope: str, go: bool, today: dt.date | None = None
) -> tuple[dict[str, Any], list[Finding]]:
    """Record the answers of §5.4 step 6; sets targets.mock_exams in course.yaml when it is
    written in the flow form `ingest init` uses."""
    today = today or dt.date.today()
    manifest, found = read_manifest(course)
    if found:
        return {}, found
    if manifest is None:
        raise IngestError(f"no sources/manifest.yaml in {content.display_path(course)}")
    try:
        answer = model.Round2(mock_exams=mock_exams, scope=scope, go=go, answered=today)  # type: ignore[arg-type]
    except ValidationError as exc:
        raise IngestError(f"round-2 answers do not validate: {exc.errors()[0]['msg']}") from exc
    manifest = manifest.model_copy(
        update={"answers": manifest.answers.model_copy(update={"round2": answer})}
    )
    write_manifest(course, manifest)
    course_file = course / "course.yaml"
    updated = False
    if course_file.is_file():
        text = course_file.read_text(encoding="utf-8")
        new = MOCK_LINE.sub(lambda m: f"{m[1]}{mock_exams}", text, count=1)
        if new != text:
            updated = _write(course_file, new)
    result = {
        "course": manifest.course,
        "round2": answer.model_dump(mode="json"),
        "course_yaml_updated": updated,
    }
    return result, gate(course)


# --- text output ------------------------------------------------------------------------------


def format_scan(data: dict[str, Any]) -> str:
    docs = data["documents"]
    lines = [f"{len(docs)} PDF(s) in {data['folder']}"]
    if docs:
        w = max(len(d["id"]) for d in docs)
        lines.append(f"  {'id':<{w}}  {'kind':<14} {'pages':>5} {'text':>5}  visual  origin")
        for d in docs:
            kind = d["kind"] + ("?" if d["uncertain"] else "")
            visual = ",".join(map(str, d["visual_pages"][:6])) + (
                "…" if len(d["visual_pages"]) > 6 else ""
            )
            status = "" if d["status"] == "new" else f" [{d['status']}]"
            lines.append(
                f"  {d['id']:<{w}}  {kind:<14} {d['pages']:>5} {d['text_share']:>5.0%}  "
                f"{visual or '-':<6}  {d['origin']}{status}"
            )
    t = data["totals"]
    lines.append(
        f"{t['pages']} pages, {t['visual_pages']} visual ({t['scanned_pages']} without text "
        f"layer), {t['chunks']} chunk(s); language {data['lang'] or 'unknown'}"
    )
    if t["uncertain_kinds"]:
        lines.append("uncertain kinds (?): " + ", ".join(t["uncertain_kinds"]))
    for s in data["skipped"]:
        lines.append(
            f"skipped {s['origin']}: {s['reason']}" + (f" ({s['note']})" if s.get("note") else "")
        )
    for d in data["exam_dates"]:
        lines.append(f"possible exam date {d['date']} ({d['doc']} p. {d['page']}): {d['context']}")
    return "\n".join(lines)


def format_result(result: dict[str, Any], what: str) -> str:
    lines = []
    if "added" in result:
        lines.append(
            f"{what} {result['course']}: {len(result['added'])} added, {len(result['changed'])} "
            f"changed, {len(result['known'])} unchanged"
            + (" (dry run, nothing written)" if result.get("dry_run") else "")
        )
        for key in ("added", "changed", "kinds_changed"):
            if result.get(key):
                lines.append(f"  {key.replace('_', ' ')}: {', '.join(result[key])}")
    if "chunks" in result and isinstance(result["chunks"], list):
        lines.append(f"{len(result['chunks'])} chunk(s) in sources/chunks.yaml")
        for c in result["chunks"]:
            mark = (
                "new"
                if c["id"] in result["new"]
                else ("replanned" if c["id"] in result["replanned"] else "kept")
            )
            flagged = f", visual {','.join(map(str, c['flagged']))}" if c["flagged"] else ""
            lines.append(f"  {c['id']:<28} {c['doc']} p. {c['pages']}{flagged} ({mark})")
        if result.get("removed"):
            lines.append(f"  removed: {', '.join(result['removed'])}")
    elif isinstance(result.get("chunks"), dict):
        ch = result["chunks"]
        lines.append(
            f"chunks: {len(ch['new'])} new, {len(ch['replanned'])} replanned, "
            f"{len(ch['removed'])} removed"
        )
        for c in result.get("read", []):
            lines.append(f"  read {c['id']} ({c['doc']} p. {c['pages']}) -> {c['notes']}")
    if result.get("next"):
        lines.append(f"next: {result['next']}")
    return "\n".join(lines)
