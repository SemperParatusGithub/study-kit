"""The Claude Code layer (.claude/): skills, agents and settings (docs/architecture.md §5),
and the Codex files that reuse it (AGENTS.md, .agents/, .codex/; §5.5).

Frontmatter follows the Claude Code docs (skills: name, description,
disable-model-invocation, user-invocable, allowed-tools, argument-hint; subagents: name,
description, tools, model, effort, maxTurns, skills, hooks). Every file, `studykit`
command and `just` recipe a skill or agent names must exist, the content-format templates
must pass lint, and the configured hook commands are run as Claude Code and Codex run them.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

from studykit import cli, codex, hook, lint, pipeline, validate
from studykit.model import ChunkNotes

REPO = Path(__file__).resolve().parents[2]
CLAUDE = REPO / ".claude"
SKILLS = CLAUDE / "skills"
AGENTS = CLAUDE / "agents"
SAMPLE = REPO / "examples" / "sample-course"
ERRORS = REPO / "docs" / "content-format" / "errors.md"
# the rules every session reads: Claude Code's and Codex's
RULE_FILES = [REPO / "CLAUDE.md", REPO / "AGENTS.md"]
CODEX = REPO / ".codex"

INTERNAL = {"content-format", "authoring", "figures", "verify-protocol", "ingest"}
COMMANDS = {
    "register-new-subject",
    "add-material",
    "regenerate",
    "verify",
    "tutor",
    "examine",
    "import-progress",
    "study-status",
}
AGENT_NAMES = {"ingester", "exam-analyst", "author", "verifier", "tutor", "examiner"}
# the first argument of each command's argument-hint (§5.2)
FIRST_ARG = {name: "<course>" for name in COMMANDS} | {"register-new-subject": "<folder>"}

SKILL_KEYS = {
    "name",
    "description",
    "when_to_use",
    "argument-hint",
    "arguments",
    "disable-model-invocation",
    "user-invocable",
    "allowed-tools",
    "disallowed-tools",
    "model",
    "effort",
    "context",
    "agent",
    "background",
    "hooks",
    "paths",
    "shell",
    "metadata",
    "license",
    "compatibility",
}
AGENT_KEYS = {
    "name",
    "description",
    "tools",
    "disallowedTools",
    "model",
    "permissionMode",
    "maxTurns",
    "skills",
    "mcpServers",
    "hooks",
    "memory",
    "background",
    "effort",
    "isolation",
    "color",
    "initialPrompt",
}
TOOLS = {
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
    "Bash",
    "AskUserQuestion",
    "WebFetch",
    "WebSearch",
    "NotebookEdit",
    "Skill",
    "TodoWrite",
}
MODELS = {"sonnet", "opus", "haiku", "inherit"}
EFFORTS = {"low", "medium", "high", "xhigh", "max"}
HOOK_EVENTS = {"PreToolUse", "PostToolUse", "Stop", "SubagentStop"}

# docs/architecture.md §5.3: (model, effort, maxTurns, tools, preloaded skills)
AGENT_SPEC = {
    "ingester": (
        "sonnet",
        "medium",
        40,
        ["Read", "Write", "Glob", "Bash"],
        ["ingest", "content-format"],
    ),
    "exam-analyst": ("opus", "high", 50, ["Read", "Write", "Glob", "Grep", "Bash"], ["ingest"]),
    "author": (
        "opus",
        "high",
        80,
        ["Read", "Write", "Edit", "Glob", "Grep", "Bash"],
        ["content-format", "authoring", "figures"],
    ),
    "verifier": (
        "opus",
        "high",
        50,
        ["Read", "Write", "Bash"],
        ["verify-protocol", "content-format"],
    ),
    "tutor": ("opus", None, None, ["Read", "Grep", "Glob", "Bash"], []),
    "examiner": ("opus", None, None, ["Read", "Grep", "Glob", "Bash", "AskUserQuestion"], []),
}

# templates/<name> -> the course file it becomes in a copy of the sample course
TEMPLATES = {
    "course.yaml": "course.yaml",
    "overview.md": "overview.md",
    "summary.md": "summary/03-rc-filter.md",
    "exercise.md": "exercises/rc-filter/ex-rc-tp-vorlage.md",
    "exercise-symbolic.md": "exercises/spannungsteiler/ex-st-vorlage.md",
    "mc-bank.md": "mc/rc-filter.md",
    "exam/exam.yaml": "exams/probeklausur-2/exam.yaml",
    "exam/01-pk2-t1.md": "exams/probeklausur-2/01-pk2-t1.md",
    "exam/mc.md": "exams/probeklausur-2/mc.md",
    "cheatsheet.md": "cheatsheet.md",
    "plan.yaml": "plan.yaml",
    "exam-profile.yaml": "analysis/exam-profile.yaml",
    "figure.py": "figures/vorlage-bode.py",
}


def split(path: Path) -> tuple[dict, str]:
    """(frontmatter, body) of a skill or agent file; frontmatter must open on line 1."""
    text = path.read_text("utf-8")
    assert text.startswith("---\n"), f"{path}: frontmatter must open on the first line"
    end = text.index("\n---\n", 4)
    data = yaml.safe_load(text[4:end])
    assert isinstance(data, dict), f"{path}: frontmatter is not a mapping"
    return data, text[end + 5 :]


def skill_files() -> list[Path]:
    return sorted(SKILLS.glob("*/SKILL.md"))


def agent_files() -> list[Path]:
    return sorted(AGENTS.glob("*.md"))


def markdown_files() -> list[Path]:
    """Every Markdown file of the skills (with supporting files) and the agents."""
    return sorted(p for p in [*SKILLS.rglob("*.md"), *AGENTS.glob("*.md")] if p.is_file())


def as_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return list(value)


# --- inventory ----------------------------------------------------------------------------


def test_the_planned_skills_and_agents_exist():
    assert {p.parent.name for p in skill_files()} == INTERNAL | COMMANDS
    assert {p.stem for p in agent_files()} == AGENT_NAMES
    leftovers = [p for p in SKILLS.iterdir() if p.is_dir() and not (p / "SKILL.md").is_file()]
    assert not leftovers


# --- skill frontmatter --------------------------------------------------------------------


@pytest.mark.parametrize("path", skill_files(), ids=lambda p: p.parent.name)
def test_skill_frontmatter(path: Path):
    data, body = split(path)
    assert set(data) <= SKILL_KEYS, f"unknown keys {set(data) - SKILL_KEYS}"
    assert data["name"] == path.parent.name
    assert re.fullmatch(r"[a-z0-9][a-z0-9-]*", data["name"])
    assert isinstance(data["description"], str)
    assert 40 <= len(data["description"]) <= 1024
    for key in ("disable-model-invocation", "user-invocable"):
        assert isinstance(data.get(key, False), bool)
    if "allowed-tools" in data:
        assert isinstance(data["allowed-tools"], list), "a list: rules contain spaces"
        for rule in data["allowed-tools"]:
            assert re.fullmatch(r"[A-Za-z]+(\(.+\))?", rule), rule
    assert body.strip()


@pytest.mark.parametrize("name", sorted(INTERNAL))
def test_internal_skills_are_hidden_and_short(name: str):
    path = SKILLS / name / "SKILL.md"
    data, _ = split(path)
    assert data.get("user-invocable") is False
    assert data.get("disable-model-invocation", False) is False  # agents preload them
    assert len(path.read_text("utf-8").splitlines()) < 500


@pytest.mark.parametrize("name", sorted(COMMANDS))
def test_user_commands_run_only_when_typed(name: str):
    data, body = split(SKILLS / name / "SKILL.md")
    assert data["disable-model-invocation"] is True
    assert data.get("user-invocable", True) is True
    assert data.get("context") != "fork"  # main thread: AskUserQuestion works there
    assert data["argument-hint"].startswith(FIRST_ARG[name])
    assert "$0" in body or "$ARGUMENTS" in body


def test_skill_text_runs_no_shell_on_load():
    """`!` before a code span runs a command when the skill loads; none of ours does."""
    for path in markdown_files():
        assert not re.search(r"(^|\s)!`", path.read_text("utf-8")), path


# --- agent frontmatter --------------------------------------------------------------------


@pytest.mark.parametrize("path", agent_files(), ids=lambda p: p.stem)
def test_agent_frontmatter(path: Path):
    data, body = split(path)
    assert set(data) <= AGENT_KEYS, f"unknown keys {set(data) - AGENT_KEYS}"
    assert data["name"] == path.stem
    assert ":" not in data["name"]
    assert isinstance(data["description"], str) and len(data["description"]) >= 40
    tools_ = as_list(data.get("tools"))
    assert tools_, "every agent lists its tools"
    assert set(tools_) <= TOOLS, set(tools_) - TOOLS
    assert "Agent" not in tools_ and "Task" not in tools_, "no agent spawns agents"
    assert data.get("model") in MODELS
    assert data.get("effort", "high") in EFFORTS
    assert isinstance(data.get("maxTurns", 1), int)
    assert "memory" not in data, "course state lives in the course, not in agent memory"
    for skill in as_list(data.get("skills")):
        skill_data, _ = split(SKILLS / skill / "SKILL.md")
        assert skill_data.get("disable-model-invocation", False) is False, (
            f"{skill} cannot be preloaded: disable-model-invocation blocks it"
        )
    for event in data.get("hooks") or {}:
        assert event in HOOK_EVENTS
    assert body.strip()


@pytest.mark.parametrize("name", sorted(AGENT_SPEC))
def test_agents_follow_the_table(name: str):
    model, effort, turns, tools_, skills = AGENT_SPEC[name]
    data, _ = split(AGENTS / f"{name}.md")
    assert data["model"] == model
    assert data.get("effort") == effort
    assert data.get("maxTurns") == turns
    assert as_list(data["tools"]) == tools_
    assert as_list(data.get("skills")) == skills


def test_only_the_verifier_has_hooks_and_they_guard_it():
    for path in agent_files():
        data, _ = split(path)
        if path.stem != "verifier":
            assert "hooks" not in data
    data, _ = split(AGENTS / "verifier.md")
    assert as_list(data["tools"]) == ["Read", "Write", "Bash"]
    assert set(data["hooks"]) == {"PreToolUse"}
    (group,) = data["hooks"]["PreToolUse"]
    matched = set(group["matcher"].split("|"))
    assert {"Read", "Write", "Edit", "Grep", "Glob", "Bash"} <= matched
    (hook,) = group["hooks"]
    assert hook["type"] == "command"
    assert hook["command"].endswith("studykit hook verifier-guard")
    assert '--project "${CLAUDE_PROJECT_DIR}"' in hook["command"]


def test_tutor_and_examiner_open_their_commands():
    for agent, command in (("tutor", "tutor"), ("examiner", "examine")):
        _, body = split(AGENTS / f"{agent}.md")
        assert f".claude/skills/{command}/SKILL.md" in body
        assert f"just {command}" in body


# --- references ---------------------------------------------------------------------------

LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
REPO_PATH = re.compile(
    r"(?<![\w./-])((?:docs|src|tests|schemas|pandoc|typst|examples|site|\.claude)/[\w./-]*[\w/])"
)
FENCE = re.compile(r"^```[^\n]*\n(.*?)^```", re.S | re.M)
SPAN = re.compile(r"`([^`\n]+)`")


def code_snippets(text: str) -> list[str]:
    """Fenced code lines and inline code spans: where commands are written out."""
    out = []
    for block in FENCE.findall(text):
        out += block.splitlines()
    out += SPAN.findall(FENCE.sub("", text))
    return out


def test_linked_files_exist():
    for path in markdown_files():
        for target in LINK.findall(path.read_text("utf-8")):
            if re.match(r"[a-z]+:", target) or target.startswith("#"):
                continue  # course links (ex:, fig:, …), URLs and anchors
            assert (path.parent / target.split("#")[0]).exists(), f"{path}: {target}"


def test_named_repository_paths_exist():
    files = [*markdown_files(), *RULE_FILES]
    for path in files:
        for ref in REPO_PATH.findall(path.read_text("utf-8")):
            if "<" in ref or "*" in ref:
                continue
            assert (REPO / ref).exists(), f"{path.relative_to(REPO)}: {ref}"


def subparsers(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return dict(action.choices)
    return {}


def options(parser: argparse.ArgumentParser) -> set[str]:
    return {s for a in parser._actions for s in a.option_strings}


def positional_choices(parser: argparse.ArgumentParser) -> set[str]:
    return {
        c
        for a in parser._actions
        if not a.option_strings and a.choices and not isinstance(a, argparse._SubParsersAction)
        for c in a.choices
    }


STUDYKIT = re.compile(r"\bstudykit\s+([a-z][a-z-]*)(.*)")


def check_command(snippet: str, top: dict[str, argparse.ArgumentParser]) -> list[str]:
    problems = []
    for m in STUDYKIT.finditer(snippet):
        cmd, rest = m[1], re.split(r"&&|\|\||;|\|", m[2])[0]
        if cmd not in top:
            problems.append(f"unknown command `studykit {cmd}`")
            continue
        parser = top[cmd]
        words = rest.split()
        nested = subparsers(parser)
        if nested:
            if not words or words[0] not in nested:
                problems.append(f"`studykit {cmd}` needs one of {sorted(nested)}: {snippet}")
                continue
            parser = nested[words[0]]
        choices = positional_choices(parser)
        first = words[0] if words else ""
        if choices and first and not first.startswith(("-", "<", "$")) and first not in choices:
            problems.append(f"`studykit {cmd} {first}` is not one of {sorted(choices)}")
        for flag in re.findall(r"(?<![\w-])(--[a-z][a-z-]*)", rest):
            if flag not in options(parser):
                problems.append(f"`studykit {cmd}` has no {flag}: {snippet}")
    return problems


def test_studykit_commands_exist():
    top = subparsers(cli.build_parser())
    problems = []
    for path in [*markdown_files(), *RULE_FILES]:
        for snippet in code_snippets(path.read_text("utf-8")):
            problems += [f"{path.relative_to(REPO)}: {p}" for p in check_command(snippet, top)]
    assert not problems, "\n".join(problems)


def test_the_command_checker_catches_mistakes():
    top = subparsers(cli.build_parser())
    assert check_command("studykit verify c id --confirm checks/x.py --method m", top) == []
    assert check_command("uv run --frozen studykit progress log c --json-line x", top) == []
    assert check_command("studykit ingest scan x --dry-run --json", top) == []
    assert check_command("studykit pipeline status c --json", top) == []
    assert check_command("studykit ingest digest x", top)
    assert check_command("studykit pipeline resume c", top)
    assert check_command("studykit progress show c", top)
    assert check_command("studykit verify c --showkey", top)
    assert check_command("studykit hook guard", top)


def just_recipes() -> set[str]:
    just = REPO / ".tools" / "bin" / "just"
    exe = str(just) if just.exists() else shutil.which("just")
    if exe is None:
        pytest.skip("just is not installed")
    out = subprocess.run(
        [exe, "--justfile", str(REPO / "justfile"), "--summary"],
        capture_output=True,
        text=True,
        check=True,
    )
    return set(out.stdout.split())


def test_just_recipes_exist():
    recipes = just_recipes()
    assert {"tutor", "examine", "verify", "status"} <= recipes
    problems = []
    for path in [*markdown_files(), *RULE_FILES]:
        for snippet in code_snippets(path.read_text("utf-8")):
            for name in re.findall(r"(?<![\w-])just\s+([a-z][a-z-]*)", snippet):
                if name not in recipes:
                    problems.append(f"{path.relative_to(REPO)}: just {name}")
    assert not problems, "\n".join(problems)


def test_sk_codes_are_documented():
    documented = set(re.findall(r"^### `(SK-[A-Z]+-[A-Z-]+)`", ERRORS.read_text(), re.M))
    for path in markdown_files():
        for code in re.findall(r"\bSK-[A-Z]+(?:-[A-Z]+)+\b", path.read_text("utf-8")):
            assert code in documented, f"{path.relative_to(REPO)}: {code}"


# --- check-script recipes -----------------------------------------------------------------


def recipes() -> list[tuple[str, str]]:
    text = (SKILLS / "verify-protocol" / "recipes.md").read_text("utf-8")
    return re.findall(r"^```(python|json)\n(.*?)^```", text, re.S | re.M)


def test_recipes_run_and_print_a_check_line(tmp_path: Path):
    scripts = [code for lang, code in recipes() if lang == "python"]
    assert len(scripts) >= 6
    for i, code in enumerate(scripts):
        path = tmp_path / f"recipe{i}.py"
        path.write_text(code)
        done = subprocess.run(
            [sys.executable, str(path)],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            timeout=120,
            check=False,
        )
        assert done.returncode == 0, f"recipe {i}:\n{code}\n{done.stderr}"
        line = json.loads(done.stdout.strip().splitlines()[-1])
        assert line["studykit-check"] == 1 and line["kind"] in ("answers", "mc-numeric")
    for lang, code in recipes():
        if lang == "json":
            assert set(json.loads(code)) == {"answer", "confidence", "ambiguous", "reason"}


def test_recipes_pass_the_verifier_guard(tmp_path: Path):
    course = tmp_path / "courses" / "c"
    (course / "checks").mkdir(parents=True)
    (course / "course.yaml").write_text("id: c\n")
    for i, (_, code) in enumerate(recipes()):
        payload = event("PreToolUse", "Write", course, content=code)
        payload["tool_input"]["file_path"] = str(course / "checks" / f"x{i}.py")
        assert hook.run("verifier-guard", json.dumps(payload)) == "", code


# --- templates ----------------------------------------------------------------------------


def test_every_template_is_listed_and_mapped():
    base = SKILLS / "content-format" / "templates"
    present = {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file()}
    assert present == set(TEMPLATES)
    text = (SKILLS / "content-format" / "SKILL.md").read_text("utf-8")
    for name in TEMPLATES:
        assert f"(templates/{name})" in text


def test_templates_pass_lint_in_the_sample_course(tmp_path: Path):
    course = tmp_path / "sample-course"
    shutil.copytree(SAMPLE, course, ignore=shutil.ignore_patterns("_build"))
    base = SKILLS / "content-format" / "templates"
    targets = []
    for name, rel in TEMPLATES.items():
        dest = course / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(base / name, dest)
        if dest.suffix != ".py":
            targets.append(dest)
    compile((base / "figure.py").read_text("utf-8"), "figure.py", "exec")
    assert "def build()" in (base / "figure.py").read_text("utf-8")
    report = lint.lint_files(targets)
    assert [f.format() for f in report.findings] == []


# --- ingest templates ---------------------------------------------------------------------

INGEST = SKILLS / "ingest"
# templates/<name> -> the course file it becomes in a draft course made for it
INGEST_TEMPLATES = {
    "notes.md": "sources/notes/vl-03-c01.md",
    "exam-profile.yaml": "analysis/exam-profile.yaml",
    "exam-profile-no-exams.yaml": "analysis/exam-profile.yaml",
    "notation.yaml": "analysis/notation.yaml",
    "outline.md": "sources/outline.md",
}
DRAFT_COURSE = """\
schema: 1
id: opv
title: 'opv'
lang: de
status: draft
exam: {date: 2027-02-17, duration_min: 90, points: 60, format: mixed}
cheatsheet: {allowed: true, max_pages: 2}
study: {start: 2026-10-29, hours_per_week: 6, blocked: []}
topics:
  - {id: draft, title: 'Themen folgen nach dem Einlesen', weight: 1, prereq: []}
