"""The pandoc filter set: every fixture through html5, typst (compiled) and json.

Fixtures live in tests/fixtures/pandoc/:
- ok/ is a small course tree; the path below ok/ is the file's sk-file.
- bad/*.md each carry their expectation in the frontmatter (sk-file, code, message, line
  and optionally targets); the frontmatter is blanked before pandoc runs, as for real
  course files, so `line` is the line in the fixture file.
- index.json is the course index the filter resolves references and figures against.
The golden corpora tests/golden/blocks.md and mcq.md are split into parts at
`# sk-file: <path>` lines and checked the same way, plus KaTeX on every formula.
"""

from __future__ import annotations

import base64
import dataclasses
import json
import re
import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

import pytest
import yaml

from studykit import golden, pandoc, tools, validate

ROOT = tools.repo_root()
FIXTURES = ROOT / "tests" / "fixtures" / "pandoc"
OK = FIXTURES / "ok"
BAD = FIXTURES / "bad"
INDEX = FIXTURES / "index.json"
GOLDEN = ROOT / "tests" / "golden"
DENYLIST = ROOT / "pandoc" / "math-denylist.json"

OK_FILES = sorted(p.relative_to(OK).as_posix() for p in OK.rglob("*.md"))
BAD_FILES = sorted(BAD.glob("*.md"))
TARGETS: tuple[pandoc.Target, ...] = ("html", "typst", "json")
INDEX_DATA = json.loads(INDEX.read_text(encoding="utf-8"))


# --- helpers -----------------------------------------------------------------------------


@pytest.fixture(scope="session")
def workdir() -> Iterator[Path]:
    """Scratch directory inside the repository: Typst reads only files below --root."""
    base = ROOT / ".cache"
    base.mkdir(exist_ok=True)
    path = Path(tempfile.mkdtemp(prefix="test-filters-", dir=base))
    figdir = path / "figures"
    figdir.mkdir()
    # Placeholder images for the compile check; real figures come from studykit.figures.
    for slug in INDEX_DATA["figures"]:
        (figdir / f"{slug}.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 60" width="120" height="60">'
            '<rect x="1" y="1" width="118" height="58" fill="none" stroke="#0072b2"/></svg>'
        )
    yield path
    shutil.rmtree(path, ignore_errors=True)


def document(file: str, workdir: Path, solutions: pandoc.Solutions = "appendix", lang: str = "de"):
    return pandoc.Document(
        course=INDEX_DATA["course"],
        lang=lang,
        file=file,
        index=INDEX,
        solutions=solutions,
        figdir=workdir / "figures",
    )


