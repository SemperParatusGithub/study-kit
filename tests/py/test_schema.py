"""Pydantic models (the schema source), the committed JSON schemas and the YAML loader."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import date

import pytest
from pydantic import ValidationError

from conftest import MINI, REPO
from studykit import cli, content, model, yamlio


def errors(cls, data, context=None) -> list[tuple[str, tuple]]:
    with pytest.raises(ValidationError) as exc:
        cls.model_validate(data, context=context)
    return [(e["type"], e["loc"]) for e in exc.value.errors()]


def test_committed_schemas_match_the_models():
    out_dir = REPO / "schemas"
    wanted = model.json_schemas()
    assert sorted(p.name for p in out_dir.glob("*.schema.json")) == sorted(wanted)
    for name, text in wanted.items():
        assert (out_dir / name).read_text() == text, f"run `studykit schema export` ({name})"


def _schema_patterns() -> list[str]:
    found: list[str] = []

    def walk(node) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "pattern" and isinstance(value, str):
                    found.append(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    for path in sorted((REPO / "schemas").glob("*.schema.json")):
        walk(json.loads(path.read_text()))
    return sorted(set(found))


# Python-only regex syntax that ECMA-262 (JSON Schema `pattern`) rejects or reads differently.
PYTHON_ONLY = ("(?P<", "(?P=", "(?#", "\\A", "\\Z", "(?i", "(?m", "(?s", "(?x", "(?a")


def test_schema_patterns_avoid_python_only_syntax():
    patterns = _schema_patterns()
    assert patterns
    bad = [p for p in patterns if any(token in p for token in PYTHON_ONLY)]
    assert bad == []


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_schema_patterns_compile_as_ecma_regexes():
    # ajv (and yaml-language-server) compile `pattern` with the `u` flag.
    script = (
        "const ps = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
        "const bad = [];"
        "for (const p of ps) {"
        "  try { new RegExp(p, 'u'); } catch (e) { bad.push(p + ': ' + e.message); }"
        "}"
        "process.stdout.write(JSON.stringify(bad));"
    )
    patterns = _schema_patterns()
    proc = subprocess.run(
        ["node", "-e", script],
        input=json.dumps(patterns),
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(proc.stdout) == []


def test_schema_export_check_passes(capsys, monkeypatch):
    monkeypatch.setenv("STUDYKIT_ROOT", str(REPO))
    assert cli.main(["schema", "export", "--check"]) == 0
    assert "up to date" in capsys.readouterr().out


def test_every_mini_file_validates():
    tree = content.CourseTree(MINI)
    checked = 0
    for doc in tree:
        if doc.kind in model.MODELS:
            m, problems = doc.validated
            assert problems == [], [p.format() for p in problems]
            assert m is not None, doc.rel
            checked += 1
    assert checked == 15  # the manifest and the exam profile have models too (Phase 6)
    assert tree.model.exam.date == date(2027, 2, 15)
    assert tree.model.topic_ids == ["spannungsteiler", "rc-tiefpass"]


def test_spec_examples_validate():
    ledger = {
        "schema": 1,
        "item": "ex-rc-tp-grenzfrequenz",
        "kind": "exercise",
        "path": "exercises/rc-filter/ex-rc-tp-grenzfrequenz.md",
        "content_sha256": "a" * 64,
        "status": "verified",
        "method": "script",
        "check": "checks/ex-rc-tp-grenzfrequenz.py",
        "check_sha256": "b" * 64,
        "rounds": 0,
        "results": [
            {
                "key": "fg",
                "expected": 1591.55,
                "computed": 1591.549,
                "unit": "Hz",
                "abs_err": 0.001,
                "rel_err": 6.3e-7,
                "tol": 1.59,
                "ok": True,
            }
        ],
        "checked_at": "2026-10-30T10:12:00Z",
        "verified_at": "2026-10-30T10:12:00Z",
    }
    assert model.VerifyEntry.model_validate(ledger).status == "verified"
    progress = {
        "schema": "studykit-progress/1",
        "course": "get2",
        "exported_at": "2026-11-20T18:03:00Z",
        "items": {
            "mc:mc-rc-filter-003": {
                "h": "9c01aa12",
                "box": 3,
                "due": "2026-11-24",
                "attempts": [
                    {
                        "t": "2026-11-20T18:00:00Z",
                        "chosen": ["A"],
                        "score": 1,
                        "conf": "sure",
                        "ms": 42000,
                    }
                ],
            },
            "ex:ex-rc-tp-grenzfrequenz": {
                "h": "3f2a91c0",
                "hints": 2,
                "answer_ok": True,
                "rating": "partial",
                "box": 2,
            },
            "exam:probeklausur-1": {
                "attempts": [
                    {
                        "started": "2026-11-20T16:00:00Z",
                        "duration_s": 6900,
                        "points": {"pk1-t3": 12, "mc": 14},
                        "total": 71,
                    }
                ]
            },
            "plan:s-2026-11-02-a": {"done": True},
        },
    }
    parsed = model.Progress.model_validate(progress)
    assert isinstance(parsed.items["ex:ex-rc-tp-grenzfrequenz"], model.ExerciseProgress)
    assert isinstance(parsed.items["mc:mc-rc-filter-003"], model.McProgress)


def test_progress_entries_follow_their_key_prefix():
    data = {
        "schema": "studykit-progress/1",
        "course": "get2",
        "exported_at": "2026-11-20T18:03:00Z",
        "items": {"plan:s-2026-11-02-a": {"h": "9c01aa12"}},
    }
    found = errors(model.Progress, data)
    assert ("missing", ("items", "plan:s-2026-11-02-a", "done")) in found


def course_data(**changes):
    data = yamlio.safe_load((MINI / "course.yaml").read_text())
    data.update(changes)
    return data


def test_models_are_strict():
    data = course_data()
    data["exam"]["mc"]["negative_marking"] = "no"
    data["exam"]["points"] = "30"
    found = errors(model.Course, data)
    assert ("bool_type", ("exam", "mc", "negative_marking")) in found
    assert ("float_type", ("exam", "points")) in found


def test_unknown_prerequisite_points_at_the_entry():
    data = course_data()
    data["topics"][1]["prereq"] = ["spannungsteiler", "gleichstrom"]
    with pytest.raises(ValidationError) as exc:
        model.validate_course(data)
    (err,) = exc.value.errors()
    assert err["type"] == "SK-STRUCT-TOPIC"
    assert err["loc"] == ("topics", 1, "prereq", 1)
    assert "spannungsteiler" in err["ctx"]["fix"]


def test_item_topics_must_be_course_topics():
    tree = content.CourseTree(MINI)
    data = tree.get("summary/01-spannungsteiler.md").data | {"topic": "gleichstrom"}
    assert errors(model.Summary, data, tree.context) == [("SK-STRUCT-TOPIC", ("topic",))]
    assert model.Summary.model_validate(data).topic == "gleichstrom"  # no course, no check


def test_cheatsheet_pages_capped_by_course():
    data = {"title": "Formelblatt", "max_pages": 3}
    context = {"topics": [], "cheatsheet_max_pages": 2}
    assert errors(model.Cheatsheet, data, context) == [("SK-SCHEMA-VALUE", ("max_pages",))]


@pytest.mark.parametrize(
    "answer",
    [
        {"key": "a", "label": "$a$", "value": 1.0},
        {"key": "a", "label": "$a$", "value": 1.0, "expr": "x", "symbols": ["x"], "rtol": 0.1},
        {"key": "a", "label": "$a$", "expr": "x"},
    ],
)
def test_answers_are_numeric_with_tolerance_or_symbolic(answer):
    found = errors(model.Answer, answer)
    assert found[0][0] == "SK-SCHEMA-ANSWER"


def test_symbolic_answer():
    a = model.Answer.model_validate(
        {"key": "H", "label": "$H(s)$", "expr": "1/(1+s*R*C)", "symbols": ["s", "R", "C"]}
    )
    assert a.value is None


@pytest.mark.parametrize(
    ("text", "ok"),
    [
        ("$f_\\mathrm{g}$", True),
        ("$|\\underline{H}(f_\\mathrm{g})|$ in dB", True),
        ("Strom $I_1$ in A", True),
        ("**fett**", False),
        ("f_g", False),
        ("$x", False),
        ("$ x $", False),
        ("$$x$$", False),
        ("\\omega", False),
        ("zwei\nZeilen", False),
    ],
)
def test_label_is_plain_text_plus_inline_math(text, ok):
    assert (model.label_problem(text) is None) is ok


def test_rubric_must_add_up():
    task = {
        "id": "pk1-t1",
        "title": "T",
        "topic": "a",
        "kind": "exam-task",
        "points": 10,
        "archetype": "x",
        "rubric": [{"points": 4, "criterion": "a"}, {"points": 5, "criterion": "b"}],
    }
    assert errors(model.ExamTask, task) == [("SK-SCHEMA-RUBRIC", ("rubric",))]
    task["rubric"][1]["points"] = 6
    assert model.ExamTask.model_validate(task).points == 10


def test_ids_follow_their_patterns():
    assert model.mc_topic("mc-rc-filter-003") == "rc-filter"
    assert model.mc_topic("mc-rc-filter-3") is None
    found = errors(model.Exercise, {"id": "rc-ex", "title": "T", "topic": "a"})
    assert ("SK-STRUCT-ID", ("id",)) in found


def test_plan_tasks_need_their_fields():
    found = errors(model.PlanTask, {"do": "mc", "topic": "a"})
    assert found == [("SK-SCHEMA-VALUE", ())]
    assert model.PlanTask.model_validate({"do": "exam", "ref": "exam:pk-1"}).ref == "exam:pk-1"


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("a: yes", "yes"),
        ("a: no", "no"),
        ("a: on", "on"),
        ("a: true", True),
        ("a: 010", 10),
        ("a: 0o10", 8),
        ("a: 0x1f", 31),
        ("a: 1e3", 1000.0),
        ("a: .5", 0.5),
        ("a: 1:30", "1:30"),
        ("a: 2026-11-02", "2026-11-02"),
        ("a: 2026-10-30T10:12:00Z", "2026-10-30T10:12:00Z"),
        ("a: ~", None),
        ("a: '\\frac{1}{2}'", "\\frac{1}{2}"),
    ],
)
def test_loader_follows_yaml_1_2_core(text, value):
    doc = yamlio.load(text + "\n", path="x.yaml")
    assert doc.findings == [] or all(f.severity == "warning" for f in doc.findings)
    assert doc.data == {"a": value}


def test_loader_rejects_merge_keys_as_plain_keys():
    doc = yamlio.load("base: &b {x: 1}\nother:\n  <<: *b\n", path="x.yaml")
    assert doc.data["other"] == {"<<": {"x": 1}}


def test_locate_uses_the_line_offset():
    doc = yamlio.load("a: 1\nb:\n  - c: 2\n", path="x.md", line_offset=1)
    assert doc.locate(["b", 0, "c"]) == (4, 5)
    assert doc.locate(["missing"]) == (2, 1)


def test_loader_reports_non_characters_with_position():
    doc = yamlio.load("a: 1\nb: x￾\n", path="x.md", line_offset=1)
    (finding,) = doc.findings
    assert (finding.code, finding.line, finding.col) == ("SK-YAML-CONTROL", 3, 5)
    assert doc.data is None


def test_double_quotes_are_an_error_even_without_a_backslash():
    doc = yamlio.load('a: "x"\n', path="x.yaml")
    (finding,) = yamlio.style_findings(doc)
    assert finding.code == "SK-YAML-DQUOTE" and finding.severity == "error"
