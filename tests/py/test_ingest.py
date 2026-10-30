"""`studykit ingest scan|init|extract|add|round2` on synthetic material (docs/architecture.md
§5.4 steps 0 to 3 and 6): every PDF is generated at test time (tests/py/materials.py)."""

from __future__ import annotations

import datetime as dt
import io
import json
import shutil
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

import materials
from conftest import REPO
from studykit import cli, content, ingest, model, validate, yamlio

TODAY = "2026-10-29"
ROUND1 = [
    "--exam-date",
    "2027-02-15",
    "--exam-format",
    "written-mc",
    "--cheatsheet",
    "2",
    "--hours-per-week",
    "6",
    "--today",
    TODAY,
]


def run(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cli.main(list(argv))
    return code, out.getvalue(), err.getvalue()


def run_json(*argv: str) -> tuple[int, dict]:
    code, out, err = run(*argv, "--json")
    assert out, err
    return code, json.loads(out)


@pytest.fixture
def courses(tmp_path: Path, monkeypatch) -> Path:
    path = tmp_path / "courses"
    path.mkdir()
    monkeypatch.setenv("STUDYKIT_COURSES_DIR", str(path))
    return path


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    return materials.folder(tmp_path / "Unterlagen")


def snapshot(root: Path) -> dict[str, tuple[int, int]]:
    return {
        p.relative_to(root).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns)
        for p in sorted(root.rglob("*"))
    }


def init(folder: Path, *extra: str) -> dict:
    code, data = run_json("ingest", "init", str(folder), "opv", *ROUND1, *extra)
    assert code == 0, data["findings"]
    return data


# --- helpers ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("VL03_Operationsverstaerker.pdf", "slides"),
        ("Folien Kapitel 2.pdf", "slides"),
        ("Skript_Kapitel4.pdf", "script"),
        ("Uebungsblatt_03.pdf", "exercises"),
        ("Übung 3 Lösung.pdf", "solutions"),
        ("Klausur_WS2025-26.pdf", "exam"),
        ("Klausur_WS2025-26_Loesung.pdf", "exam-solutions"),
        ("Musterlösung Klausur SS24.pdf", "exam-solutions"),
        ("exam_2024_solutions.pdf", "exam-solutions"),
        ("lecture-05.pdf", "slides"),
        ("scan0001.pdf", "other"),
    ],
)
def test_kind_from_the_file_name(name: str, kind: str):
    assert ingest.guess_kind(name, "", False)[0] == kind


def test_kind_from_the_cover_page_and_the_page_shape():
    assert ingest.guess_kind("scan0001.pdf", "Klausur Elektronik 1, 18.02.2026", False) == (
        "exam",
        "cover",
    )
    assert ingest.guess_kind("scan0001.pdf", "", True) == ("slides", "layout")


def test_doc_ids_are_kebab_case_unique_and_cut_at_a_word():
    assert ingest.doc_id("VL 03 \u2013 Operationsverstärker.pdf") == "vl-03-operationsverstaerker"
    assert ingest.doc_id("a.pdf", {"a"}) == "a-2"
    long = ingest.doc_id("Skript_Kapitel4_Operationsverstaerker_Grundschaltungen_Teil2.pdf")
    assert len(long) <= ingest.MAX_ID and not long.endswith("-")
    assert long == "skript-kapitel4-operationsverstaerker"


@pytest.mark.parametrize(
    ("pages", "kind", "ranges"),
    [
        (14, "slides", [(1, 14)]),
        (20, "script", [(1, 20)]),
        (21, "script", [(1, 11), (12, 21)]),
        (45, "script", [(1, 15), (16, 30), (31, 45)]),
        (45, "exam", [(1, 45)]),  # past exams stay whole
        (3, "exam-solutions", [(1, 3)]),
    ],
)
def test_chunk_ranges(pages: int, kind: str, ranges: list):
    assert ingest.plan_ranges(pages, kind) == ranges


# --- scan --------------------------------------------------------------------------------------