def compile_typst(source: str, workdir: Path, name: str) -> None:
    """Compile with the pinned Typst exactly as the PDF build does; fail on any warning."""
    typ = workdir / f"{name}.typ"
    typ.write_text(source, encoding="utf-8")
    proc = subprocess.run(
        [
            str(tools.bin_path(ROOT, "typst")),
            "compile",
            "--root",
            str(ROOT),
            "--ignore-system-fonts",
            "--diagnostic-format",
            "short",
            str(typ),
            str(typ.with_suffix(".pdf")),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env={"SOURCE_DATE_EPOCH": "0", "PATH": "/usr/bin:/bin"},
        check=False,
    )
    problems = [ln for ln in proc.stderr.splitlines() if "error" in ln or "warning" in ln]
    assert proc.returncode == 0 and not problems, f"{name}: {proc.stderr}\n--- source ---\n{source}"


@dataclass
class Node:
    tag: str
    attrs: dict[str, str | None]
    children: list[Node] = field(default_factory=list)
    text: str = ""

    def iter(self, tag: str | None = None) -> Iterator[Node]:
        for child in self.children:
            if tag is None or child.tag == tag:
                yield child
            yield from child.iter(tag)

    def find_all(self, tag: str) -> list[Node]:
        return list(self.iter(tag))

    def classes(self) -> list[str]:
        return (self.attrs.get("class") or "").split()

    def all_text(self) -> str:
        return self.text + "".join(c.all_text() for c in self.children)


VOID = {"br", "hr", "img", "input", "col", "meta", "link", "source", "wbr"}


class TreeBuilder(HTMLParser):
    """A strict little DOM: every non-void element must be closed in order."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", {})
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, dict(attrs)))

    def handle_endtag(self, tag):
        assert self.stack[-1].tag == tag, f"</{tag}> closes <{self.stack[-1].tag}>"
        self.stack.pop()

    def handle_data(self, data):
        self.stack[-1].text += data


def parse_html(fragment: str) -> Node:
    builder = TreeBuilder()
    builder.feed(fragment)
    builder.close()
    assert len(builder.stack) == 1, f"unclosed <{builder.stack[-1].tag}>"
    return builder.root


def sk_meta(tree: Node) -> dict:
    scripts = [n for n in tree.iter("script") if n.attrs.get("id") == "sk-meta"]
    assert len(scripts) == 1
    assert tree.children[-1] is scripts[0], "sk-meta must be the last block"
    assert scripts[0].attrs.get("type") == "application/json"
    return json.loads(scripts[0].text)


def check_html_contract(html: str) -> Node:
    """Structural checks of contract item 5 that hold for every document."""
    tree = parse_html(html)
    for math in tree.iter("sk-math"):
        assert set(math.attrs) == {"data-tex", "data-display"}
        assert math.attrs["data-display"] in {"0", "1"}
        assert base64.b64decode(math.attrs["data-tex"]).decode("utf-8").strip()
        assert not math.children and not math.text
    for aside in tree.iter("aside"):
        name = aside.attrs["data-block"]
        assert aside.classes() == ["sk-block", f"sk-{name}"]
        first = aside.children[0]
        assert first.tag == "div" and first.classes() == ["sk-block-title"]
        assert first.all_text().strip()
    for fig in tree.iter("figure"):
        assert fig.classes() == ["sk-fig"] and fig.attrs["data-slug"] in INDEX_DATA["figures"]
        assert [c.tag for c in fig.children] == ["div", "figcaption"]
        assert fig.children[0].classes() == ["sk-fig-slot"] and not fig.children[0].children
    for a in tree.iter("a"):
        kinds = [c for c in a.classes() if c.startswith("sk-ref-")]
        if "sk-ref" in a.classes():
            assert len(kinds) == 1
            assert a.attrs["href"].startswith(f"/c/{INDEX_DATA['course']}/")
    for mc in tree.iter("sk-mc"):
        check_mc(mc)
    meta = sk_meta(tree)
    assert set(meta) == {"headings", "items"}
    for h in meta["headings"]:
        assert h["level"] >= 2 and h["id"] and h["text"]
    return tree


def check_mc(mc: Node) -> None:
    attrs = mc.attrs
    assert attrs["data-type"] in {"single", "multi", "kprim"}
    assert attrs["data-difficulty"] in {"1", "2", "3", "4"}
    assert attrs["data-pin-last"] in {"true", "false"}
    assert attrs["data-id"] and attrs["data-topic"]
    tags = [c.tag for c in mc.children]
    assert tags[0] == "div" and mc.children[0].classes() == ["sk-stem"]
    assert tags[-1] == "div" and mc.children[-1].classes() == ["sk-explanation"]
    assert "hidden" in mc.children[-1].attrs
    opts = [c for c in mc.children if c.tag == "sk-opt"]
    assert tags == ["div", *["sk-opt"] * len(opts), "div"]
    assert [o.attrs["data-key"] for o in opts] == list("ABCDEF"[: len(opts)])
    for o in opts:
        assert o.attrs["data-correct"] in {"true", "false"}
        text, why = o.children
        assert text.classes() == ["sk-opt-text"] and "hidden" not in text.attrs
        assert why.classes() == ["sk-why"] and "hidden" in why.attrs
    correct = sum(o.attrs["data-correct"] == "true" for o in opts)
    n = len(opts)
    match attrs["data-type"]:
        case "single":
            assert 3 <= n <= 5 and correct == 1
        case "multi":
            assert 4 <= n <= 6 and 0 < correct < n
        case "kprim":
            assert n == 4


def corpus_parts(path: Path) -> list[tuple[str, str]]:
    """Split a golden corpus at `# sk-file: <path>` lines, keeping line numbers."""
    lines = path.read_text(encoding="utf-8").splitlines()
    parts: list[tuple[str, list[str]]] = []
    for i, line in enumerate(lines):
        m = re.fullmatch(r"# sk-file: (\S+)", line)
        if m:
            parts.append((m.group(1), [""] * len(lines)))
        elif parts:
            parts[-1][1][i] = line
    return [(file, "\n".join(body) + "\n") for file, body in parts]


GOLDEN_PARTS = [
    pytest.param(corpus, file, body, id=f"{corpus}:{file}")
    for corpus in ("blocks.md", "mcq.md")
    for file, body in corpus_parts(GOLDEN / corpus)
]


def math_in(tree: Node) -> list[golden.Formula]:
    return [
        golden.Formula(
            base64.b64decode(m.attrs["data-tex"]).decode("utf-8"), m.attrs["data-display"] == "1"
        )
        for m in tree.iter("sk-math")
    ]


# --- pandoc behaviour the filter relies on -------------------------------------------------


def test_loose_task_list_keeps_checkbox_markers():
    """docs/architecture.md §2.6: option paragraph + why paragraph per item still parses."""
    ast = pandoc.to_json("- [x] right\n\n  why\n\n- [ ] wrong\n\n  why\n")
    (bullet,) = ast["blocks"]
    assert bullet["t"] == "BulletList"
    markers = []
    for item in bullet["c"]:
        assert [b["t"] for b in item] == ["Para", "Para"]
        markers.append(item[0]["c"][0]["c"])
    assert markers == ["☒", "☐"]


def test_task_list_splits_at_item_without_checkbox():
    ast = pandoc.to_json("- [x] a\n\n  why\n\n- b\n\n  why\n\n- [ ] c\n\n  why\n")
    assert [b["t"] for b in ast["blocks"]] == ["BulletList"] * 3


def test_defaults_work_with_spec_command_line(workdir):
    """`pandoc -d pandoc/defaults/common.yaml -d pandoc/defaults/web.yaml` from the root."""
    doc = document("overview.md", workdir)
    args = pandoc.argv(doc, "html")
    rel = ["-d", "pandoc/defaults/common.yaml", "-d", "pandoc/defaults/web.yaml", *args[4:]]
    body = pandoc.blank_frontmatter((OK / "overview.md").read_text(encoding="utf-8"))
    html = pandoc.run(rel, stdin=body, cwd=ROOT).stdout
    assert '<figure class="sk-fig" data-slug="topic-map">' in html


# --- python helpers ---------------------------------------------------------------------


def test_argv_carries_the_metadata_contract(workdir):
    doc = document("mc/rc-filter.md", workdir, solutions="none")
    html = pandoc.argv(doc, "html")
    meta = dict(html[i + 1].split("=", 1) for i, a in enumerate(html) if a == "-M")
    assert set(meta) == {"sk-index", "sk-course", "sk-lang", "sk-file"}
    assert meta["sk-index"] == str(INDEX.resolve())
    assert meta["sk-file"] == "mc/rc-filter.md"
    assert html[1].endswith("pandoc/defaults/common.yaml")
    assert html[3].endswith("pandoc/defaults/web.yaml")
    typ = pandoc.argv(doc, "typst")
    meta = dict(typ[i + 1].split("=", 1) for i, a in enumerate(typ) if a == "-M")
    assert meta["sk-solutions"] == "none"
    assert Path(meta["sk-figdir"]).is_absolute()
    with pytest.raises(ValueError):
        pandoc.argv(doc, "pdf")  # type: ignore[arg-type]


def test_blank_frontmatter_keeps_line_numbers():
    text = "---\nid: x\ntitle: 'y'\n---\n\nBody\n"
    blanked = pandoc.blank_frontmatter(text)
    assert blanked.splitlines() == ["", "", "", "", "", "Body"]
    assert pandoc.blank_frontmatter("No frontmatter\n") == "No frontmatter\n"
    assert pandoc.blank_frontmatter("---\nunterminated\n") == "---\nunterminated\n"


def test_run_filtered_reads_course_and_language_from_the_index(workdir):
    html = pandoc.run_filtered(
        OK, "exercises/rc-filter/ex-rc-tp-grenzfrequenz.md", "html", index=INDEX
    )
    assert "<summary>Hinweis 1</summary>" in html
    assert "/c/rc-netzwerke/summary/rc-filter/" in html


# --- ok fixtures -------------------------------------------------------------------------


@pytest.mark.parametrize("rel", OK_FILES)
def test_ok_fixture_html(rel, workdir):
    body = pandoc.blank_frontmatter((OK / rel).read_text(encoding="utf-8"))
    html = pandoc.convert(body, document(rel, workdir), "html")
    check_html_contract(html)


@pytest.mark.parametrize("rel", OK_FILES)
def test_ok_fixture_json(rel, workdir):
    body = pandoc.blank_frontmatter((OK / rel).read_text(encoding="utf-8"))
    ast = json.loads(pandoc.convert(body, document(rel, workdir), "json"))
    # validation only: the AST is exactly what pandoc read, sourcepos included
    plain = pandoc.run(["-f", pandoc.READER + "+sourcepos", "-t", "json"], stdin=body).stdout

    def blocks(data: dict) -> str:  # data-pos names the input file (a temp file or none)
        return re.sub(r'"[^"]*@(\d+:\d+)', r'"\1', json.dumps(data["blocks"]))

    assert blocks(ast) == blocks(json.loads(plain))
    assert '"data-pos"' in blocks(ast)


@pytest.mark.parametrize("rel", OK_FILES)
@pytest.mark.parametrize("solutions", ["inline", "appendix", "none"])
def test_ok_fixture_typst_compiles(rel, solutions, workdir):
    body = pandoc.blank_frontmatter((OK / rel).read_text(encoding="utf-8"))
    typ = pandoc.convert(body, document(rel, workdir, solutions), "typst")
    assert '#import "/typst/studykit.typ": *' in typ
    compile_typst(typ, workdir, f"{rel.replace('/', '_')}-{solutions}")


# --- bad fixtures ------------------------------------------------------------------------


@pytest.mark.parametrize("path", BAD_FILES, ids=lambda p: p.stem)
def test_bad_fixture_fails_with_its_finding(path, workdir):
    text = path.read_text(encoding="utf-8")
    expect = yaml.safe_load(text.split("---\n")[1])
    body = pandoc.blank_frontmatter(text)
    for target in expect.get("targets", TARGETS):
        with pytest.raises(pandoc.FilterError) as info:
            pandoc.convert(body, document(expect["sk-file"], workdir), target)
        findings = info.value.findings
        assert findings, info.value.stderr
        for f in findings:
            m = pandoc.FINDING.match(f)
            assert m, f
            assert m["path"] == expect["sk-file"], f
            assert "(fix: " in m["message"], f
        # json runs with +sourcepos and must name the line; html and typst may not know it
        lines = {str(expect["line"])} if target == "json" else {str(expect["line"]), "0"}
        hits = [
            f
            for f in findings
            if (m := pandoc.FINDING.match(f))
            and m["code"] == expect["code"]
            and expect["message"] in m["message"]
            and m["line"] in lines
        ]
        assert hits, f"{target}: no {expect['code']} '{expect['message']}' on line {lines}:\n" + (
            "\n".join(findings)
        )


# --- golden corpora ----------------------------------------------------------------------


@pytest.mark.parametrize(("corpus", "file", "body"), GOLDEN_PARTS)
def test_golden_corpus(corpus, file, body, workdir):
    tree = check_html_contract(pandoc.convert(body, document(file, workdir), "html"))
    formulas = math_in(tree)
    errors = [
        (f.tex, e) for f, e in zip(formulas, golden.katex_check(ROOT, formulas), strict=True) if e
    ]
    assert not errors
    pandoc.convert(body, document(file, workdir), "json")
    for solutions in ("inline", "appendix"):
        typ = pandoc.convert(body, document(file, workdir, solutions), "typst")
        compile_typst(typ, workdir, f"golden-{corpus}-{file.replace('/', '_')}-{solutions}")


def test_golden_corpora_cover_every_block_and_mc_type(workdir):
    seen_blocks, seen_types, pinned = set(), set(), False
    for _, file, body in (p.values for p in GOLDEN_PARTS):
        tree = parse_html(pandoc.convert(body, document(file, workdir), "html"))
        seen_blocks |= {a.attrs["data-block"] for a in tree.iter("aside")}
        seen_blocks |= {d.classes()[0] for d in tree.iter("details")}
        seen_blocks |= {"mcq"} if tree.find_all("sk-mc") else set()
        seen_blocks |= {"figure"} if tree.find_all("figure") else set()
        for mc in tree.iter("sk-mc"):
            seen_types.add(mc.attrs["data-type"])
            pinned |= mc.attrs["data-pin-last"] == "true"
    assert seen_blocks == {
        "definition",
        "theorem",
        "example",
        "note",
        "warning",
        "takeaways",
        "sk-hint",
        "sk-solution",
        "mcq",
        "figure",
    }
    assert seen_types == {"single", "multi", "kprim"}
    assert pinned


# --- contract details --------------------------------------------------------------------


def test_html_blocks_hints_and_solutions(workdir):
    rel = "exercises/rc-filter/ex-rc-tp-grenzfrequenz.md"
    body = pandoc.blank_frontmatter((OK / rel).read_text(encoding="utf-8"))
    tree = parse_html(pandoc.convert(body, document(rel, workdir), "html"))
    hints = [d for d in tree.iter("details") if d.classes() == ["sk-hint"]]
    assert [h.attrs["data-index"] for h in hints] == ["1", "2"]
    assert [h.children[0].text for h in hints] == ["Hinweis 1", "Hinweis 2"]
    (solution,) = [d for d in tree.iter("details") if d.classes() == ["sk-solution"]]
    assert solution.children[0].tag == "summary" and solution.children[0].text == "Lösung"
    meta = sk_meta(tree)
    assert meta["items"] == [
        {
            "id": "ex-rc-tp-grenzfrequenz",
            "kind": "exercise",
            "topic": "rc-filter",
            "difficulty": None,
        }
    ]


def test_sk_meta_takes_the_difficulty_from_the_index_when_it_has_one(workdir):
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    data["items"]["ex-rc-tp-grenzfrequenz"]["difficulty"] = 3
    index = workdir / "index-difficulty.json"
    index.write_text(json.dumps(data), encoding="utf-8")
    rel = "exercises/rc-filter/ex-rc-tp-grenzfrequenz.md"
    doc = dataclasses.replace(document(rel, workdir), index=index)
    body = pandoc.blank_frontmatter((OK / rel).read_text(encoding="utf-8"))
    (item,) = sk_meta(parse_html(pandoc.convert(body, doc, "html")))["items"]
    assert item["difficulty"] == 3


def test_html_box_titles_and_defaults(workdir):
    body = "::: definition\n**Grenzfrequenz $f_g$**\n\nText.\n:::\n\n::: note\nOhne.\n:::\n"
    tree = parse_html(pandoc.convert(body, document("summary/02-rc-filter.md", workdir), "html"))
    titles = [a.children[0] for a in tree.iter("aside")]
    assert titles[0].all_text().split() == ["Grenzfrequenz"]
    assert titles[0].find_all("sk-math")
    assert titles[1].all_text().strip() == "Anmerkung"
    # the title paragraph is removed from the body
    first_box = next(tree.iter("aside"))
    assert len(first_box.find_all("p")) == 1


def test_english_labels(workdir):
    rel = "exercises/rc-filter/ex-rc-tp-grenzfrequenz.md"
    body = pandoc.blank_frontmatter((OK / rel).read_text(encoding="utf-8"))
    html = pandoc.convert(body, document(rel, workdir, lang="en"), "html")
    assert "<summary>Hint 2</summary>" in html and "<summary>Solution</summary>" in html
    typ = pandoc.convert(body, document(rel, workdir, "inline", lang="en"), "typst")
    assert "title: [Hint 1]" in typ and 'lang: "en"' in typ


def test_html_mcq_contract(workdir):
    body = pandoc.blank_frontmatter((OK / "mc/rc-filter.md").read_text(encoding="utf-8"))
    tree = parse_html(pandoc.convert(body, document("mc/rc-filter.md", workdir), "html"))
    mcs = tree.find_all("sk-mc")
    assert [m.attrs["data-id"] for m in mcs] == [
        "mc-rc-filter-003",
        "mc-rc-filter-011",
        "mc-rc-filter-020",
    ]
    first = mcs[0]
    assert first.attrs["data-topic"] == "rc-filter" and first.attrs["data-source"] == "uebung-04:2"
    assert [o.attrs["data-correct"] for o in first.find_all("sk-opt")] == [
        "true",
        "false",
        "false",
        "false",
    ]
    assert mcs[1].attrs["data-pin-last"] == "true"
    meta = sk_meta(tree)
    assert [(i["id"], i["kind"], i["difficulty"]) for i in meta["items"]] == [
        ("mc-rc-filter-003", "mc", 1),
        ("mc-rc-filter-011", "mc", 2),
        ("mc-rc-filter-020", "mc", 2),
    ]


@pytest.mark.parametrize("target", TARGETS)
def test_bare_urls_split_by_sourcepos_are_found(target, workdir):
    """+sourcepos splits `https://b.de` into Strs at every punctuation mark."""
    body = "Text.\n\nSiehe https://b.de und www.c.de hier, (https://d.de/x).\n"
    with pytest.raises(pandoc.FilterError) as info:
        pandoc.convert(body, document("summary/02-rc-filter.md", workdir), target)
    found = {
        (m["line"], m["col"], m["message"].split(" (fix:")[0])
        for f in info.value.findings
        if (m := pandoc.FINDING.match(f))
    }
    want = {("3", "7", "bare URL https://b.de"), ("3", "24", "bare URL www.c.de")}
    want.add(("3", "40", "bare URL https://d.de/x"))
    if target != "json":
        want = {("0", "0", message) for _, _, message in want}
    assert found == want


def test_html_refs_use_routes(workdir):
    body = pandoc.blank_frontmatter((OK / "summary/02-rc-filter.md").read_text(encoding="utf-8"))
    html = pandoc.convert(body, document("summary/02-rc-filter.md", workdir), "html")
    for snippet in (
        '<a class="sk-ref sk-ref-src" href="/c/rc-netzwerke/src/vl-05.pdf#page=14">',
        '<a class="sk-ref sk-ref-ex" href="/c/rc-netzwerke/exercises/ex-rc-tp-grenzfrequenz/">',
        '<a class="sk-ref sk-ref-topic" href="/c/rc-netzwerke/summary/gleichstrom/">',
        '<a class="sk-ref sk-ref-mc" href="/c/rc-netzwerke/mc/rc-filter/#mc-rc-filter-003">',
        '<a class="sk-ref sk-ref-exam" href="/c/rc-netzwerke/exams/probeklausur-1/">',
    ):
        assert snippet in html


def test_source_link_without_a_page_opens_the_pdf(workdir):
    body = "Siehe [Vorlesung](src:vl-05).\n"
    html = pandoc.convert(body, document("summary/02-rc-filter.md", workdir), "html")
    assert 'href="/c/rc-netzwerke/src/vl-05.pdf"' in html


def test_file_scope_skips_targets_the_index_lacks(workdir):
    """The quick lint of one edited file: links to parts not written yet are not errors."""
    body = (
        "Siehe [später](ex:ex-noch-nicht-da), [Thema](topic:kommt-noch) und"
        " [Folie](src:vl-99#p=3).\n\n![Bild](fig:kommt-noch)\n\nKaputt: [x](ex:Nicht_Kebab).\n"
    )
    doc = dataclasses.replace(document("summary/02-rc-filter.md", workdir), scope="file")
    assert pandoc.argv(doc, "json")[-2:] == ["-M", "sk-scope=file"]
    with pytest.raises(pandoc.FilterError) as info:
        pandoc.convert(body, doc, "json")
    assert len(info.value.findings) == 1
    assert "malformed link target `ex:Nicht_Kebab`" in info.value.findings[0]
    with pytest.raises(pandoc.FilterError) as info:
        pandoc.convert(body, dataclasses.replace(doc, scope="course"), "json")
    assert len(info.value.findings) == 5


def test_typst_figure_paths_are_relative_to_the_typst_root(workdir, tmp_path):
    body = "Text.\n\n![Bode-Diagramm](fig:rc-bode)\n"
    typ = pandoc.convert(body, document("summary/02-rc-filter.md", workdir), "typst")
    rel = (workdir / "figures").relative_to(ROOT).as_posix()
    assert f'image("/{rel}/rc-bode.svg", alt: "Bode-Diagramm")' in typ
    outside = dataclasses.replace(document("summary/02-rc-filter.md", workdir), figdir=tmp_path)
    with pytest.raises(pandoc.FilterError, match="outside the working directory"):
        pandoc.convert(body, outside, "typst")


# Minus signs are U+2212, accents combining marks (u + U+0302).
ALT_TEXT = [
    (r"\underline{U}_C", "U_C"),
    (r"U_\mathrm{C}", "U_C"),
    (r"\mathrm{k\Omega}", "kΩ"),
    (r"R = 3{,}3\,\mathrm{k\Omega}", "R = 3,3 kΩ"),
    (
        r"f_\mathrm{g} = \frac{1}{2\pi R C} \approx 1{,}59\,\mathrm{kHz}",
        "f_g = 1/(2πRC) ≈ 1,59 kHz",
    ),
    (r"\frac{U_2}{U_1} = \frac{1}{\sqrt{2}}", "U_2/U_1 = 1/√2"),
    (r"\omega\tau = 1", "ωτ = 1"),
    (r"\varphi = -56{,}3^\circ", "φ = \u221256,3°"),
    (r"10^{-3}\,\mathrm{A}", "10⁻³ A"),
    (r"\mathrm{e}^{-t/\tau}", "e^(\u2212t/τ)"),
    (r"\lvert\underline{H}(\mathrm{j}\omega)\rvert", "|H(jω)|"),
    (r"\sqrt{R^2 + X_L^2}", "√(R² + X_L²)"),
    (r"\left. \frac{dU}{dt} \right|_{t=0}", "dU/dt|_(t = 0)"),
    (r"u(t) = \hat{u}\sin(\omega t + \varphi_u)", "u(t) = u\u0302 sin(ωt + φ_u)"),
    (r"\text{für } t > 0", "für t > 0"),
    (r"A^\mathrm{T},\ x \in \mathbb{R}", "Aᵀ, x ∈ \u211d"),
]


def test_alt_text_reads_math_as_text(tmp_path):
    """lib/alttext.lua turns TeX into the plain text a screen reader gets as alt text."""
    driver = tmp_path / "alttext.lua"
    driver.write_text(
        "package.path = arg[1] .. '/?.lua;' .. package.path\n"
        "local alttext = require 'lib.alttext'\n"
        "local out = {}\n"
        "for i = 2, #arg do out[#out + 1] = alttext.tex(arg[i]) end\n"
        "print(pandoc.json.encode(out))\n",
        encoding="utf-8",
    )
    tex = [t for t, _ in ALT_TEXT]
    proc = pandoc.run(["lua", str(driver), str(ROOT / "pandoc" / "filters"), *tex])
    assert dict(zip(tex, json.loads(proc.stdout), strict=True)) == dict(ALT_TEXT)


def test_figure_caption_math_is_rendered_and_read_as_text_in_the_alt(workdir):
    body = (
        "Text.\n\n"
        r"![Spannung $\underline{U}_C$ am Kondensator mit $C = 47\,\mathrm{nF}$](fig:rc-bode)"
        "\n"
    )
    doc = document("summary/02-rc-filter.md", workdir)
    typ = pandoc.convert(body, doc, "typst")
    assert 'alt: "Spannung U_C am Kondensator mit C = 47 nF")' in typ
    assert "caption: [Spannung $underline(U)_C$ am Kondensator" in typ
    compile_typst(typ, workdir, "figure-caption-math")
    tree = check_html_contract(pandoc.convert(body, doc, "html"))
    (caption,) = tree.find_all("figcaption")
    assert [m.attrs["data-display"] for m in caption.find_all("sk-math")] == ["0", "0"]
    pandoc.convert(body, doc, "json")


def test_typst_refs_link_inside_the_document_or_name_the_target(workdir):
    body = pandoc.blank_frontmatter((OK / "mc/rc-filter.md").read_text(encoding="utf-8"))
    typ = pandoc.convert(body, document("mc/rc-filter.md", workdir), "typst")
    assert "#link(<mc-rc-filter-003>)[die erste Frage]" in typ
    body = "Siehe [Übung](ex:ex-spannungsteiler).\n"
    typ = pandoc.convert(body, document("summary/02-rc-filter.md", workdir), "typst")
    assert "Übung (→ Übung: Belasteter Spannungsteiler)" in typ


def test_typst_math_fixups():
    tex = r"u(t) = \begin{cases} 1{,}5 & t < 0 \\ 0 & \text{sonst} \end{cases}"
    doc = pandoc.Document(course="c", lang="de", file="summary/01-x.md", index=INDEX)
    typ = pandoc.convert(f"$$\n{tex}\n$$\n", doc, "typst")
    assert '1","5' in typ and "1\\,5" not in typ
    assert 'cases(delim: "{", 1","5 & quad t < 0, 0 & quad upright("sonst"))' in typ


# One table for both engines (validate.thin_space_in_number and math.lua).
THIN_SPACES = [
    (r"10\,000", r"0\,0"),
    (r"1\,5\,\mathrm{V}", r"1\,5"),
    (r"x_{1 \, 2}", r"1\,2"),
    ("1\\, % a comment\n5", r"1\,5"),
    (r"R = 10{\,}000", r"0{\,}0"),  # a group of spaces
    (r"R = 10{\,\,}000", r"0{\,\,}0"),
    (r"R = 10\thinspace 000", r"0\thinspace0"),
    (r"R = 10\medspace 000", r"0\medspace0"),
    (r"R = 10\thickspace 000", r"0\thickspace0"),
    (r"R = 10\:000", r"0\:0"),
    (r"R = 10\;000", r"0\;0"),
    (r"R = 10\>000", r"0\>0"),
    (r"R = 10~000", r"0~0"),
    (r"R = 10\ 000", r"0\ 0"),
    (r"R = 1\,{\;}5", r"1\,{\;}5"),
    (r"3{,}3\,\mathrm{k\Omega} + 470\,\Omega", None),
    (r"10^4\,\mathrm{Hz} = 10000\,\mathrm{Hz}", None),
    (r"\lambda_{1{,}2} = a\,b", None),
    (r"U_2 = 2\cdot 3\,\mathrm{V}", None),
    (r"x^{2}\,3 + 2~\mathrm{V} + a\;b", None),  # a closing brace ends the number
    (r"1{,}5\;\mathrm{mA} \cdot 2\ \text{s}", None),
]


@pytest.mark.parametrize(("tex", "number"), THIN_SPACES)
def test_validate_and_the_filter_agree_on_thin_spaces_in_numbers(tex, number, workdir):
    """SK-MATH-THINSPACE: one token rule in validate and math.lua."""
    assert validate.thin_space_in_number(tex) == number
    doc = document("summary/02-rc-filter.md", workdir)
    if number is None:
        pandoc.convert(f"Text ${tex}$.\n", doc, "json")
        return
    with pytest.raises(pandoc.FilterError) as info:
        pandoc.convert(f"Text ${tex}$.\n", doc, "json")
    # \thinspace and \thickspace also fail the Typst conversion (SK-MATH)
    (f,) = [f for f in info.value.findings if " SK-MATH-THINSPACE " in f]
    assert f" SK-MATH-THINSPACE space between two digits ({number}) in $" in f
    assert f.endswith("(fix: write 10000, 10^4, or {,} for a decimal comma)")


def test_golden_math_corpus_has_no_thin_space_in_a_number():
    tex = [t for t, _ in pandoc.math_nodes((GOLDEN / "math.md").read_text(encoding="utf-8"))]
    assert len(tex) > 100
    assert [t for t in tex if validate.thin_space_in_number(t)] == []


def test_typst_decimal_comma_fixup_leaves_thin_spaces_alone():
    """pandoc writes TeX \\, as Typst `thin` and only {,} as `\\,`, which the fix-up rewrites."""
    doc = pandoc.Document(course="c", lang="de", file="summary/01-x.md", index=INDEX)
    typ = pandoc.convert("$3{,}3\\,\\mathrm{k\\Omega}$\n", doc, "typst")
    assert '3","3 thin upright(k Omega)' in typ


def test_typst_mcq_shuffle_is_deterministic_and_keeps_pin_last(workdir):
    body = pandoc.blank_frontmatter((OK / "mc/rc-filter.md").read_text(encoding="utf-8"))
    runs = [pandoc.convert(body, document("mc/rc-filter.md", workdir), "typst") for _ in range(2)]
    assert runs[0] == runs[1]
    calls = [c.split("explanation:")[0] for c in runs[0].split("#sk-mcq(")[1:4]]
    orders = [re.findall(r'\(key: "([A-F])", text: \[(.*?)\], correct', c, re.S) for c in calls]
    assert [len(o) for o in orders] == [4, 4, 4]
    # the single-choice question is shuffled away from source order
    assert orders[0][0][1] != '$1","59 thin upright(k H z)$'
    # pin-last: "Keine der Aussagen ist richtig." stays last
    assert orders[1][-1][1] == "Keine der Aussagen ist richtig."
    assert all([k for k, _ in o] == ["A", "B", "C", "D"] for o in orders)


def test_typst_solution_modes(workdir):
    rel = "exercises/rc-filter/ex-rc-tp-grenzfrequenz.md"
    body = pandoc.blank_frontmatter((OK / rel).read_text(encoding="utf-8"))
    inline = pandoc.convert(body, document(rel, workdir, "inline"), "typst")
    appendix = pandoc.convert(body, document(rel, workdir, "appendix"), "typst")
    none = pandoc.convert(body, document(rel, workdir, "none"), "typst")
    assert "#sk-hint(index: 2" in inline and "#sk-solution(" in inline
    assert "#sk-appendix(" not in inline
    assert "#metadata(" in appendix and "back: <ex-rc-tp-grenzfrequenz>" in appendix
    assert appendix.index("#sk-appendix(title: [Hinweise])") < appendix.index(
        "#sk-appendix(title: [Lösungen])"
    )
    assert "Wirk- und Blindwiderstand" not in none and "#sk-appendix(" not in none


def test_typst_mcq_answer_key_modes(workdir):
    body = pandoc.blank_frontmatter((OK / "mc/rc-filter.md").read_text(encoding="utf-8"))
    for mode, keys in (("inline", 0), ("appendix", 3), ("none", 0)):
        typ = pandoc.convert(body, document("mc/rc-filter.md", workdir, mode), "typst")
        assert typ.count("#sk-mcq-key(") == keys
        assert typ.count(f'answers: "{mode}"') == 3


# --- math denylist -----------------------------------------------------------------------

# One sample formula per denylist token; the kind test runs them through both engines.
SAMPLES = {
    r"\overset": r"a \overset{!}{=} b",
    r"\stackrel": r"a \stackrel{!}{=} b",
    r"\underset": r"\underset{x}{\max} f",
    r"\xrightarrow": r"a \xrightarrow{t} b",
    r"\xleftarrow": r"a \xleftarrow{t} b",
    r"\color": r"\color{red} x",
    r"\textcolor": r"\textcolor{red}{x}",
    r"\tag": r"x = 1 \tag{1}",
    r"\label": r"x = 1 \label{eq:a}",
    r"\eqref": r"\eqref{eq:a}",
    r"\ref": r"\ref{eq:a}",
    "env:vmatrix": r"\begin{vmatrix} a & b \\ c & d \end{vmatrix}",
    "env:Vmatrix": r"\begin{Vmatrix} a & b \\ c & d \end{Vmatrix}",
    "env:matrix": r"\begin{matrix} a & b \\ c & d \end{matrix}",
    "env:array": r"\begin{array}{cc} a & b \\ c & d \end{array}",
    r"\hline": r"\left(\begin{array}{cc} a & b \\ \hline c & d \end{array}\right)",
    r"\big": r"\big( x \big)",
    r"\Big": r"\Big( x \Big)",
    r"\bigg": r"\bigg( x \bigg)",
    r"\Bigg": r"\Bigg( x \Bigg)",
    r"\bigl": r"\bigl( x \bigr)",
    r"\bigr": r"x \bigr)",
    r"\bigm": r"a \bigm| b",
    r"\Bigl": r"\Bigl( x \Bigr)",
    r"\Bigr": r"x \Bigr)",
    r"\Bigm": r"a \Bigm| b",
    r"\biggl": r"\biggl( x \biggr)",
    r"\biggr": r"x \biggr)",
    r"\biggm": r"a \biggm| b",
    r"\Biggl": r"\Biggl( x \Biggr)",
    r"\Biggr": r"x \Biggr)",
    r"\Biggm": r"a \Biggm| b",
    r"\|": r"\| x \|_2",
    r"\left\lVert": r"\left\lVert x \right\rVert_2",
    r"\mathsf": r"A^\mathsf{T}",
    r"\operatorname*": r"\operatorname*{arg\,max}_x f(x)",
    r"\limits": r"\sum\limits_{k=1}^{n} k",
    r"\SI": r"\SI{3}{\volt}",
    r"\qty": r"\qty{3}{V}",
    r"\si": r"\si{\volt}",
    r"\R": r"x \in \R",
    r"\N": r"n \in \N",
    r"\ce": r"\ce{H2O}",
    r"\pu": r"\pu{3 V}",
    r"\def": r"\def\foo{x}\foo",
    r"\gdef": r"\gdef\foo{x}\foo",
    r"\edef": r"\edef\foo{x}\foo",
    r"\let": r"\let\foo\bar",
    r"\newcommand": r"\newcommand{\foo}{x} \foo",
    r"\renewcommand": r"\renewcommand{\vec}{x} \vec",
    r"\providecommand": r"\providecommand{\foo}{x}\foo",
    r"\DeclareMathOperator": r"\DeclareMathOperator{\sgn}{sgn}",
}

# docs/architecture.md §2.3: the denied table and "Verified in Phase 1".
SPEC_TOKENS = {
    r"\overset",
    r"\stackrel",
    r"\xrightarrow",
    r"\color",
    r"\textcolor",
    r"\tag",
    r"\label",
    r"\eqref",
    r"\ref",
    "env:vmatrix",
    "env:Vmatrix",
    "env:matrix",
    "env:array",
    r"\hline",
    r"\big",
    r"\bigg",
    r"\|",
    r"\left\lVert",
    r"\mathsf",
    r"\operatorname*",
    r"\limits",
    r"\SI",
    r"\qty",
    r"\si",
    r"\R",
    r"\N",
    r"\ce",
    r"\pu",
    r"\def",
    r"\newcommand",
}


def denylist() -> list[dict]:
    return json.loads(DENYLIST.read_text(encoding="utf-8"))


def test_denylist_shape_and_spec_coverage():
    entries = denylist()
    tokens = [e["token"] for e in entries]
    assert len(tokens) == len(set(tokens))
    assert set(tokens) >= SPEC_TOKENS
    assert set(tokens) == set(SAMPLES)
    for e in entries:
        assert set(e) <= {"token", "use", "kind", "unless_wrapped"}
        assert e["kind"] in {"silent", "fails"} and e["use"]
        assert e["token"].startswith(("\\", "env:"))


def test_every_denied_token_is_reported_with_its_replacement(workdir):
    entries = denylist()
    body = "\n\n".join(f"$${SAMPLES[e['token']]}$$" for e in entries) + "\n"
    with pytest.raises(pandoc.FilterError) as info:
        pandoc.convert(body, document("summary/02-rc-filter.md", workdir), "json")
    findings = info.value.findings
    for e in entries:
        what = (
            f"environment {e['token'][4:]} is not allowed in $"
            if e["token"].startswith("env:")
            else f"`{e['token']}` is not allowed in $"
        )
        assert any(what in f and f.endswith(f"(fix: {e['use']})") for f in findings), e["token"]


def test_golden_math_corpus_passes_the_filter(workdir):
    """No false positives on the allowed dialect, and the fixed-up Typst still compiles."""
    body = re.sub(r"(?m)^# .*$", "", (GOLDEN / "math.md").read_text(encoding="utf-8"))
    doc = document("summary/02-rc-filter.md", workdir)
    pandoc.convert(body, doc, "json")
    compile_typst(pandoc.convert(body, doc, "typst"), workdir, "golden-math")


def test_control_words_match_exactly(workdir):
    body = r"$\sin x + \Rightarrow + \limsup_n a_n + \Re z + \mathrm{N}$" + "\n"
    pandoc.convert(body, document("summary/02-rc-filter.md", workdir), "json")


WRAPPED_MATRICES = [
    r"\left|\begin{matrix} a & b \\ c & d \end{matrix}\right|",
    r"\left(\begin{matrix} a \\ b \end{matrix}\right)",
    r"\left[\begin{matrix} a & b \\ c & d \end{matrix}\right]",
    r"\left\{\begin{matrix} a & b \\ c & d \end{matrix}\right\}",
    r"\left( % a comment" "\n" r"\begin{matrix} a \\ b \end{matrix} \right)",
]


@pytest.mark.parametrize("tex", WRAPPED_MATRICES)
def test_wrapped_matrix_is_allowed(tex, workdir):
    """unless_wrapped lists pairs that pandoc turns into a Typst matrix (or a vector)."""
    doc = document("summary/02-rc-filter.md", workdir)
    pandoc.convert(f"$${tex}$$\n", doc, "json")
    assert re.search(r"\b(mat|vec)\(", pandoc.convert(f"$${tex}$$\n", doc, "typst"))


DENY_USE = {e["token"]: e["use"] for e in json.loads(DENYLIST.read_text(encoding="utf-8"))}
MATRIX_FIX = DENY_USE["env:matrix"]
VMATRIX_FIX = DENY_USE["env:vmatrix"]
ALLOWLIST_FIX = "use aligned, gathered, cases, pmatrix, bmatrix or Bmatrix"


REJECTED_ENVIRONMENTS = [
    # silently become alignment rows (or a stray "[r]") in Typst
    (r"\begin{matrix*} a & b \\ c & d \end{matrix*}", "matrix*", MATRIX_FIX),
    (r"\begin{matrix*}[r] a & b \\ c & d \end{matrix*}", "matrix*", MATRIX_FIX),
    (r"\left(\begin{matrix*}[r] a & b \end{matrix*}\right)", "matrix*", MATRIX_FIX),
    (r"\begin{smallmatrix} a & b \\ c & d \end{smallmatrix}", "smallmatrix", ALLOWLIST_FIX),
    # pass the Typst conversion, then fail typst compile
    (r"\begin{vmatrix*} a & b \\ c & d \end{vmatrix*}", "vmatrix*", VMATRIX_FIX),
    (r"\begin{Vmatrix*} a & b \\ c & d \end{Vmatrix*}", "Vmatrix*", VMATRIX_FIX),
    # outside the allowlist of docs/architecture.md §2.3
    (r"\begin{align} a &= b \end{align}", "align", ALLOWLIST_FIX),
    (r"\begin{gather} a \\ b \end{gather}", "gather", ALLOWLIST_FIX),
    (r"\begin{alignat}{2} a &= b \end{alignat}", "alignat", ALLOWLIST_FIX),
    (r"\begin{split} a &= b \end{split}", "split", ALLOWLIST_FIX),
    (r"\begin{equation} a = b \end{equation}", "equation", ALLOWLIST_FIX),
    (r"\begin { align } a &= b \end{align}", "align", ALLOWLIST_FIX),
    # a matrix counts as wrapped only between a listed \left…\right pair
    (r"\left.\begin{matrix} a \\ b \end{matrix}\right\}", "matrix", MATRIX_FIX),
    (r"\left\langle\begin{matrix} a \\ b \end{matrix}\right\rangle", "matrix", MATRIX_FIX),
    (r"\left[\begin{matrix} a \\ b \end{matrix}\right)", "matrix", MATRIX_FIX),
    (r"\left( x + \begin{matrix} a \\ b \end{matrix}\right)", "matrix", MATRIX_FIX),
    # an array drops its column spec in Typst, wrapped or not
    (r"\left[\begin{array}{rl} 10 & 1 \\ 1 & 10 \end{array}\right]", "array", None),
    (r"\left(\begin{matrix} \begin{matrix} 1 \end{matrix} \end{matrix}\right)", "matrix", None),
]


@pytest.mark.parametrize(("tex", "env", "fix"), REJECTED_ENVIRONMENTS)
def test_environments_outside_the_allowlist_are_reported(tex, env, fix, workdir):
    with pytest.raises(pandoc.FilterError) as info:
        pandoc.convert(f"$${tex}$$\n", document("summary/02-rc-filter.md", workdir), "json")
    hits = [f for f in info.value.findings if f"environment {env} is not allowed in $" in f]
    assert hits, info.value.findings
    if fix is not None:
        assert hits[0].endswith(f"(fix: {fix})"), hits[0]


def validate_rejects(tex: str) -> bool:
    """The verdict of `studykit validate` (SK-MATH-DENIED or SK-MATH-ENV) on one formula."""
    entries = validate.load_denylist(DENYLIST)
    envs = validate._environments(tex, validate._wraps(entries))
    return bool(validate.denied(tex, entries)) or any(
        not wrapped and name not in validate.ALLOWED_ENVS for name, wrapped in envs
    )


@pytest.mark.parametrize(
    ("tex", "rejected"),
    [(t, False) for t in WRAPPED_MATRICES] + [(t, True) for t, _, _ in REJECTED_ENVIRONMENTS],
)
def test_validate_and_the_filter_agree_on_environments(tex, rejected):
    """validate reads unless_wrapped from the same denylist, so both give one verdict."""
    assert validate_rejects(tex) is rejected


def test_allowed_environments_pass(workdir):
    body = "\n\n".join(
        f"$$\\begin{{{env}}} a & b \\\\ c & d \\end{{{env}}}$$"
        for env in ("aligned", "gathered", "cases", "pmatrix", "bmatrix", "Bmatrix")
    )
    pandoc.convert(body + "\n", document("summary/02-rc-filter.md", workdir), "json")


def typst_fails(tex: str, workdir: Path) -> bool:
    try:
        typ = pandoc.run(
            ["-f", pandoc.READER, "-t", "typst", "--standalone", "--fail-if-warnings"],
            stdin=f"$${tex}$$\n",
        ).stdout
    except pandoc.PandocError:
        return True
    try:
        compile_typst(typ, workdir, "denylist-kind")
    except AssertionError:
        return True
    return False


def test_denylist_kind_matches_the_engines(workdir):
    """'fails' breaks KaTeX or pandoc→Typst; 'silent' passes both, so only the lint helps."""
    entries = denylist()
    formulas = [golden.Formula(SAMPLES[e["token"]], True) for e in entries]
    katex = golden.katex_check(ROOT, formulas)
    wrong = []
    for e, f, k in zip(entries, formulas, katex, strict=True):
        fails = k is not None or typst_fails(f.tex, workdir)
        if fails != (e["kind"] == "fails"):
            wrong.append((e["token"], e["kind"], "fails" if fails else "passes both engines"))
    assert not wrong
