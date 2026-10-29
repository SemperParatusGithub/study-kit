"""`studykit check-links site/dist`: every internal link of the built site resolves.

Part of the Site stage (docs/architecture.md §4.3, SK-SITE). Every HTML file under the
directory is parsed; each `href`, `src`, `srcset` and form `action` that points inside the
site must name a file in the directory, and a `#fragment` on an HTML target must name an
`id` (or `<a name>`) in that page. A route ending in `/` resolves to its `index.html`.

External URLs (any scheme, protocol-relative `//host`) are skipped, and so are query strings
and fragment references inside inline SVG (`<use href="#…">`), which never leave the page.

PDFs under `/c/<course>/src/` and `/c/<course>/pdf/` are served from course files the site
does not build itself (lecture sources, `_build/pdf`); a missing one is a warning unless
`strict_documents` is set.

Each problem is a finding `path:line:col SK-SITE-LINK message (fix: …)`.
"""

from __future__ import annotations

import posixpath
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from studykit import content
from studykit.findings import Finding

CODE = "SK-SITE-LINK"
# Attributes that point at another resource, per element.
LINK_ATTRS: dict[str, tuple[str, ...]] = {
    "a": ("href",),
    "area": ("href",),
    "link": ("href",),
    "img": ("src", "srcset"),
    "source": ("src", "srcset"),
    "script": ("src",),
    "iframe": ("src",),
    "video": ("src", "poster"),
    "audio": ("src",),
    "track": ("src",),
    "embed": ("src",),
    "form": ("action",),
}
# Links to these may point at documents the site serves from course files, not from dist.
DOCUMENT_RE = re.compile(r"^/c/[^/]+/(?:src|pdf)/[^/]+\.pdf$")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


@dataclass
class Page:
    ids: set[str] = field(default_factory=set)
    links: list[tuple[int, int, str, str]] = field(default_factory=list)  # line, col, attr, url


class _Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.page = Page()
        self.svg_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._tag(tag, attrs)
        if tag == "svg":
            self.svg_depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._tag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag == "svg" and self.svg_depth:
            self.svg_depth -= 1

    def _tag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {k: v for k, v in attrs if v is not None}
        if values.get("id"):
            self.page.ids.add(values["id"])
        if tag == "a" and values.get("name"):
            self.page.ids.add(values["name"])
        if self.svg_depth:
            return  # <use href="#…"> and friends stay inside the inline SVG
        line, col = self.getpos()
        for attr in LINK_ATTRS.get(tag, ()):
            value = values.get(attr)
            if value is None:
                continue
            if attr == "srcset":
                for part in value.split(","):
                    url = part.strip().split(" ")[0]
                    if url:
                        self.page.links.append((line, col + 1, attr, url))
            else:
                self.page.links.append((line, col + 1, attr, value.strip()))


def parse_page(path: Path) -> Page:
    parser = _Parser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    parser.close()
    return parser.page


def is_external(url: str) -> bool:
    return bool(SCHEME_RE.match(url)) or url.startswith("//")


def page_url(dist: Path, path: Path) -> str:
    """The URL path a file in dist is served at (`c/x/index.html` -> `/c/x/`)."""
    rel = path.relative_to(dist).as_posix()
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    return "/" + rel


def resolve(dist: Path, url_path: str) -> Path | None:
    """The file in dist that serves `url_path`, or None."""
    rel = url_path.lstrip("/")
    candidates = []
    if rel == "" or url_path.endswith("/"):
        candidates.append(dist / rel / "index.html")
    else:
        candidates += [dist / rel, dist / rel / "index.html", dist / f"{rel}.html"]
    for candidate in candidates:
        try:
            candidate.resolve().relative_to(dist.resolve())
        except ValueError:
            continue
        if candidate.is_file():
            return candidate
    return None


def html_files(dist: Path) -> Iterator[Path]:
    yield from sorted(dist.rglob("*.html"))


def check(dist: Path, *, strict_documents: bool = False) -> list[Finding]:
    """All broken internal links and anchors in `dist`, as findings."""
    dist = dist.resolve()
    pages: dict[Path, Page] = {p.resolve(): parse_page(p) for p in html_files(dist)}
    out: list[Finding] = []
    for path, page in pages.items():
        here = page_url(dist, path)
        shown = content.display_path(path)
        for line, col, attr, url in page.links:
            if not url or is_external(url):
                continue
            parts = urlsplit(url)
            target_path = unquote(parts.path)
            if target_path:
                base = here if here.endswith("/") else posixpath.dirname(here) + "/"
                joined = posixpath.normpath(posixpath.join(base, target_path))
                if target_path.endswith("/") and not joined.endswith("/"):
                    joined += "/"
                target = resolve(dist, joined)
            else:
                joined, target = here, path
            if target is None:
                warn = DOCUMENT_RE.match(joined) and not strict_documents
                out.append(
                    Finding(
                        shown,
                        line,
                        col,
                        CODE,
                        f"{attr}={url!r}: {joined} is not in the built site",
                        "fix the link, or build the page or file it points to",
                        "warning" if warn else "error",
                    )
                )
                continue
            fragment = unquote(parts.fragment)
            if not fragment or target.suffix != ".html":
                continue
            target_page = pages.get(target.resolve())
            if target_page is not None and fragment not in target_page.ids:
                out.append(
                    Finding(
                        shown,
                        line,
                        col,
                        CODE,
                        f"{attr}={url!r}: no element with id {fragment!r} in {joined}",
                        "link an existing heading or item id",
                    )
                )
    return sorted(out)