def test_scan_inventories_without_touching_the_folder(folder: Path):
    before = snapshot(folder)
    code, data = run_json("ingest", "scan", str(folder), "--dry-run", "--today", TODAY)
    assert code == 0 and data["ok"]
    assert snapshot(folder) == before
    docs = {d["origin"]: d for d in data["documents"]}
    assert sorted(docs) == [
        "Klausur_WS2425.pdf",
        "Scan_2019.pdf",
        "Skript.pdf",
        "Uebung01.pdf",
        "VL01_Grundlagen.pdf",
    ]
    vl = docs["VL01_Grundlagen.pdf"]
    assert (vl["id"], vl["kind"], vl["kind_from"], vl["pages"]) == (
        "vl01-grundlagen",
        "slides",
        "filename",
        2,
    )
    assert vl["text_share"] == 1.0 and vl["landscape"] and vl["visual_pages"] == []
    assert docs["Klausur_WS2425.pdf"]["kind"] == "exam"
    assert docs["Skript.pdf"]["chunks"] == 3
    scan = docs["Scan_2019.pdf"]
    assert scan["text_share"] == 0.0
    assert scan["scanned_pages"] == [1] and scan["visual_pages"] == [1]
    assert scan["kind"] == "other" and scan["uncertain"]
    skipped = {s["origin"]: s for s in data["skipped"]}
    assert skipped["copy/VL01_Grundlagen.pdf"]["reason"] == "duplicate"
    assert skipped["copy/VL01_Grundlagen.pdf"]["duplicate_of"] == "vl01-grundlagen"
    assert skipped["Folien_VL02.pptx"]["reason"] == "unsupported"
    assert "export it as PDF" in skipped["Folien_VL02.pptx"]["note"]
    assert skipped["Tafelbild.jpg"]["reason"] == "image"
    assert skipped["liesmich.txt"]["reason"] == "ignored"
    assert ".DS_Store" not in skipped
    codes = sorted({f["code"] for f in data["findings"]})
    assert codes == ["SK-INGEST-DUPLICATE", "SK-INGEST-UNSUPPORTED"]
    assert all(f["severity"] == "warning" for f in data["findings"])
    t = data["totals"]
    assert (t["pdfs"], t["pages"], t["scanned_pages"], t["chunks"]) == (5, 52, 1, 7)
    assert t["past_exams"] == ["klausur-ws2425"]
    assert data["lang"] == "de"
    assert [d["date"] for d in data["exam_dates"]] == ["2027-02-15"]
    assert data["exam_dates"][0]["doc"] == "vl01-grundlagen"


def test_scan_text_output_and_kind_override(folder: Path):
    code, out, err = run("ingest", "scan", str(folder), "--kind", "scan-2019=exercises")
    assert code == 0
    assert "SK-INGEST-UNSUPPORTED" in err
    assert "scan-2019" in out and "exercises" in out
    assert "uncertain kinds" not in out


def test_scan_refuses_a_missing_or_empty_folder(tmp_path: Path):
    code, data = run_json("ingest", "scan", str(tmp_path / "nope"))
    assert code == 1 and data["findings"][0]["code"] == "SK-INGEST-FOLDER"
    (tmp_path / "leer").mkdir()
    (tmp_path / "leer" / "folien.pptx").write_bytes(b"PK")
    code, data = run_json("ingest", "scan", str(tmp_path / "leer"))
    assert code == 1
    assert "SK-INGEST-FOLDER" in {f["code"] for f in data["findings"]}
    assert run("ingest", "scan", str(tmp_path), "--kind", "x=lecture")[0] == 2


def test_scan_reports_an_unreadable_pdf(tmp_path: Path):
    folder = tmp_path / "f"
    materials.text_pdf(folder / "ok.pdf", [materials.page_text(1)])
    (folder / "kaputt.pdf").write_bytes(b"%PDF-1.4 this is not a PDF")
    code, data = run_json("ingest", "scan", str(folder))
    assert code == 0
    assert [d["origin"] for d in data["documents"]] == ["ok.pdf"]
    assert data["skipped"][0]["reason"] == "unreadable"
    assert data["findings"][0]["code"] == "SK-INGEST-PDF"