focus: []
skip: []
targets: {exercises_per_topic: auto, mc_per_topic: auto, mock_exams: 2}
retired_ids: []
"""
# the documents the templates cite: (id, pages, kind)
INGEST_DOCS = [
    ("vl-03", 14, "slides"),
    ("klausur-ws2526", 2, "exam"),
    ("klausur-ws2526-loesung", 1, "exam-solutions"),
    ("uebung-03", 1, "exercises"),
]


def draft_course(root: Path) -> Path:
    """A course as `ingest init` and `ingest extract` leave it, with the chunk of the notes
    template planned at the template's sha256."""
    course = root / "opv"
    (course / "sources" / "notes").mkdir(parents=True)
    (course / "analysis").mkdir()
    (course / "course.yaml").write_text(DRAFT_COURSE)
    notes, _ = split(INGEST / "templates" / "notes.md")
    lines = ["schema: 1", "course: opv", "documents:"]
    for i, (doc, pages, kind) in enumerate(INGEST_DOCS):
        sha = notes["source_sha256"] if doc == notes["doc"] else f"{i:064x}"
        lines.append(
            f"  - {{id: {doc}, title: {doc}, file: {doc}.pdf, origin: {doc}.pdf, "
            f"sha256: '{sha}', bytes: 1000, pages: {pages}, kind: {kind}, "
            "kind_from: filename, text_share: 1, added: 2026-10-29}"
        )
    (course / "sources" / "manifest.yaml").write_text("\n".join(lines) + "\n")
    first, last = notes["pages"].split("-")
    (course / "sources" / "chunks.yaml").write_text(
        "schema: 1\nmax_pages: 20\nchunks:\n"
        f"  - {{id: {notes['chunk']}, doc: {notes['doc']}, kind: {notes['kind']}, "
        f"first: {first}, last: {last}, flagged: [], scanned: [], "
        f"sha256: '{notes['source_sha256']}'}}\n"
    )
    return course


