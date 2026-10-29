"""`studykit pipeline status|report` (docs/architecture.md §5.4): every step's status comes
from the outputs alone, and the first unfinished step is where an interrupted run resumes."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import materials
from conftest import REPO
from studykit import ingest, pipeline
from test_ingest import ROUND1, init, notes_for, run, run_json

PROFILE = """schema: 1
confidence: medium
basis: past-exams
exams: [klausur-ws2425]
format: mixed
duration_min: 90
points: 60
archetypes:
  - {id: verstaerker, title: Verstärkerschaltung berechnen, share: 0.6}
  - {id: integrierer, title: Integrierer im Zeitbereich, share: 0.4}
"""
NOTATION = "schema: 1\nimaginary_unit: j\nphasor: underline\ndecimal: comma\n"
TOPICS = """topics:
  - {id: idealer-opv, title: Der ideale OPV, weight: 0.4, prereq: []}
  - {id: grundschaltungen, title: Grundschaltungen, weight: 0.6, prereq: [idealer-opv]}
"""


@pytest.fixture
def courses(tmp_path: Path, monkeypatch) -> Path:
    path = tmp_path / "courses"
    path.mkdir()
    monkeypatch.setenv("STUDYKIT_COURSES_DIR", str(path))
    return path


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    return materials.folder(tmp_path / "Unterlagen")


def status(course: str = "opv") -> dict:
    code, data = run_json("pipeline", "status", course)
    assert code == 0
    return data


def steps(data: dict) -> dict[str, str]:
    return {s["name"]: s["status"] for s in data["steps"]}


def resume(data: dict) -> str | None:
    return data["resume"]["name"] if data["resume"] else None


def read_all(course: Path, transcribe: bool = True) -> None:
    """What the ingesters and the exam-analyst write in step 4."""
    plan = ingest.read_chunks(course)[0]
    assert plan is not None
    for chunk in plan.chunks:
        notes_for(course, chunk)
        for n in chunk.scanned if transcribe else []:
            ingest.vision_file(course, chunk.doc, n).write_text("Aufgabe 1\n")
    (course / "analysis").mkdir(exist_ok=True)
    (course / "analysis" / "exam-profile.yaml").write_text(PROFILE)
    (course / "analysis" / "notation.yaml").write_text(NOTATION)


def synthesize(course: Path) -> None:
    """What the main thread writes in step 5: the outline and the topics."""
    plan = ingest.read_chunks(course)[0]
    assert plan is not None
    chunks = ", ".join(c.id for c in plan.chunks)
    (course / "sources" / "outline.md").write_text(
        f"# Gliederung\n\n## idealer-opv\n\n## grundschaltungen\n\nQuellen: {chunks}\n"
    )
    path = course / "course.yaml"
    text = path.read_text()
    start = text.index("topics:")
    end = text.index("focus:")
    path.write_text(text[:start] + TOPICS + text[end:])


def test_a_course_that_does_not_exist_starts_at_preflight(courses: Path):
    data = status("neu")
    assert not data["exists"] and resume(data) == "preflight"
    # the commands hand `dir` to their agents as the absolute course directory
    assert data["dir"] == str((courses / "neu").resolve())
    assert set(steps(data).values()) == {"pending"}
    assert run("pipeline", "status", "Bad Id")[0] == 2


def test_resume_point_follows_the_outputs(courses: Path, folder: Path):
    course = courses / "opv"
    init(folder)
    data = status()
    assert resume(data) == "extract"
    assert [steps(data)[s] for s in ("preflight", "ask-1", "scaffold")] == ["done"] * 3

    run("ingest", "extract", "opv")
    data = status()
    assert resume(data) == "read" and steps(data)["read"] == "pending"
    read = next(s for s in data["steps"] if s["name"] == "read")
    assert len(read["todo"]["chunks_without_notes"]) == 7
    assert read["todo"]["transcriptions_missing"] == ["scan-2019 p. 1"]

    # an interrupted reading wave: some notes written
    plan = ingest.read_chunks(course)[0]
    assert plan is not None
    for chunk in plan.chunks[:3]:
        notes_for(course, chunk)
    data = status()
    assert resume(data) == "read" and steps(data)["read"] == "partial"
    read = next(s for s in data["steps"] if s["name"] == "read")
    assert len(read["todo"]["chunks_without_notes"]) == 4
    assert "exam_profile" in read["todo"]

    read_all(course, transcribe=False)
    data = status()
    # notes alone are not enough: the scanned page needs its transcription
    assert steps(data)["read"] == "partial" and resume(data) == "read"
    read = next(s for s in data["steps"] if s["name"] == "read")
    assert read["todo"] == {"transcriptions_missing": ["scan-2019 p. 1"]}
    ingest.vision_file(course, "scan-2019", 1).write_text("Aufgabe 1\n")
    data = status()
    assert steps(data)["read"] == "done" and resume(data) == "synthesize"
    assert steps(data)["synthesize"] == "pending"

    (course / "sources" / "outline.md").write_text("# Gliederung\n")
    assert steps(status())["synthesize"] == "partial"
    synthesize(course)
    data = status()
    assert steps(data)["synthesize"] == "done" and resume(data) == "ask-2"

    run("ingest", "round2", "opv", "--mock-exams", "1", "--scope", "full", "--no-go")
    data = status()
    assert steps(data)["ask-2"] == "partial" and resume(data) == "ask-2"
    run("ingest", "round2", "opv", "--mock-exams", "1", "--scope", "full")
    data = status()
    assert steps(data)["ask-2"] == "done" and resume(data) == "author"
    author = next(s for s in data["steps"] if s["name"] == "author")
    assert author["status"] == "pending"
    assert author["todo"]["summary"] == ["idealer-opv", "grundschaltungen"]
    assert author["todo"]["overview"] == ["overview.md"]


def test_new_material_makes_the_reading_stale(courses: Path, folder: Path, tmp_path: Path):
    course = courses / "opv"
    init(folder)
    run("ingest", "extract", "opv")
    read_all(course)
    synthesize(course)
    assert resume(status()) == "ask-2"
    # a changed sheet replaces its document: its chunk is planned again, its notes are stale
    materials.text_pdf(folder / "Uebung01.pdf", [materials.page_text(1, "Neue Fassung.")])
    data = status()
    assert steps(data)["scaffold"] == "stale" and resume(data) == "scaffold"
    scaffold = next(s for s in data["steps"] if s["name"] == "scaffold")
    assert scaffold["todo"]["folder_changed"] == ["Uebung01.pdf"]
    code, _ = run_json("ingest", "add", "opv", str(folder))
    assert code == 0
    data = status()
    assert steps(data)["scaffold"] == "done" and steps(data)["extract"] == "done"
    assert steps(data)["read"] == "stale" and resume(data) == "read"
    read = next(s for s in data["steps"] if s["name"] == "read")
    assert read["todo"]["notes_stale"] == ["uebung01-c01"]
    # rewritten notes; a new document then leaves the outline behind
    plan = ingest.read_chunks(course)[0]
    assert plan is not None
    notes_for(course, next(c for c in plan.chunks if c.id == "uebung01-c01"))
    assert resume(status()) == "ask-2"
    materials.text_pdf(tmp_path / "neu" / "VL02.pdf", [materials.page_text(1)])
    run("ingest", "add", "opv", str(tmp_path / "neu"))
    plan = ingest.read_chunks(course)[0]
    assert plan is not None
    notes_for(course, next(c for c in plan.chunks if c.id == "vl02-c01"))
    data = status()
    assert steps(data)["read"] == "done"
    assert steps(data)["synthesize"] == "stale" and resume(data) == "synthesize"


def test_a_damaged_extract_is_detected(courses: Path, folder: Path):
    course = courses / "opv"
    init(folder)
    run("ingest", "extract", "opv")
    (course / "sources" / "text" / "skript" / "p0007.txt").unlink()
    data = status()
    assert steps(data)["extract"] == "stale" and resume(data) == "extract"
    run("ingest", "extract", "opv")
    assert steps(status())["extract"] == "done"
    (course / "sources" / "raw" / "uebung01.pdf").unlink()
    data = status()
    assert steps(data)["scaffold"] == "partial" and resume(data) == "scaffold"
    run("ingest", "init", str(folder), "opv")  # resumes: copies what is missing
    assert steps(status())["scaffold"] == "done"


def test_core_scope_defers_exams_and_cheat_sheet(courses: Path, folder: Path):
    course = courses / "opv"
    init(folder)
    run("ingest", "extract", "opv")
    read_all(course)
    synthesize(course)
    run("ingest", "round2", "opv", "--mock-exams", "2", "--scope", "core")
    data = status()
    assert data["scope"] == "core"
    by = {s["name"]: s for s in data["steps"]}
    assert by["mock-exams"]["deferred"] and by["cheatsheet"]["deferred"]
    assert "exercises" not in by["author"]["todo"]
    assert data["deferred"] == ["mock-exams", "cheatsheet"]


def test_text_output_names_the_resume_point(courses: Path, folder: Path):
    init(folder)
    code, out, _err = run("pipeline", "status", "opv")
    assert code == 0
    assert out.splitlines()[-1] == "resume at step 3 (extract)"


def test_sample_course_after_registration(courses: Path, folder: Path):
    """The later steps on a copy of the sample course that went through ingest."""
    course = courses / "sample-course"
    shutil.copytree(
        REPO / "examples" / "sample-course",
        course,
        ignore=shutil.ignore_patterns("_build", "state"),
    )
    code, data = run_json("ingest", "init", str(folder), "sample-course", *ROUND1)
    assert code == 0 and not data["created"]
    run("ingest", "extract", "sample-course")
    read_all(course)
    (course / "analysis" / "exam-profile.yaml").write_text(
        (REPO / "examples" / "sample-course" / "analysis" / "exam-profile.yaml").read_text()
    )
    plan = ingest.read_chunks(course)[0]
    assert plan is not None
    (course / "sources" / "outline.md").write_text(
        "# Gliederung\n\nspannungsteiler, wechselstrom, rc-filter\n\n"
        + ", ".join(c.id for c in plan.chunks)
        + "\n"
    )
    run("ingest", "round2", "sample-course", "--mock-exams", "1", "--scope", "full")
    data = status("sample-course")
    by = {s["name"]: s for s in data["steps"]}
    assert [by[s]["status"] for s in pipeline.STEPS[:8]] == ["done"] * 8, [
        (s, by[s]["details"]) for s in pipeline.STEPS[:8]
    ]
    assert by["plan"]["status"] == "done"
    assert by["verify"]["status"] == "pending" and by["verify"]["todo"]["no_ledger"]
    assert by["publish"]["status"] == "stale"  # ready, but the copy has no PDFs and no site
    assert resume(data) == "figures"
    # the report proves step 14 until the content changes
    code, out, _ = run("pipeline", "report", "sample-course", "--today", "2026-10-29")
    assert code == 0 and "state/pipeline/report.md" in out
    text = (course / "state" / "pipeline" / "report.md").read_text()
    assert "| Mock exams | 1 | probeklausur-1 |" in text
    assert "/examine sample-course diagnostic" in text
    assert by_name(status("sample-course"), "report") == "done"
    mc = course / "mc" / "rc-filter.md"
    mc.write_text(mc.read_text() + "\n")
    assert by_name(status("sample-course"), "report") == "stale"


def by_name(data: dict, name: str) -> str:
    return steps(data)[name]