# --- init ---------------------------------------------------------------------------------------


def test_init_copies_and_writes_a_draft_course(courses: Path, folder: Path):
    before = snapshot(folder)
    data = init(folder, "--title", "Elektronik 1", "--kind", "scan-2019=exercises")
    assert snapshot(folder) == before  # the user's folder is only read
    course = courses / "opv"
    assert data["created"] and len(data["added"]) == 5
    raw = sorted(p.name for p in (course / "sources" / "raw").iterdir())
    assert raw == [f"{d}.pdf" for d in sorted(data["added"])]
    manifest = model.SourceManifest.model_validate(
        yamlio.safe_load((course / "sources" / "manifest.yaml").read_text())
    )
    assert manifest.course == "opv" and manifest.folder == str(folder)
    scan = next(d for d in manifest.documents if d.id == "scan-2019")
    assert (scan.kind, scan.kind_from, scan.text_share) == ("exercises", "user", 0.0)
    assert scan.added == dt.date(2026, 10, 29)
    for d in manifest.documents:
        assert ingest.sha256_file(course / "sources" / "raw" / d.file) == d.sha256
    r1 = manifest.answers.round1
    assert r1 is not None
    assert (r1.exam_date, r1.exam_format, r1.cheatsheet_pages, r1.hours_per_week, r1.lang) == (
        dt.date(2027, 2, 15),
        "written-mc",
        2,
        6,
        "de",
    )
    assert {s.origin for s in manifest.skipped} == {
        "copy/VL01_Grundlagen.pdf",
        "Folien_VL02.pptx",
        "Tafelbild.jpg",
        "liesmich.txt",
    }
    tree = content.CourseTree(course)
    c = tree.model
    assert c is not None, tree.course_doc.validated[1]
    assert (c.status, c.topic_ids, c.title) == ("draft", [model.DRAFT_TOPIC], "Elektronik 1")
    assert c.exam.format == "mixed" and c.exam.mc and c.exam.mc.present
    assert c.cheatsheet.allowed and c.cheatsheet.max_pages == 2
    assert c.study and c.study.hours_per_week == 6 and c.study.start == dt.date(2026, 10, 29)
    report = validate.validate([course], quick=True)
    assert not [f for f in report.findings if f.is_error], [f.format() for f in report.findings]


def test_init_is_idempotent(courses: Path, folder: Path):
    init(folder)
    course = courses / "opv"
    files = snapshot(course)
    data = init(folder)
    assert not data["created"] and data["added"] == [] and len(data["known"]) == 5
    assert snapshot(course) == files


@pytest.mark.parametrize("pages", [0, 10])
def test_init_on_an_unknown_exam_date_with_cheatsheet_allowance(courses: Path, folder: Path, pages):
    code, data = run_json(
        "ingest",
        "init",
        str(folder),
        "et2",
        "--exam-date",
        "unknown",
        "--exam-format",
        "oral",
        "--cheatsheet",
        str(pages),
        "--hours-per-week",
        "4.5",
        "--lang",
        "en",
    )
    assert code == 0, data["findings"]
    c = content.CourseTree(courses / "et2").model
    assert c is not None
    assert c.exam.date is None and c.exam.format == "oral"
    assert c.cheatsheet.allowed == bool(pages)
    if pages:
        assert c.cheatsheet.max_pages == pages
    assert c.lang == "en" and c.topics[0].title == "Topics follow after reading"


def test_init_needs_the_round_one_answers(courses: Path, folder: Path):
    code, _out, err = run("ingest", "init", str(folder), "opv")
    assert code == 2 and "--exam-date" in err and "--hours-per-week" in err
    assert not (courses / "opv").exists()
    code, _out, err = run("ingest", "init", str(folder), "Not A Course", *ROUND1)
    assert code == 2 and "course id" in err


def test_init_dry_run_writes_nothing(courses: Path, folder: Path):
    code, data = run_json("ingest", "init", str(folder), "opv", *ROUND1, "--dry-run")
    assert code == 0 and data["dry_run"] and len(data["added"]) == 5
    assert not (courses / "opv").exists()