def test_every_ingest_template_is_listed_and_tested():
    base = INGEST / "templates"
    present = {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file()}
    assert present == set(INGEST_TEMPLATES)
    text = (INGEST / "SKILL.md").read_text("utf-8") + (INGEST / "exam-analysis.md").read_text(
        "utf-8"
    )
    for name in INGEST_TEMPLATES:
        assert f"templates/{name}" in text


@pytest.mark.parametrize("profile", ["exam-profile.yaml", "exam-profile-no-exams.yaml"])
def test_ingest_templates_validate_in_a_draft_course(tmp_path: Path, profile: str):
    course = draft_course(tmp_path)
    base = INGEST / "templates"
    for name in ("notes.md", profile, "notation.yaml"):
        shutil.copyfile(base / name, course / INGEST_TEMPLATES[name])
    paths = [course / "sources", course / "analysis"]
    report = validate.validate(
        [course], paths=paths, config=validate.Config(figures=False, pdf=False, site=False)
    )
    assert [f.format() for f in report.findings if f.is_error] == []
    notes, _ = split(base / "notes.md")
    assert ChunkNotes.model_validate(notes).topics


def test_outline_template_names_its_topics_and_chunks():
    text = (INGEST / "templates" / "outline.md").read_text("utf-8")
    rows = re.findall(r"^\| [0-9]+ \| ([a-z0-9-]+) \|", text, re.M)
    chunks = re.findall(r"^\| ([a-z0-9-]+-c[0-9]{2,}) \|", text, re.M)
    assert len(rows) >= 2 and chunks
    for ident in rows:
        assert f"## {ident}:" in text
    for chunk in chunks:
        assert text.count(chunk) >= 2  # in the chunk table and under a topic


