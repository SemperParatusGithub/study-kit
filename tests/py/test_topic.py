"""A topic (`kind: topic`, docs/architecture.md §5.6): what its course.yaml may hold, what
validate asks of it, its flash cards, its material and the pipeline's steps. The mini topic
in tests/fixtures/courses/mini-topic is clean; each test breaks one thing in a copy."""

from __future__ import annotations

import io
import json
import shutil
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest
from PIL import Image
from pydantic import ValidationError

import materials
from conftest import FIXTURES
from studykit import cli, content, index, ingest, model, pipeline, progress, render, tools, validate

MINI_TOPIC = FIXTURES / "courses" / "mini-topic"
TOPIC = {
    "schema": 1,
    "kind": "topic",
    "id": "x-topic",
    "title": "X",
    "lang": "en",
    "topics": [{"id": "a", "title": "A", "weight": 1, "prereq": []}],
}


def run(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cli.main(list(argv))
    return code, out.getvalue(), err.getvalue()


@pytest.fixture
def courses(tmp_path: Path, monkeypatch) -> Path:
    path = tmp_path / "courses"
    path.mkdir()
    monkeypatch.setenv("STUDYKIT_COURSES_DIR", str(path))
    return path


@pytest.fixture
def topic(courses: Path) -> Path:
    target = courses / "mini-topic"
    shutil.copytree(MINI_TOPIC, target, ignore=shutil.ignore_patterns("_build"))
    return target


def check(course: Path, denylist: Path | None = None, **kw) -> validate.Report:
    config = validate.Config(denylist=denylist, katex=False, figures=False, pdf=False, site=False)
    return validate.validate([course], config=config, **kw)


def codes(report: validate.Report) -> set[str]:
    return {f.code for f in report.findings}


# --- course.yaml ------------------------------------------------------------------------------


def test_a_course_without_kind_stays_a_course_and_needs_its_exam():
    data = {**TOPIC, "exam": {"format": "written"}}
    del data["kind"]
    course = model.validate_course(data)
    assert course.kind == "course" and not course.is_topic and course.contents is None
    del data["exam"]
    with pytest.raises(ValidationError, match="exam"):
        model.validate_course(data)


def test_a_topic_has_contents_and_no_exam():
    course = model.validate_course(TOPIC)
    assert course.is_topic and course.exam is None
    assert course.contents == model.TopicContents(cards=True, glossary=True, concept_map=True)


@pytest.mark.parametrize(
    "extra",
    [
        {"exam": {"format": "written"}},
        {"study": {"hours_per_week": 3}},
        {"cheatsheet": {"allowed": True, "max_pages": 1}},
    ],
)
def test_a_topic_refuses_what_only_a_course_has(extra: dict):
    with pytest.raises(ValidationError, match=r"a topic has no"):
        model.validate_course({**TOPIC, **extra})


def test_a_course_refuses_contents():
    data = {**TOPIC, "kind": "course", "exam": {"format": "written"}, "contents": {"cards": True}}
    with pytest.raises(ValidationError, match="only for kind: topic"):
        model.validate_course(data)


# --- validate ---------------------------------------------------------------------------------


def test_the_mini_topic_is_clean_also_for_release(topic: Path, denylist: Path):
    assert check(topic, denylist).findings == []
    assert check(topic, denylist, release=True).findings == []


def test_index_lists_the_cards(topic: Path):
    items = index.build(content.CourseTree(topic))["items"]
    assert items["card-basics-001"]["kind"] == "card"
    assert items["card-basics-001"]["topic"] == "basics"


@pytest.mark.parametrize(
    ("rel", "text"),
    [
        ("plan.yaml", "schema: 1\ncourse: mini-topic\nsessions: []\n"),
        ("mc/basics.md", "---\ntopic: basics\ntitle: MC\n---\n"),
        ("cheatsheet.md", "---\ntitle: S\nmax_pages: 1\n---\n"),
        ("analysis/notation.yaml", "schema: 1\n"),
    ],
)
def test_course_files_in_a_topic_are_refused(topic: Path, denylist: Path, rel: str, text: str):
    path = topic / rel
    path.parent.mkdir(exist_ok=True)
    path.write_text(text)
    assert "SK-STRUCT-KIND" in codes(check(topic, denylist))


CARD_FILE = """---
topic: basics
title: Cards
---

{body}
"""


@pytest.mark.parametrize(
    ("body", "code"),
    [
        (":::: {.flashcard #card-basics-1}\nFront?\n\n::: back\nBack.\n:::\n::::", "SK-CARD-ID"),
        (":::: {.flashcard #card-other-001}\nFront?\n\n::: back\nBack.\n:::\n::::", "SK-CARD-ID"),
        (":::: {.flashcard #card-basics-001}\n::: back\nBack.\n:::\n::::", "SK-CARD-FRONT"),
        (":::: {.flashcard #card-basics-001}\nFront?\n::::", "SK-CARD-BACK"),
        (":::: {.flashcard #card-basics-001}\nFront?\n\n::: back\n:::\n::::", "SK-CARD-BACK"),
        (
            ":::: {.flashcard #card-basics-001}\nFront?\n\n::: back\nA.\n:::\n\n"
            "::: back\nB.\n:::\n::::",
            "SK-CARD-BACK",
        ),
        (
            ':::: {.flashcard #card-basics-001 box="2"}\nFront?\n\n::: back\nBack.\n:::\n::::',
            "SK-CARD-ATTR",
        ),
        (
            "Loose text.\n\n:::: {.flashcard #card-basics-001}\nF?\n\n::: back\nB.\n:::\n::::",
            "SK-CARD-FORMAT",
        ),
        (
            ":::: {.flashcard #card-basics-001}\nF?\n\n::: back\nB.\n:::\n\nMore.\n::::",
            "SK-CARD-FORMAT",
        ),
    ],
)
def test_a_broken_card_gets_its_code(topic: Path, denylist: Path, body: str, code: str):
    (topic / "cards" / "basics.md").write_text(CARD_FILE.format(body=body))
    assert code in codes(check(topic, denylist, quick=True))


def test_a_card_id_used_twice_is_a_duplicate(topic: Path, denylist: Path):
    bank = topic / "cards" / "basics.md"
    bank.write_text(bank.read_text().replace("card-basics-002", "card-basics-001"))
    assert "SK-STRUCT-DUP" in codes(check(topic, denylist, quick=True))


def test_a_flashcard_outside_a_card_file_is_misplaced(topic: Path, denylist: Path):
    chapter = topic / "summary" / "01-basics.md"
    chapter.write_text(
        chapter.read_text()
        + "\n:::: {.flashcard #card-basics-009}\nF?\n\n::: back\nB.\n:::\n::::\n"
    )
    assert "SK-BLOCK-PLACEMENT" in codes(check(topic, denylist, quick=True))


def test_the_overview_of_a_topic_has_its_own_sections(topic: Path, denylist: Path):
    overview = topic / "overview.md"
    text = overview.read_text()
    overview.write_text(
        text.replace("## Concept map\n\n![How the chapters connect](fig:topic-map)\n\n", "")
    )
    assert "SK-STRUCT-SECTIONS" in codes(check(topic, denylist, quick=True))
    course = topic / "course.yaml"
    course.write_text(course.read_text().replace("concept_map: true", "concept_map: false"))
    assert "SK-STRUCT-SECTIONS" not in codes(check(topic, denylist, quick=True))


def test_coverage_asks_for_what_contents_chose(topic: Path, denylist: Path):
    (topic / "cards" / "details.md").unlink()
    chapter = topic / "summary" / "02-details.md"
    chapter.write_text(chapter.read_text().replace("**Ähnliches Detail**\n\n", ""))
    found = codes(check(topic, denylist, release=True))
    assert {"SK-COV-CARDS", "SK-COV-GLOSSARY"} <= found
    course = topic / "course.yaml"
    course.write_text(
        course.read_text()
        .replace("cards: true", "cards: false")
        .replace("glossary: true", "glossary: false")
    )
    assert not {"SK-COV-CARDS", "SK-COV-GLOSSARY"} & codes(check(topic, denylist, release=True))


def test_a_concept_map_needs_two_chapters(topic: Path, denylist: Path):
    course = topic / "course.yaml"
    course.write_text(
        course.read_text().replace(
            "  - {id: details, title: Details, weight: 0.5, prereq: [basics]}\n", ""
        )
    )
    (topic / "summary" / "02-details.md").unlink()
    (topic / "cards" / "details.md").unlink()
    (topic / "overview.md").write_text(
        (topic / "overview.md").read_text().replace("[Details](topic:details)", "Details")
    )
    assert "SK-COV-CONCEPT-MAP" in codes(check(topic, denylist, release=True))


# --- rendering --------------------------------------------------------------------------------


@pytest.mark.skipif(not tools.bin_path(tools.repo_root(), "pandoc").exists(), reason="no pandoc")
def test_cards_render_to_their_html_contract(topic: Path):
    result = render.render_course(topic, paths=["cards/basics.md"])
    (file,) = result["files"]
    assert file["kind"] == "cards" and file["findings"] == []
    assert '<sk-card data-id="card-basics-001" data-topic="basics">' in file["html"]
    assert '<div class="sk-card-front">' in file["html"]
    assert '<div class="sk-card-back">' in file["html"]


# --- progress ---------------------------------------------------------------------------------


def test_progress_validates_and_merges_card_entries():
    doc = {
        "schema": "studykit-progress/1",
        "course": "mini-topic",
        "exported_at": "2026-11-03T10:00:00Z",
        "items": {
            "card:card-basics-001": {"h": "aaaaaaaa", "box": 2, "due": "2026-11-05", "reviews": 2}
        },
    }
    assert model.Progress.model_validate(doc).items["card:card-basics-001"].reviews == 2
    more = json.loads(json.dumps(doc))
    more["items"]["card:card-basics-001"].update(box=3, due="2026-11-12", reviews=3)
    merged, added, count = progress.merge(doc, more)
    assert (added, count) == (0, 1)
    assert merged["items"]["card:card-basics-001"]["reviews"] == 3
    merged, _, _ = progress.merge(more, doc)
    assert merged["items"]["card:card-basics-001"]["reviews"] == 3


# --- refusals ---------------------------------------------------------------------------------


def test_status_and_plan_say_a_topic_has_neither(topic: Path):
    code, _, err = run("status", "mini-topic")
    assert code == 2 and "is a topic" in err
    code, _, err = run("plan", "mini-topic")
    assert code != 0 and "no exam and no study plan" in err


# --- material ---------------------------------------------------------------------------------


@pytest.fixture
def mixed(tmp_path: Path) -> Path:
    """A folder with every kind of material, and what a topic leaves out."""
    folder = tmp_path / "Material"
    folder.mkdir()
    (folder / "notes.txt").write_text(
        "Grüße: ein Text über Blöcke.\n\n#hash $x$ *stern* [klammer]\n"
    )
    (folder / "more.md").write_text("# Heading\n\nA short markdown note.\n")
    (folder / "chart.png").write_bytes(_image("PNG"))
    (folder / "photo.jpg").write_bytes(_image("JPEG"))
    (folder / "old.tiff").write_bytes(_image("TIFF"))
    (folder / "bad.txt").write_bytes(b"\xff\xfe\x00 not utf-8")
    (folder / "empty.md").write_text("   \n")
    (folder / "slides.pptx").write_text("no")
    (folder / "data.xyz").write_text("no")
    materials.text_pdf(
        folder / "script.pdf", ["Page one of the script.", "Page two of the script."]
    )
    return folder


def _image(fmt: str) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (64, 32), (200, 220, 240)).save(out, fmt)
    return out.getvalue()


