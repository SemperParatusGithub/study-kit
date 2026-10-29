"""Synthetic lecture material for the ingest tests, generated at test time (no PDF is
committed): text PDFs written by hand with the standard Helvetica font, and an image-only
"scan" written by Pillow."""

from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw

LOREM = (
    "Der ideale Operationsverstärker hat eine unendlich große Leerlaufverstärkung, einen "
    "unendlich großen Eingangswiderstand und einen verschwindenden Ausgangswiderstand. Mit "
    "Gegenkopplung gilt der virtuelle Kurzschluss zwischen den Eingängen, und in die "
    "Eingänge fließt kein Strom. Der invertierende Verstärker hat die Verstärkung -R2/R1."
)


def _esc(text: str) -> bytes:
    raw = text.encode("cp1252", "replace")
    return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def text_pdf(path: Path, pages: list[str], *, landscape: bool = False) -> Path:
    """A PDF with one text page per entry (WinAnsi Helvetica, so umlauts work)."""
    w, h = (842, 595) if landscape else (595, 842)
    objs: list[bytes] = []
    kids = [4 + 2 * i for i in range(len(pages))]
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    refs = " ".join(f"{k} 0 R" for k in kids)
    objs.append(f"<< /Type /Pages /Kids [{refs}] /Count {len(pages)} >>".encode())
    objs.append(
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    )
    for i, text in enumerate(pages):
        lines = [ln for para in text.split("\n") for ln in textwrap.wrap(para, 90) or [""]]
        body = b" ".join(b"(" + _esc(ln) + b") '" for ln in lines)
        stream = b"BT /F1 10 Tf 14 TL 40 %d Td " % (h - 40) + body + b" ET"
        objs.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {w} {h}] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {kids[i] + 1} 0 R >>".encode()
        )
        objs.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for n, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % n + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objs) + 1,
        xref,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(out))
    return path


def scan_pdf(path: Path, text: str = "Aufgabe 1: Berechnen Sie die Verstärkung.") -> Path:
    """An image-only page: what a scanner makes of a printed sheet (no text layer)."""
    img = Image.new("L", (620, 877), 245)
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(textwrap.wrap(text * 6, 70)):
        draw.text((40, 40 + 18 * i), line, fill=30)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PDF", resolution=75)
    return path


def page_text(n: int, topic: str = "") -> str:
    return f"Seite {n}. {topic} {LOREM}"


def folder(root: Path) -> Path:
    """The test folder: slides (2 pages, with the exam date), an exercise sheet, a past exam
    (3 pages), a 45-page script, a scan, a duplicate, an unsupported .pptx, a photo, and
    files that are ignored."""
    root.mkdir(parents=True, exist_ok=True)
    text_pdf(
        root / "VL01_Grundlagen.pdf",
        [
            page_text(1, "Vorlesung 1: Grundlagen."),
            page_text(2, "Organisatorisches: Klausurtermin am 15.02.2027, 90 Minuten."),
        ],
        landscape=True,
    )
    text_pdf(root / "Uebung01.pdf", [page_text(1, "Übungsblatt 1, Aufgabe 1.")])
    text_pdf(
        root / "Klausur_WS2425.pdf",
        [page_text(n, f"Klausur WS 2024/25, Aufgabe {n} (20 Punkte).") for n in (1, 2, 3)],
    )
    text_pdf(root / "Skript.pdf", [page_text(n, "Skript Kapitel 2.") for n in range(1, 46)])
    scan_pdf(root / "Scan_2019.pdf")
    (root / "copy").mkdir(exist_ok=True)
    (root / "copy" / "VL01_Grundlagen.pdf").write_bytes((root / "VL01_Grundlagen.pdf").read_bytes())
    (root / "Folien_VL02.pptx").write_bytes(b"PK\x03\x04 not really a presentation")
    Image.new("RGB", (40, 30), "white").save(root / "Tafelbild.jpg")
    (root / "liesmich.txt").write_text("Hinweise zum Kurs\n")
    (root / ".DS_Store").write_bytes(b"\0\0\0\1Bud1")
    return root