# --- the register and add-material commands -----------------------------------------------


def test_register_command_covers_every_pipeline_step_in_order():
    _, body = split(SKILLS / "register-new-subject" / "SKILL.md")
    headings = [int(n) for n in re.findall(r"^## ([0-9]+)\. ", body, re.M)]
    assert headings == list(range(len(pipeline.STEPS)))
    for n, name in enumerate(pipeline.STEPS):
        if n >= 2:  # 0 and 1 are judged by the step after them
            assert f"pipeline step {n} (`{name}`)" in body, name
    assert "pipeline status <c> --json" in body
    assert "resume.step" in body


def test_register_command_asks_the_planned_questions():
    _, body = split(SKILLS / "register-new-subject" / "SKILL.md")
    round1 = body.split("## 1. Ask, round 1", 1)[1].split("\n## 2.", 1)[0]
    rows = [r for r in re.findall(r"^\| (.+?) \|", round1, re.M) if r not in ("Header", "---")]
    assert rows == ["Exam date", "Format", "Cheat sheet", "Hours/week"]
    assert all(len(r) <= 12 for r in rows)  # AskUserQuestion headers
    assert "past exams or" in round1 and "language" in round1
    round2 = body.split("## 6. Ask, round 2", 1)[1].split("\n## 7.", 1)[0]
    for needle in ("focus 3,5; skip 9; merge 6+7; ok", "mock exams", "scope", "Go"):
        assert needle in round2