# --- extract -----------------------------------------------------------------------------------


def test_extract_writes_page_text_and_the_chunk_plan(courses: Path, folder: Path):
    init(folder)
    course = courses / "opv"
    code, data = run_json("ingest", "extract", "opv")
    assert code == 0, data["findings"]
    chunks = {c["id"]: c for c in data["chunks"]}
    assert sorted(chunks) == [
        "klausur-ws2425-c01",
        "scan-2019-c01",
        "skript-c01",
        "skript-c02",
        "skript-c03",
        "uebung01-c01",
        "vl01-grundlagen-c01",
    ]
    assert [chunks[f"skript-c0{i}"]["pages"] for i in (1, 2, 3)] == ["1-15", "16-30", "31-45"]
    assert chunks["klausur-ws2425-c01"]["pages"] == "1-3"
    assert chunks["scan-2019-c01"]["flagged"] == [1] == chunks["scan-2019-c01"]["scanned"]
    assert sorted(data["new"]) == sorted(chunks)
    text = course / "sources" / "text"
    assert (text / "vl01-grundlagen" / "p0002.txt").read_text().count("15.02.2027") == 1
    assert len(list((text / "skript").glob("p*.txt"))) == 45
    assert (text / "scan-2019" / "p0001.txt").read_text().strip() == ""
    index = json.loads((text / "scan-2019" / "index.json").read_text())
    assert index["pages"][0]["scanned"] and "no text layer" in index["pages"][0]["reasons"]
    plan = model.ChunkPlan.model_validate(
        yamlio.safe_load((course / "sources" / "chunks.yaml").read_text())
    )
    assert all(c.first <= c.last <= c.first + 19 or c.kind == "exam" for c in plan.chunks)
    # a second run reads nothing again and keeps every chunk id
    files = snapshot(course / "sources")
    code, again = run_json("ingest", "extract", "opv")
    assert code == 0 and again["new"] == [] and sorted(again["kept"]) == sorted(chunks)
    assert all(d["cached"] for d in again["docs"])
    assert snapshot(course / "sources") == files
    report = validate.validate([course], quick=True)
    assert not [f for f in report.findings if f.is_error]


def test_extract_needs_a_manifest(courses: Path):
    (courses / "x1").mkdir()
    code, _out, err = run("ingest", "extract", "x1")
    assert code == 2 and "ingest init" in err


# --- add ---------------------------------------------------------------------------------------


def test_add_copies_only_new_and_changed_documents(courses: Path, folder: Path, tmp_path: Path):
    init(folder)
    run("ingest", "extract", "opv")
    course = courses / "opv"
    extra = tmp_path / "neu"
    materials.text_pdf(extra / "VL02_Verstaerker.pdf", [materials.page_text(n) for n in (1, 2)])
    shutil.copy(folder / "Uebung01.pdf", extra / "Uebung01_Kopie.pdf")
    code, data = run_json("ingest", "add", "opv", str(extra), "--today", "2026-11-05")
    assert code == 0, data["findings"]
    assert data["added"] == ["vl02-verstaerker"]
    assert data["chunks"]["new"] == ["vl02-verstaerker-c01"]
    assert [c["notes"] for c in data["read"]] == ["sources/notes/vl02-verstaerker-c01.md"]
    assert "SK-INGEST-DUPLICATE" in {f["code"] for f in data["findings"]}
    manifest = ingest.read_manifest(course)[0]
    assert manifest is not None
    new = next(d for d in manifest.documents if d.id == "vl02-verstaerker")
    assert new.added == dt.date(2026, 11, 5)
    assert len(manifest.documents) == 6
    # the same PDF again: nothing to do
    code, data = run_json("ingest", "add", "opv", str(extra / "VL02_Verstaerker.pdf"))
    assert code == 0 and data["added"] == [] and data["known"] == ["vl02-verstaerker"]
    assert data["chunks"]["new"] == []