def test_a_topic_reads_text_images_and_pdfs(mixed: Path):
    sc = ingest.scan(mixed, topic=True)
    docs = {c.origin: c for c in sc.documents}
    assert set(docs) == {"notes.txt", "more.md", "chart.png", "photo.jpg", "script.pdf"}
    assert {c.kind for c in docs.values()} == {"other"}
    assert not any(row["uncertain"] for row in sc.to_json()["documents"])
    # a text keeps its characters literally, and even a short one is no picture
    page = docs["notes.txt"].info.pages[0]
    assert "#hash $x$ *stern* [klammer]" in page.text and "Grüße" in page.text
    assert not page.visual and not page.scanned
    assert not docs["more.md"].info.pages[0].visual
    # an image is a page without text, which the ingester transcribes
    assert docs["chart.png"].info.pages[0].scanned
    assert docs["notes.txt"].source_sha256 == ingest.sha256_file(mixed / "notes.txt")
    assert docs["script.pdf"].source_sha256 is None
    skipped = {s.origin: s.reason for s in sc.skipped}
    assert skipped == {
        "bad.txt": "unreadable",
        "empty.md": "unreadable",
        "old.tiff": "image",
        "slides.pptx": "unsupported",
        "data.xyz": "ignored",
    }
    assert {f.code for f in sc.findings} == {"SK-INGEST-CONVERT", "SK-INGEST-UNSUPPORTED"}


