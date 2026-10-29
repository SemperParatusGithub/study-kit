"""`studykit check-links`: internal links and anchors of the built site resolve."""

from __future__ import annotations

from pathlib import Path

import pytest

from studykit import checklinks, cli


def page(dist: Path, rel: str, body: str) -> None:
    path = dist / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"<!doctype html><html><body>\n{body}\n</body></html>\n", "utf-8")


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    root = tmp_path / "dist"
    page(root, "index.html", '<a href="/c/mini/">Mini</a> <a href="#top" id="top">top</a>')
    page(
        root,
        "c/mini/index.html",
        '<h2 id="übersicht">Übersicht</h2>\n'
        '<a href="summary/rc/">rel</a>\n'
        '<a href="/c/mini/summary/rc/#%C3%BCbertragung">encoded anchor</a>\n'
        '<a href="/c/mini/mc/rc.json">json</a>\n'
        '<a href="https://example.org/x">external</a> <a href="mailto:a@b.de">mail</a>\n'
        '<img src="/_astro/fig.svg" srcset="/_astro/fig.svg 1x, /_astro/fig.svg 2x">\n'
        '<a href="/search?q=rc">search</a>\n'
        '<svg><use href="#glyph-in-svg"></use></svg>',
    )
    page(root, "c/mini/summary/rc/index.html", '<h2 id="übertragung">Ü</h2>')
    page(root, "search/index.html", "<p>search</p>")
    (root / "c/mini/mc").mkdir(parents=True)
    (root / "c/mini/mc/rc.json").write_text("{}")
    (root / "_astro").mkdir()
    (root / "_astro/fig.svg").write_text("<svg/>")
    return root


def test_a_clean_site_has_no_findings(dist: Path) -> None:
    assert checklinks.check(dist) == []


def test_missing_pages_and_anchors_are_reported(dist: Path) -> None:
    page(
        dist,
        "c/mini/exercises/index.html",
        '<a href="/c/mini/exercises/ex-fehlt/">gone</a>\n'
        '<a href="/c/mini/#nirgends">bad anchor</a>\n'
        '<a href="#lokal">local</a>\n'
        '<script src="/_astro/missing.js"></script>',
    )
    found = checklinks.check(dist)
    assert [(f.line, f.code, f.severity) for f in found] == [
        (2, "SK-SITE-LINK", "error"),
        (3, "SK-SITE-LINK", "error"),
        (4, "SK-SITE-LINK", "error"),
        (5, "SK-SITE-LINK", "error"),
    ]
    messages = " | ".join(f.message for f in found)
    assert "/c/mini/exercises/ex-fehlt/ is not in the built site" in messages
    assert "no element with id 'nirgends' in /c/mini/" in messages
    assert "no element with id 'lokal'" in messages
    assert "/_astro/missing.js" in messages
    assert all(f.path.endswith("c/mini/exercises/index.html") for f in found)


def test_course_documents_are_warnings_unless_strict(dist: Path) -> None:
    page(dist, "c/mini/summary/x/index.html", '<a href="/c/mini/src/vl-02.pdf#page=7">VL</a>')
    found = checklinks.check(dist)
    assert [f.severity for f in found] == ["warning"]
    strict = checklinks.check(dist, strict_documents=True)
    assert [f.severity for f in strict] == ["error"]


def test_links_cannot_escape_the_site(dist: Path) -> None:
    (dist.parent / "secret.html").write_text("x")
    page(dist, "a/index.html", '<a href="../../secret.html">up</a>')
    assert [f.severity for f in checklinks.check(dist)] == ["error"]


def test_cli_exit_codes(dist: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["check-links", str(dist)]) == 0
    assert "0 broken link(s)" in capsys.readouterr().out
    page(dist, "b/index.html", '<a href="/nope/">x</a>')
    assert cli.main(["check-links", str(dist)]) == 1
    out = capsys.readouterr().out
    assert "b/index.html:2:1 SK-SITE-LINK href='/nope/': /nope/ is not in the built site" in out
    assert cli.main(["check-links", str(dist / "missing")]) == 2