@pytest.mark.parametrize("name", ["register-new-subject", "add-material"])
def test_ingest_commands_cap_agents_and_judge_by_files(name: str):
    _, body = split(SKILLS / name / "SKILL.md")
    assert "at most 6" in body
    assert "pipeline status" in body
    assert "not from" in body or "never from" in body  # agents' reports are not the gate
    for agent in ("ingester", "exam-analyst"):
        assert f"`{agent}`" in body
    # the user's folder is read by studykit ingest only
    assert "Never Read, Write or list" in body


def test_add_material_uses_the_rebuild_dependencies():
    _, body = split(SKILLS / "add-material" / "SKILL.md")
    spec = (REPO / "docs" / "architecture.md").read_text("utf-8")
    block = spec.split("**Rebuild dependencies**", 1)[1].split("```", 2)[1].strip()
    assert block in body
    for part in ("summary", "exercises", "mc", "overview", "exams", "plan"):
        assert f"/regenerate <c> {part}" in body


RULE_FOR = {
    "uv run --frozen studykit": "Bash(uv run --frozen studykit *)",
    "date -u": "Bash(date -u *)",
    "mkdir -p": "Bash(mkdir -p *)",
    "cp -p": "Bash(cp -p *)",
    "ls ": "Bash(ls *)",
}