def test_a_course_still_takes_only_pdfs(mixed: Path):
    sc = ingest.scan(mixed)
    assert [c.origin for c in sc.documents] == ["script.pdf"]
    assert {s.origin: s.reason for s in sc.skipped}["chart.png"] == "image"


def test_characters_the_fonts_lack_are_reported(tmp_path: Path):
    (tmp_path / "emoji.txt").write_text("A note with an emoji 🙂 in it.\n")
    sc = ingest.scan(tmp_path / "emoji.txt", topic=True)
    assert [c.origin for c in sc.documents] == ["emoji.txt"]
    (finding,) = [f for f in sc.findings if f.code == "SK-INGEST-CONVERT"]
    assert "🙂" in finding.message and finding.severity == "warning"


def test_nothing_readable_stops_the_scan(tmp_path: Path):
    (tmp_path / "data.xyz").write_text("no")
    sc = ingest.scan(tmp_path, topic=True)
    assert [f.code for f in sc.findings if f.is_error] == ["SK-INGEST-FOLDER"]
    missing = ingest.scan([tmp_path / "gone", tmp_path], topic=True)
    assert [f.code for f in missing.findings if f.is_error] == ["SK-INGEST-FOLDER"]


def test_ingest_topic_copies_extracts_and_resumes(courses: Path, mixed: Path):
    code, out, err = run(
        "ingest", "topic", "kurs", str(mixed), "--title", "Kurs", "--lang", "de",
        "--contents", "cards,concept-map", "--json",
    )  # fmt: skip
    assert code == 0, err
    data = json.loads(out)
    assert data["created"] and len(data["added"]) == 5
    course = content.CourseTree(courses / "kurs").model
    assert course.is_topic and course.lang == "de" and course.topic_ids == [model.DRAFT_TOPIC]
    assert course.contents == model.TopicContents(cards=True, glossary=False, concept_map=True)
    raw = courses / "kurs" / "sources" / "raw"
    assert sorted(p.suffix for p in raw.iterdir()) == [".pdf"] * 5
    manifest, _ = ingest.read_manifest(courses / "kurs")
    assert manifest.answers.round1 is None and manifest.folder == str(mixed.resolve())
    for d in manifest.documents:
        assert ingest.sha256_file(raw / d.file) == d.sha256

    code, out, err = run("ingest", "extract", "kurs", "--json")
    assert code == 0, err
    chunks = {c["doc"]: c for c in json.loads(out)["chunks"]}
    assert chunks["notes"]["flagged"] == [] and chunks["notes"]["scanned"] == []
    assert chunks["chart"]["scanned"] == [1]
    assert "Grüße" in (courses / "kurs" / "sources" / "text" / "notes" / "p0001.txt").read_text()

    # a second run finds everything known, by the original files
    code, out, _ = run("ingest", "topic", "kurs", str(mixed), "--json")
    data = json.loads(out)
    assert code == 0 and data["added"] == [] and data["changed"] == [] and len(data["known"]) == 5
    # a changed text file replaces its document
    (mixed / "notes.txt").write_text("Ein anderer Text.\n")
    data = json.loads(run("ingest", "add", "kurs", str(mixed), "--json")[1])
    assert data["changed"] == ["notes"] and len(data["known"]) == 4
    assert pipeline.status(courses / "kurs")["steps"][2]["status"] == "done"