def test_add_replaces_a_changed_document(courses: Path, folder: Path):
    init(folder)
    run("ingest", "extract", "opv")
    course = courses / "opv"
    old = ingest.read_manifest(course)[0]
    materials.text_pdf(folder / "Uebung01.pdf", [materials.page_text(1, "Neue Fassung.")] * 2)
    code, data = run_json("ingest", "add", "opv", str(folder), "--today", "2026-11-05")
    assert code == 0, data["findings"]
    assert data["changed"] == ["uebung01"] and data["added"] == []
    assert data["chunks"]["replanned"] == ["uebung01-c01"]
    m = ingest.read_manifest(course)[0]
    assert m is not None
    doc = next(d for d in m.documents if d.id == "uebung01")
    assert doc.pages == 2 and doc.updated == dt.date(2026, 11, 5)
    assert doc.sha256 != next(d for d in old.documents if d.id == "uebung01").sha256
    assert len(list((course / "sources" / "text" / "uebung01").glob("p*.txt"))) == 2


def test_add_dry_run_writes_nothing(courses: Path, folder: Path, tmp_path: Path):
    init(folder)
    course = courses / "opv"
    files = snapshot(course)
    materials.text_pdf(tmp_path / "x" / "Neu.pdf", [materials.page_text(1)])
    code, data = run_json("ingest", "add", "opv", str(tmp_path / "x"), "--dry-run")
    assert code == 0 and data["added"] == ["neu"]
    assert snapshot(course) == files


# --- round 2 -----------------------------------------------------------------------------------


def test_round2_records_the_answers(courses: Path, folder: Path):
    init(folder)
    code, data = run_json("ingest", "round2", "opv", "--mock-exams", "3", "--scope", "core")
    assert code == 0 and data["course_yaml_updated"]
    course = courses / "opv"
    m = ingest.read_manifest(course)[0]
    assert m is not None and m.answers.round2 is not None
    assert (m.answers.round2.mock_exams, m.answers.round2.scope, m.answers.round2.go) == (
        3,
        "core",
        True,
    )
    c = content.CourseTree(course).model
    assert c is not None and c.targets.mock_exams == 3


# --- validate on the ingest files ----------------------------------------------------------


NOTES = """---
chunk: {chunk}
doc: {doc}
pages: '{pages}'
source_sha256: {sha}
kind: {kind}
title: Grundlagen
topics: [idealer-opv]
---

# Grundlagen

Der ideale OPV hat $V_0 \\to \\infty$.
"""


def notes_for(course: Path, chunk: model.Chunk, **change: str) -> Path:
    fields = {
        "chunk": chunk.id,
        "doc": chunk.doc,
        "pages": f"{chunk.first}-{chunk.last}",
        "sha": chunk.sha256,
        "kind": chunk.kind,
        **change,
    }
    path = course / "sources" / "notes" / f"{change.get('file', chunk.id)}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(NOTES.format(**fields))
    return path


def codes(course: Path, *, quick: bool = False) -> dict[str, list[str]]:
    report = validate.validate([course], quick=quick, config=validate.Config(pdf=False))
    out: dict[str, list[str]] = {}
    for f in report.findings:
        out.setdefault(f.code, []).append(f.severity)
    return out


def test_validate_checks_notes_against_the_chunk_plan(courses: Path, folder: Path):
    init(folder)
    run("ingest", "extract", "opv")
    course = courses / "opv"
    plan = ingest.read_chunks(course)[0]
    assert plan is not None
    first, second, third = plan.chunks[:3]
    notes_for(course, first)
    assert "SK-REF-CHUNK" not in codes(course)
    notes_for(course, second, pages="1-99")
    notes_for(course, third, sha="f" * 64)
    found = codes(course)
    assert sorted(found["SK-REF-CHUNK"]) == ["error", "warning"]
    (course / "sources" / "notes" / f"{second.id}.md").unlink()
    notes_for(course, first, file="vl01-grundlagen-c09")
    found = codes(course, quick=True)
    assert "error" in found["SK-STRUCT-PATH"]