@pytest.mark.parametrize("name", sorted(COMMANDS - {"tutor", "examine"}))
def test_commands_preapprove_what_they_run(name: str):
    """A command's allowed-tools cover the shell commands it writes out (§5.1); `just` is
    allowed project-wide."""
    data, body = split(SKILLS / name / "SKILL.md")
    allowed = set(data.get("allowed-tools") or [])
    for snippet in code_snippets(body):
        for prefix, rule in RULE_FOR.items():
            if snippet.startswith(prefix):
                assert rule in allowed, f"{name}: {snippet}"


# --- settings.json ------------------------------------------------------------------------


def settings() -> dict:
    return json.loads((CLAUDE / "settings.json").read_text("utf-8"))


def hook_command(event: str, matcher: str) -> dict:
    (group,) = [g for g in settings()["hooks"][event] if g["matcher"] == matcher]
    (hook,) = group["hooks"]
    assert hook["type"] == "command"
    return hook


def test_settings_attribution_and_permissions():
    data = settings()
    assert data["attribution"] == {"commit": "", "pr": ""}
    perms = data["permissions"]
    assert set(perms["allow"]) == {
        "Bash(just *)",
        "Bash(uv run --frozen studykit *)",
        "Bash(uv run --frozen python courses/*)",
        "Read(/courses/**)",
        "Edit(/courses/**)",
    }
    # Write(path) rules never match (Claude Code checks writes against Edit rules)
    assert not any(r.startswith("Write(") for r in perms["allow"] + perms["deny"])
    assert set(perms["deny"]) == {"Bash(git add -f *)", "Bash(git add --force *)"}
    assert not any(".claude" in r for r in perms["deny"])
    assert set(data["hooks"]) == {"PreToolUse", "PostToolUse"}


def test_settings_hooks():
    lint_hook = hook_command("PostToolUse", "Write|Edit")
    assert lint_hook["command"] == (
        'uv run --frozen --project "${CLAUDE_PROJECT_DIR}" studykit lint --hook'
    )
    git_hook = hook_command("PreToolUse", "Bash")
    assert git_hook["if"] == "Bash(git *)"
    assert git_hook["command"] == (
        'uv run --frozen --project "${CLAUDE_PROJECT_DIR}" studykit hook pre-git'
    )


# --- the hook commands as Claude Code runs them -------------------------------------------


def run_hook(command: str, payload: dict, cwd: Path, **env: str) -> subprocess.CompletedProcess:
    if shutil.which("uv") is None:
        pytest.skip("uv is not installed")
    environ = {k: v for k, v in os.environ.items() if k not in ("VIRTUAL_ENV", "STUDYKIT_ROOT")}
    environ.update(CLAUDE_PROJECT_DIR=str(REPO), **env)
    return subprocess.run(
        ["bash", "-c", command],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=cwd,
        env=environ,
        timeout=180,
        check=False,
    )


