"""`studykit hook verifier-guard` and `studykit hook pre-git` on sample hook events."""

from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import pytest

from studykit import cli, hook


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repository with one course under courses/ and the layout the guard knows."""
    root = tmp_path / "repo"
    course = root / "courses" / "get2"
    for rel in (
        "exercises/rc",
        "mc",
        "exams/pk1",
        "checks",
        "state/verify",
        "summary",
        "_build/blind",
        "_build/figures",
        "_build/typ",
        "_history/x",
    ):
        (course / rel).mkdir(parents=True)
    (course / "course.yaml").write_text("id: get2\n")
    (course / "exercises" / "rc" / "ex-a.md").write_text("---\n")
    (root / "courses" / "README.md").write_text("readme\n")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def event(tool: str, cwd: Path, **tool_input) -> dict:
    return {
        "session_id": "s",
        "cwd": str(cwd),
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": tool_input,
        "agent_type": "verifier",
    }


def decide(name: str, payload: dict) -> str | None:
    """The deny reason, or None when the hook makes no decision."""
    out = hook.run(name, json.dumps(payload))
    if not out:
        return None
    data = json.loads(out)["hookSpecificOutput"]
    assert (data["hookEventName"], data["permissionDecision"]) == ("PreToolUse", "deny")
    return data["permissionDecisionReason"]


C = "courses/get2"


@pytest.mark.parametrize(
    "path",
    [
        f"{C}/exercises/rc/ex-a.md",
        f"{C}/mc/rc.md",
        f"{C}/exams/pk1/01-pk1-t1.md",
        f"{C}/state/verify/ex-a.json",
        f"{C}/_history/x/old.md",
        f"{C}/_build/typ/exercises.md",
        f"{C}/_build/index.json",
        f"{C}/_build/figures/rc.facts.json",
        f"{C}/exercises",
        "site/dist/c/get2/exercises/ex-a/index.html",
        "courses/new/exercises/ex-b.md",  # not there yet: judged by its segments
    ],
)
def test_guard_denies_reading_items(repo: Path, path: str):
    reason = decide("verifier-guard", event("Read", repo, file_path=path))
    assert reason and reason.startswith("verifier-guard:") and "studykit blind" in reason
    absolute = event("Read", repo / "elsewhere", file_path=str(repo / path))
    assert decide("verifier-guard", absolute)


@pytest.mark.parametrize(
    "path",
    [
        f"{C}/_build/blind/ex-a.md",
        f"{C}/_build/figures/rc.png",
        f"{C}/checks/ex-a.py",
        f"{C}/summary/01-rc.md",
        f"{C}/course.yaml",
        "docs/architecture.md",
    ],
)
def test_guard_allows_the_blind_view_and_checks(repo: Path, path: str):
    assert decide("verifier-guard", event("Read", repo, file_path=path)) is None


def test_guard_follows_symlinks(repo: Path):
    checks = repo / C / "checks"
    (checks / "up").symlink_to("..")
    (checks / "key.md").symlink_to("../mc/rc.md")
    for path in (f"{C}/checks/up/exercises/rc/ex-a.md", f"{C}/checks/key.md"):
        assert decide("verifier-guard", event("Read", repo, file_path=path)), path
    write = event("Write", repo, file_path=f"{C}/checks/up/mc/rc.md", content="x")
    assert "writes only into a course's checks/" in decide("verifier-guard", write)
    grep = event("Grep", repo, pattern="fg", path=f"{C}/checks/up/exams")
    assert decide("verifier-guard", grep)
    assert (
        decide("verifier-guard", event("Read", repo, file_path=f"{C}/checks/up/course.yaml"))
        is None
    )


def test_guard_on_grep_and_glob(repo: Path):
    course = repo / C
    assert decide("verifier-guard", event("Grep", repo, pattern="fg"))  # the repo has courses
    assert decide("verifier-guard", event("Grep", repo, pattern="fg", path=f"{C}/mc"))
    assert decide("verifier-guard", event("Grep", course / "checks", pattern="fg")) is None
    assert decide(
        "verifier-guard", event("Grep", course, pattern="x", path="checks", glob="../mc/*.md")
    )
    assert decide("verifier-guard", event("Glob", repo, pattern="**/*.md"))
    assert decide("verifier-guard", event("Glob", course, pattern="exercises/**/*.md"))
    assert decide("verifier-guard", event("Glob", course / "checks", pattern="*.py")) is None


def test_guard_on_writes(repo: Path):
    ok = event("Write", repo, file_path=f"{C}/checks/ex-a.py", content="answers(fg=1)\n")
    assert decide("verifier-guard", ok) is None
    outside = event("Write", repo, file_path=f"{C}/mc/rc.md", content="x")
    assert "writes only into a course's checks/" in decide("verifier-guard", outside)
    sneaky = event(
        "Write",
        repo,
        file_path=f"{C}/checks/ex-a.py",
        content="open('../exercises/rc/ex-a.md').read()",
    )
    assert "must not read course item files" in decide("verifier-guard", sneaky)
    edit = event(
        "Edit",
        repo,
        file_path=f"{C}/checks/ex-a.py",
        old_string="1",
        new_string="open('../mc/rc.md')",
    )
    assert decide("verifier-guard", edit)


@pytest.mark.parametrize(
    "code",
    [
        "# capacitor voltage in steady state\nanswers(uc=5.0)\n",
        'answers(uc=5.0, method="steady state analysis")\n',
        "u0 = 0.0  # initial state\n",
        'review(True, "exams use the same values; mc and state are words here")\n',
    ],
)
def test_guard_allows_words_that_are_dir_names_in_check_code(repo: Path, code: str):
    write = event("Write", repo, file_path=f"{C}/checks/ex-a.py", content=code)
    assert decide("verifier-guard", write) is None, code


@pytest.mark.parametrize(
    "code",
    [
        'Path(__file__).parent.parent / "exercises" / "rc"',
        "glob.glob('../exams/*/*.md')",
        "open(root + '/state/verify/ex-a.json')",
        'x = "mc"\nopen(f"../{x}/rc.md")',
        "p = 'exercises'\n",
    ],
)
def test_guard_denies_paths_in_check_code(repo: Path, code: str):
    write = event("Write", repo, file_path=f"{C}/checks/ex-a.py", content=code)
    assert decide("verifier-guard", write), code


@pytest.mark.parametrize(
    "command",
    [
        f"cat {C}/exercises/rc/ex-a.md",
        f"grep -r fg {C}/mc",
        "ls exams",
        f"python -c \"print(open('{C}/mc/rc.md').read())\"",
        f"uv run --frozen studykit blind get2 ex-a && cat {C}/exercises/rc/ex-a.md",
        f"head $(ls {C}/mc/*.md)",
        f"cat {C}/state/verify/ex-a.json",
        f"cat {C}/_build/typ/exercises.md",
        "uv run --frozen studykit render get2 --json",
        "studykit verify get2 ex-a --json",
        "uv run --frozen studykit verify get2 ex-a --show-key",
        "uv run --frozen studykit verify get2 ex-a --show",  # argparse-style prefixes
        "studykit verify get2 ex-a --js",
        "studykit verify get2 ex-a --json=1",
        "studykit pdf get2",
        f"python ../checks/../mc/rc.md {C}/mc",
        # no blocked name in the text: globs, braces, recursion and links
        f"cat {C}/exer*/rc/*.md",
        f"cat {C}/{{exercises,summary}}/rc/ex-a.md",
        f"cat < {C}/checks/../e?ercises/rc/ex-a.md",
        f"grep -r key {C}",
        "grep -rn . courses",
        "grep -r key .",
        f"find {C} -exec cat {{}} +",
        f"cd {C} && cat ex*/rc/*.md",
        f"cd {C} && grep -r key",
        f"cd {C}/checks && rg key ..",
        f"cd {C} && find -name '*.md'",
        f"ln -s .. {C}/checks/up",
    ],
)
def test_guard_denies_bash_that_reads_items(repo: Path, command: str):
    assert decide("verifier-guard", event("Bash", repo, command=command)), command


@pytest.mark.parametrize(
    "command",
    [
        "uv run --frozen studykit blind get2 ex-a",
        "studykit calc '1/(2*pi*R*C)' --subs R=1e3 C=1e-7",
        f"uv run --frozen studykit verify {C} ex-a",
        "studykit verify get2 mc --status",
        f"uv run --frozen python {C}/checks/ex-a.py",
        "python checks/ex-a.py | tail -1",
        f"cat {C}/_build/blind/ex-a.md",
        "python -c 'import sympy; print(sympy.sqrt(2))'",
        "python -c 'from studykit.check import mc_numeric'",
        "ls",
        f"cat {C}/checks/*.py",
        f"cd {C} && uv run --frozen python checks/ex-a.py",
        f"cd {C} && ls checks",
        f"cd {C}/checks && grep -rn fg .",
        f"grep -n fg {C}/checks/ex-a.py",
        "python -c 'print(2*3, [1, 2][0], {1, 2})'",
    ],
)
def test_guard_allows_the_protocol(repo: Path, command: str):
    assert decide("verifier-guard", event("Bash", repo, command=command)) is None, command


@pytest.mark.parametrize(
    "command",
    [
        "git add -f courses/get2/mc/rc.md",
        "git add --force notes.txt",
        "git add -Af",
        "git add courses/get2",
        "git add courses/",
        "git -C courses/get2 add mc/rc.md",
        "git add 'courses/*'",
        "cd x && git add courses/get2/course.yaml",
        "git commit -m 'feat: x' courses/get2/course.yaml",
        "git commit --no-verify -m 'feat: x'",
        "git commit -nm 'feat: x'",
        "git stage courses/get2/mc",
    ],
)
def test_pre_git_blocks(repo: Path, command: str):
    reason = decide("pre-git", event("Bash", repo, command=command))
    assert reason and reason.startswith("pre-git:"), command


@pytest.mark.parametrize(
    "command",
    [
        "git add courses/README.md",
        "git add src/studykit/verify.py tests",
        "git add -A",
        "git commit -m 'feat(verify): add the ledger'",
        "git commit -am 'fix: n is not a flag here'",
        "git commit -m 'courses/get2 is mentioned only in the message'",
        "git status",
        "git log --oneline -- courses",
        "echo git add -f",
    ],
)
def test_pre_git_allows(repo: Path, command: str):
    assert decide("pre-git", event("Bash", repo, command=command)) is None, command


def test_pre_git_sees_course_files_already_staged(repo: Path):
    subprocess.run(["git", "-C", str(repo), "add", "-f", f"{C}/course.yaml"], check=True)
    reason = decide("pre-git", event("Bash", repo, command="git commit -m 'chore: x'"))
    assert reason and f"{C}/course.yaml" in reason


def test_other_tools_and_bad_input_make_no_decision(repo: Path):
    assert decide("pre-git", event("Read", repo, file_path="courses/get2/mc/rc.md")) is None
    assert hook.run("verifier-guard", "not json") == ""
    assert hook.run("pre-git", "[]") == ""
    assert decide("verifier-guard", event("WebFetch", repo, url="https://x.y")) is None


def test_cli(repo: Path, monkeypatch, capsys):
    payload = event("Read", repo, file_path=f"{C}/mc/rc.md")
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    assert cli.main(["hook", "verifier-guard"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(event("Bash", repo, command="ls"))))
    assert cli.main(["hook", "pre-git"]) == 0
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("flag", ["--show", "--js"])
def test_verify_takes_no_flag_prefixes(flag: str):
    # a prefix would print the key past the guard's flag check
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["verify", "get2", "ex-a", flag])