def test_several_sources_keep_their_names_apart(courses: Path, tmp_path: Path):
    for name, text in (("a", "Text of folder a.\n"), ("b", "Text of folder b.\n")):
        (tmp_path / name).mkdir()
        (tmp_path / name / "notes.txt").write_text(text)
    single = tmp_path / "pasted-1.txt"
    single.write_text("Pasted in the chat.\n")
    code, _, err = run(
        "ingest",
        "topic",
        "x-topic",
        str(tmp_path / "a"),
        str(tmp_path / "b"),
        str(single),
        "--json",
    )
    assert code == 0, err
    manifest, _ = ingest.read_manifest(courses / "x-topic")
    assert sorted(d.origin for d in manifest.documents) == [
        "a/notes.txt",
        "b/notes.txt",
        "pasted-1.txt",
    ]
    assert len({d.id for d in manifest.documents}) == 3
    assert manifest.folder is None


def test_text_pasted_in_the_chat_is_enough(courses: Path):
    # /register-new-topic Writes it into the new topic's _build/inbox, before there is a topic
    pasted = courses / "x-topic" / "_build" / "inbox" / "pasted-1.txt"
    pasted.parent.mkdir(parents=True)
    pasted.write_text("A note the user pasted, long enough to say something about blocks.\n")
    assert pipeline.status(courses / "x-topic")["resume"]["name"] == "preflight"
    code, out, err = run("ingest", "topic", "x-topic", str(pasted), "--title", "X", "--json")
    assert code == 0, err
    assert json.loads(out)["added"] == ["pasted-1"]
    assert (courses / "x-topic" / "sources" / "raw" / "pasted-1.pdf").is_file()
    assert run("ingest", "extract", "x-topic", "--json")[0] == 0
    assert pipeline.status(courses / "x-topic")["resume"]["name"] == "read"