def event(name: str, tool: str, cwd: Path, **tool_input) -> dict:
    return {
        "session_id": "test",
        "cwd": str(cwd),
        "hook_event_name": name,
        "tool_name": tool,
        "tool_input": tool_input,
    }


def test_lint_hook_catches_a_broken_fence_from_any_directory(tmp_path: Path):
    courses = tmp_path / "courses"
    course = courses / "sample-course"
    shutil.copytree(SAMPLE, course, ignore=shutil.ignore_patterns("_build"))
    exercise = course / "exercises" / "rc-filter" / "ex-rc-tp-grenzfrequenz.md"
    exercise.write_text(exercise.read_text("utf-8").replace("::: hint\n", ":::hint\n", 1))
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    command = hook_command("PostToolUse", "Write|Edit")["command"]

    done = run_hook(
        command,
        event("PostToolUse", "Edit", elsewhere, file_path=str(exercise)),
        elsewhere,
        STUDYKIT_COURSES_DIR=str(courses),
    )
    assert done.returncode == 2, done.stderr
    assert "SK-BLOCK-" in done.stderr
    assert "ex-rc-tp-grenzfrequenz.md" in done.stderr

    # normal work outside the courses is never blocked
    other = run_hook(
        command,
        event("PostToolUse", "Write", elsewhere, file_path=str(REPO / "README.md")),
        elsewhere,
        STUDYKIT_COURSES_DIR=str(courses),
    )
    assert (other.returncode, other.stdout, other.stderr) == (0, "", "")


def test_pre_git_hook_denies_forced_adds_only(tmp_path: Path):
    command = hook_command("PreToolUse", "Bash")["command"]
    denied = run_hook(command, event("PreToolUse", "Bash", REPO, command="git add -f x"), tmp_path)
    assert denied.returncode == 0
    decision = json.loads(denied.stdout)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    allowed = run_hook(command, event("PreToolUse", "Bash", REPO, command="git status"), tmp_path)
    assert (allowed.returncode, allowed.stdout) == (0, "")