def test_validate_checks_the_exam_profile(courses: Path, folder: Path):
    init(folder)
    course = courses / "opv"
    profile = course / "analysis" / "exam-profile.yaml"
    profile.parent.mkdir()
    profile.write_text(
        "schema: 1\nconfidence: medium\nbasis: past-exams\nexams: [klausur-ws2425, ws99]\n"
        "archetypes:\n  - {id: verstaerker, title: Verstärker, topic: opv, share: 0.5}\n"
        "  - {id: integrierer, title: Integrierer, share: 0.3}\n"
    )
    found = codes(course)
    assert found["SK-SCHEMA-SHARES"] == ["error"]
    profile.write_text(profile.read_text().replace("share: 0.3", "share: 0.5"))
    found = codes(course)
    assert "SK-SCHEMA-SHARES" not in found
    assert found["SK-REF-MISSING"] == ["error"]  # ws99; topics are not checked while draft


def test_a_ready_course_cannot_keep_the_draft_topic(courses: Path, folder: Path):
    init(folder)
    path = courses / "opv" / "course.yaml"
    path.write_text(path.read_text().replace("status: draft", "status: ready"))
    assert "SK-STRUCT-DRAFT" in codes(courses / "opv", quick=True)


def test_schema_files_cover_the_ingest_models():
    for name in ("manifest", "chunks", "notes", "exam-profile", "notation"):
        assert (REPO / "schemas" / f"{name}.schema.json").is_file()


# --- the sample materials (examples/sample-materials) --------------------------------------------


def test_the_sample_materials_build_and_scan(tmp_path: Path):
    """`just sample-materials` builds every PDF, and the scan sees them as §5.4 expects:
    the kinds from the file names, the circuit slides and the scan as visual pages."""
    out = tmp_path / "materials"
    script = REPO / "examples" / "sample-materials" / "build.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--out", str(out)], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    data = ingest.scan(out, today=dt.date(2026, 10, 29)).to_json()
    assert data["findings"] == []
    docs = {d["origin"]: d for d in data["documents"]}
    assert {o: d["kind"] for o, d in docs.items()} == {
        "Altes_Uebungsblatt02_Scan.pdf": "exercises",
        "Klausur_WS2025-26.pdf": "exam",
        "Klausur_WS2025-26_Loesung.pdf": "exam-solutions",
        "Skript_Kapitel4_Operationsverstaerker.pdf": "script",
        "Uebung03_OPV_Grundschaltungen.pdf": "exercises",
        "Uebung03_OPV_Grundschaltungen_Loesung.pdf": "solutions",
        "VL03_Operationsverstaerker_Grundschaltungen.pdf": "slides",
    }
    scan = docs["Altes_Uebungsblatt02_Scan.pdf"]
    assert scan["text_share"] == 0.0 and scan["scanned_pages"] == [1]
    slides = docs["VL03_Operationsverstaerker_Grundschaltungen.pdf"]
    assert slides["pages"] == 14 and slides["landscape"] and slides["text_share"] == 1.0
    assert {5, 8, 11} <= set(slides["visual_pages"])  # the three circuit slides
    assert "2027-02-17" in [d["date"] for d in data["exam_dates"]]
    assert data["lang"] == "de"


# --- page ------------------------------------------------------------------------------------


def test_page_renders_pdf_pages_to_png(courses: Path, folder: Path):
    init(folder)
    course = courses / "opv"
    m, _ = ingest.read_manifest(course)
    doc = m.documents[0]
    code, data = run_json("ingest", "page", "opv", doc.id, "1-2" if doc.pages > 1 else "1")
    assert code == 0
    images = [REPO / p if not Path(p).is_absolute() else Path(p) for p in data["images"]]
    assert [p.name for p in images] == [f"p{n:04d}.png" for n in range(1, len(images) + 1)]
    for p in images:
        assert p.parent == course / "_build" / "pages" / doc.id
        assert p.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    code, _, err = run("ingest", "page", "opv", doc.id, str(doc.pages + 1))
    assert code == 2 and "page" in err
    code, _, err = run("ingest", "page", "opv", "nope", "1")
    assert code == 2 and "nope" in err
    code, _, err = run("ingest", "page", "opv", doc.id, "1-9")
    assert code == 2 and "at most" in err