def test_a_course_is_not_turned_into_a_topic(courses: Path, mixed: Path):
    target = courses / "mini"
    shutil.copytree(FIXTURES / "courses" / "mini", target, ignore=shutil.ignore_patterns("_build"))
    code, _, err = run("ingest", "topic", "mini", str(mixed))
    assert code == 2 and "is a course" in err


def test_contents_flag_is_checked():
    assert ingest.parse_contents("none") == model.TopicContents(
        cards=False, glossary=False, concept_map=False
    )
    with pytest.raises(ingest.IngestError, match="choose from"):
        ingest.parse_contents("cards,quiz")


# --- pipeline ---------------------------------------------------------------------------------


def test_what_only_a_course_has_is_not_applicable(topic: Path):
    result = pipeline.status(topic)
    status = {s["name"]: s["status"] for s in result["steps"]}
    assert result["kind"] == "topic"
    for name in pipeline.NOT_FOR_TOPICS:
        assert status[name] == "n/a", name
    assert result["resume"]["name"] == "preflight"  # the fixture has no sources yet


def test_a_topic_needs_no_exam_profile_and_reports_its_cards(topic: Path, tmp_path: Path):
    path, data = pipeline.report(topic)
    assert data["cards"] == 10 and data["glossary_terms"] == 2 and data["chapters"] == 2
    text = path.read_text()
    assert "Flash cards | 10" in text and "not checked by the blind verifier" in text
    assert pipeline.status(topic)["steps"][14]["status"] == "done"