def test_verifier_guard_hook_keeps_the_verifier_blind(tmp_path: Path):
    data, _ = split(AGENTS / "verifier.md")
    command = data["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    course = tmp_path / "courses" / "sample-course"
    shutil.copytree(SAMPLE, course, ignore=shutil.ignore_patterns("_build"))
    exercise = course / "exercises" / "rc-filter" / "ex-rc-tp-grenzfrequenz.md"

    read = run_hook(command, event("PreToolUse", "Read", tmp_path, file_path=str(exercise)), REPO)
    assert json.loads(read.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"
    blind = course / "_build" / "blind" / "ex-rc-tp-grenzfrequenz.md"
    ok = run_hook(command, event("PreToolUse", "Read", tmp_path, file_path=str(blind)), REPO)
    assert (ok.returncode, ok.stdout) == (0, "")
    write = run_hook(
        command,
        event("PreToolUse", "Write", tmp_path, file_path=str(course / "summary" / "x.md")),
        REPO,
    )
    assert json.loads(write.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


# --- CLAUDE.md ----------------------------------------------------------------------------


@pytest.mark.parametrize("path", RULE_FILES, ids=lambda p: p.name)
def test_rule_files_state_the_rules(path: Path):
    text = path.read_text("utf-8")
    for needle in (
        "courses/",
        "PDFs",
        "Co-Authored-By",
        "course.lang",
        "Figures are code",
        "studykit calc",
        "studykit validate",
        "studykit ls",
    ):
        assert needle in text, needle


def test_rule_files_share_the_hard_rules():
    def hard_rules(path: Path) -> str:
        return path.read_text("utf-8").split("## Hard rules", 1)[1].split("\n## ", 1)[0]

    assert hard_rules(REPO / "CLAUDE.md") == hard_rules(REPO / "AGENTS.md")


# --- Codex (§5.5) ---------------------------------------------------------------------------


def test_codex_finds_the_skills_through_the_link():
    link = REPO / ".agents" / "skills"
    assert link.is_symlink() and os.readlink(link) == "../.claude/skills"
    assert {p.parent.name for p in link.glob("*/SKILL.md")} == INTERNAL | COMMANDS


@pytest.mark.parametrize("name", sorted(COMMANDS))
def test_codex_runs_user_commands_only_when_typed(name: str):
    policy = yaml.safe_load((SKILLS / name / "agents" / "openai.yaml").read_text("utf-8"))
    assert policy == {"policy": {"allow_implicit_invocation": False}}


def test_codex_agents_are_generated_from_the_claude_agents():
    assert codex.sync(check=True, root=REPO) == []
    assert {p.stem for p in (CODEX / "agents").glob("*.toml")} == set(codex.CODEX_AGENTS)
    for name in codex.CODEX_AGENTS:
        data = tomllib.loads((CODEX / "agents" / f"{name}.toml").read_text("utf-8"))
        meta, body = split(AGENTS / f"{name}.md")
        assert data["name"] == name and data["description"] == meta["description"]
        assert data["model_reasoning_effort"] == meta["effort"]
        assert body.strip() in data["developer_instructions"]
        for skill in meta.get("skills", []):
            assert f".claude/skills/{skill}/SKILL.md" in data["developer_instructions"]
    assert (
        "keep yourself blind"
        in tomllib.loads((CODEX / "agents" / "verifier.toml").read_text("utf-8"))[
            "developer_instructions"
        ]
    )


def test_codex_agents_sync_reports_and_repairs_drift(tmp_path: Path):
    shutil.copytree(AGENTS, tmp_path / ".claude" / "agents")
    assert len(codex.sync(check=True, root=tmp_path)) == len(codex.CODEX_AGENTS)
    stray = tmp_path / ".codex" / "agents" / "old.toml"
    stray.parent.mkdir(parents=True)
    stray.write_text("")
    codex.sync(check=False, root=tmp_path)
    assert not stray.exists()
    assert codex.sync(check=True, root=tmp_path) == []


def test_gitignore_keeps_the_codex_project_layer_tracked():
    def ignored(path: str) -> bool:
        done = subprocess.run(
            ["git", "check-ignore", "--no-index", "-q", path], cwd=REPO, check=False
        )
        assert done.returncode in (0, 1)
        return done.returncode == 0

    for path in [
        ".codex/config.toml",
        ".codex/hooks.json",
        ".codex/agents/new-agent.toml",
        ".codex/rules/new.rules",
    ]:
        assert not ignored(path), path
    assert ignored(".codex/local-state.json")


def test_codex_config_caps_the_agents():
    config = tomllib.loads((CODEX / "config.toml").read_text("utf-8"))
    assert config == {"agents": {"max_concurrent_threads_per_session": 6}}


def test_codex_rules_forbid_forced_adds():
    text = (CODEX / "rules" / "studykit.rules").read_text("utf-8")
    assert 'pattern = ["git", "add", ["-f", "--force"]]' in text
    assert 'decision = "forbidden"' in text


def codex_hook(event_name: str, matcher: str) -> str:
    data = json.loads((CODEX / "hooks.json").read_text("utf-8"))
    assert set(data["hooks"]) == {"PreToolUse", "PostToolUse"}
    (group,) = [g for g in data["hooks"][event_name] if g["matcher"] == matcher]
    (handler,) = group["hooks"]
    assert handler["type"] == "command"
    return handler["command"]


def test_codex_hooks_run_the_same_commands():
    root = '"$(git rev-parse --show-toplevel)"'
    assert codex_hook("PostToolUse", "^apply_patch$") == (
        f"uv run --frozen --project {root} studykit lint --hook"
    )
    assert codex_hook("PreToolUse", "^Bash$") == (
        f"uv run --frozen --project {root} studykit hook pre-git"
    )


def test_codex_lint_hook_reads_apply_patch(tmp_path: Path):
    courses = tmp_path / "courses"
    course = courses / "sample-course"
    shutil.copytree(SAMPLE, course, ignore=shutil.ignore_patterns("_build"))
    exercise = course / "exercises" / "rc-filter" / "ex-rc-tp-grenzfrequenz.md"
    exercise.write_text(exercise.read_text("utf-8").replace("::: hint\n", ":::hint\n", 1))
    rel = os.path.relpath(exercise, course)
    patch = f"*** Begin Patch\n*** Update File: {rel}\n@@\n-a\n+b\n*** End Patch\n"
    command = codex_hook("PostToolUse", "^apply_patch$")
    # Codex runs hooks in the session's directory, somewhere inside the repository
    done = run_hook(
        command,
        event("PostToolUse", "apply_patch", course, command=patch),
        REPO / "src",
        STUDYKIT_COURSES_DIR=str(courses),
    )
    assert done.returncode == 2, done.stderr
    assert "SK-BLOCK-" in done.stderr and "ex-rc-tp-grenzfrequenz.md" in done.stderr
    readme = "*** Begin Patch\n*** Add File: README.md\n+x\n*** End Patch\n"
    other = run_hook(
        command,
        event("PostToolUse", "apply_patch", REPO, command=readme),
        REPO,
        STUDYKIT_COURSES_DIR=str(courses),
    )
    assert (other.returncode, other.stdout, other.stderr) == (0, "", "")


def test_codex_pre_git_hook_denies_forced_adds(tmp_path: Path):
    command = codex_hook("PreToolUse", "^Bash$")
    denied = run_hook(command, event("PreToolUse", "Bash", REPO, command="git add -f x"), REPO)
    assert json.loads(denied.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"
    allowed = run_hook(command, event("PreToolUse", "Bash", REPO, command="ls"), REPO / "src")
    assert (allowed.returncode, allowed.stdout) == (0, "")
