"""`studykit hook <name>`: Claude Code PreToolUse hooks (docs/architecture.md §5.1, §5.3).

Each hook reads the hook event JSON on stdin (`tool_name`, `tool_input`, `cwd`, …) and,
to block the call, prints

    {"hookSpecificOutput": {"hookEventName": "PreToolUse",
     "permissionDecision": "deny", "permissionDecisionReason": "…"}}

and exits 0. Without a decision it prints nothing and exits 0, so the normal permission
flow applies. Unreadable input never blocks (a hook bug must not stop the session); the
reasons say what to do instead.

- `verifier-guard` (agent-scoped, the verifier only): keeps the verifier blind. It denies
  Read, Grep and Glob on a course's `exercises/`, `mc/` and `exams/` and on everything
  else that holds keys or solutions (`state/`, `_history/`, `_build/` except `blind/` and
  the figure images, the built site), Grep and Glob over a tree that contains a course,
  writes outside a course's `checks/`, and Bash commands that mention those paths (also
  through `cd`, globs, braces or symlinks), name or recursively search a tree holding a
  course, or make links, unless they are `studykit` (blind, calc, verify, ls, lint,
  validate, fig, index, doctor) or `python checks/…`. `studykit render`, `pdf` and the
  key-revealing `verify --json` and `--show-key` (or a prefix of either) are denied even
  without a path.
- `pre-git` (project-wide, on `Bash(git *)`): denies `git add` with `-f`/`--force` or a
  path under `courses/` (except `courses/README.md`), and `git commit` with a course path,
  `--no-verify`, or course files already staged.
"""

from __future__ import annotations

import glob
import json
import os
import re
import shlex
import subprocess
from collections.abc import Callable, Iterator
from itertools import islice
from pathlib import Path
from typing import Any

BLOCKED_DIRS = {"exercises", "mc", "exams", "_history", "state"}
BUILD_OK = {"blind", "figures"}
SITE_PARTS = [("site", "dist"), ("site", ".astro")]
VERIFIER_STUDYKIT = {"blind", "calc", "verify", "ls", "lint", "validate", "fig", "index", "doctor"}
KEY_FLAGS = {"--json", "--show-key"}
OPERATORS = {";", "&&", "||", "|", "&", "|&", "\n", "(", ")"}
SUBSTITUTION = re.compile(r"\$\(|`|<\(|>\(")
# a path mention: one of the blocked names as a whole path segment
MENTION = re.compile(
    r"(?:^|[\s'\"=/:])(?:exercises|mc|exams|_history|state)(?=/|\s|$|['\"])"
    r"|_build/(?!blind\b|figures/[^\s'\"]*\.(?:png|svg)\b)"
    r"|\.facts\.json|site/dist|site/\.astro|(?:^|[\s'\"=/])\.cache/"
)
# the same in check code, where only a path counts: a blocked name between '/' or quotes, or
# before a '/' ("../exercises/x.md", / "mc"), not a word of a comment ("steady state")
CODE_MENTION = re.compile(
    r"(?<=[/'\"])(?:exercises|mc|exams|_history|state)(?=[/'\"]|$)"
    r"|(?<![\w.-])(?:exercises|mc|exams|_history|state)/"
    r"|_build/(?!blind\b|figures/[^\s'\"]*\.(?:png|svg)\b)"
    r"|\.facts\.json|site/dist|site/\.astro|(?:^|[\s'\"=/])\.cache/",
    re.MULTILINE,
)


def deny(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


# --- paths -----------------------------------------------------------------------------------


def _resolve(raw: str, cwd: Path) -> Path:
    path = Path(os.path.expanduser(raw))
    path = path if path.is_absolute() else cwd / path
    return Path(os.path.normpath(path))


def course_root(path: Path) -> Path | None:
    for parent in [path, *path.parents]:
        if (parent / "course.yaml").is_file():
            return parent
    return None


def blocked_path(path: Path) -> str | None:
    """Why the verifier may not look at `path`, or None. A symlink is judged by its own
    path and by the path it resolves to (`checks/up -> ..` must not open the items)."""
    why = _blocked_lexically(path)
    real = Path(os.path.realpath(path))
    if why is None and real != path:
        why = _blocked_lexically(real)
    return why


def _blocked_lexically(path: Path) -> str | None:
    parts = path.parts
    for a, b in SITE_PARTS:
        if any(parts[i : i + 2] == (a, b) for i in range(len(parts) - 1)):
            return "the built site holds every key and solution"
    if ".cache" in parts:
        return ".cache holds copies of courses"
    if path.name.endswith(".facts.json"):
        return "figure facts can hold results"
    root = course_root(path)
    if root is not None and root != path:
        rel = path.relative_to(root).parts
        if rel[0] in BLOCKED_DIRS:
            return f"{rel[0]}/ holds the items and their keys"
        if rel[0] == "_build" and (len(rel) < 2 or rel[1] not in BUILD_OK):
            return "_build/ holds rendered items with their solutions"
        return None
    # a path that does not exist (yet): judge it by its segments
    for i, part in enumerate(parts):
        if part in BLOCKED_DIRS and i >= 2 and parts[i - 2] in ("courses", "examples"):
            return f"{part}/ holds the items and their keys"
    return None


def contains_course(path: Path, depth: int = 2) -> bool:
    """True if a course lives at or below `path` (within `depth` levels)."""
    if not path.is_dir():
        return False
    if (path / "course.yaml").is_file():
        return True
    pattern = "course.yaml"
    for _ in range(depth):
        pattern = "*/" + pattern
        if next(path.glob(pattern), None) is not None:
            return True
    return False


# --- shell commands ------------------------------------------------------------------------


def segments(command: str) -> Iterator[list[str]]:
    """The simple commands of a shell line, as word lists (operators split them)."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()\n")
    lexer.whitespace_split = True
    lexer.commenters = ""
    words: list[str] = []
    try:
        for token in lexer:
            if token in OPERATORS or set(token) <= set(";&|()\n"):
                if words:
                    yield words
                words = []
            else:
                words.append(token)
    except ValueError:  # unbalanced quotes: judge the raw text as one command
        yield command.split()
        return
    if words:
        yield words


def _strip_env(words: list[str]) -> list[str]:
    i = 0
    while i < len(words) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[i]):
        i += 1
    if words[i : i + 1] == ["env"]:
        return _strip_env(words[i + 1 :])
    return words[i:]


UV_RUN_OPTS_WITH_VALUE = {"--project", "--directory", "--with", "--python", "-p", "--group"}


def _program(words: list[str]) -> list[str]:
    """The command after env assignments and an `uv run [options]` prefix."""
    words = _strip_env(words)
    if words[:2] == ["uv", "run"]:
        i = 2
        while i < len(words) and words[i].startswith("-"):
            i += 2 if words[i] in UV_RUN_OPTS_WITH_VALUE else 1
        words = words[i:]
    if words and words[0].endswith("/studykit"):
        words = ["studykit", *words[1:]]
    return words


def _key_flag(word: str) -> bool:
    """`--json`, `--show-key` or a prefix of one (`--show`, `--js=1`), as argparse reads it."""
    name = word.split("=", 1)[0]
    return len(name) >= 3 and name.startswith("--") and any(f.startswith(name) for f in KEY_FLAGS)


def _verifier_allowed(words: list[str]) -> str | None:
    """None if the verifier may run this command whatever paths it names; else why not."""
    prog = _program(words)
    if not prog:
        return "empty command"
    name = os.path.basename(prog[0])
    if name == "studykit":
        sub = prog[1] if len(prog) > 1 else ""
        if sub not in VERIFIER_STUDYKIT:
            return f"`studykit {sub}` is not for the verifier"
        if sub == "verify" and any(_key_flag(w) for w in prog[2:]):
            return "`studykit verify --json`/`--show-key` print the key"
        return None
    if re.fullmatch(r"python3?(\.\d+)?", name) and len(prog) > 1:
        script = prog[1]
        in_checks = script.startswith("checks/") or "/checks/" in script
        if in_checks and ".." not in Path(script).parts:
            return None
    return "only studykit and python checks/… may name course item paths"


GLOB_CHARS = re.compile(r"[*?\[]")
BRACES = re.compile(r"\{([^{}]*,[^{}]*)\}")
REDIRECT = re.compile(r"^\d*(?:<|>{1,2})&?")


def _expand_braces(word: str, limit: int = 64) -> list[str]:
    """The words a shell brace expansion makes of `word` (`{exercises,mc}/x`)."""
    match = BRACES.search(word)
    if match is None:
        return [word]
    out: list[str] = []
    for alt in match[1].split(","):
        out.extend(_expand_braces(word[: match.start()] + alt + word[match.end() :], limit))
        if len(out) >= limit:
            break
    return out[:limit]


def _word_paths(word: str, cwd: Path) -> Iterator[Path]:
    """The paths a shell word can stand for: itself, its brace expansions and glob matches."""
    word = REDIRECT.sub("", word)
    if word.startswith("-"):
        if "=" not in word:
            return
        word = word.split("=", 1)[1]  # --file=<path>
    for text in _expand_braces(word) if word else []:
        path = _resolve(text, cwd)
        yield path
        if GLOB_CHARS.search(text):
            try:
                yield from (Path(p) for p in islice(glob.iglob(str(path)), 500))
            except OSError, ValueError, re.error:
                continue


def _word_blocked(path: Path) -> str | None:
    why = blocked_path(path)
    if why is None and (contains_course(path) or contains_course(Path(os.path.realpath(path)))):
        why = "it holds a course; read single files of checks/ or the blind view"
    return why


def verifier_bash(command: str, cwd: Path) -> str | None:
    if SUBSTITUTION.search(command):
        if MENTION.search(command):
            return "command substitution around course item paths"
        return None
    where = cwd
    for words in segments(command):
        prog = _program(words)
        if not prog:
            continue
        name = os.path.basename(prog[0])
        if name == "studykit":
            why = _verifier_allowed(words)
            if why:
                return why
            continue
        if name in ("cd", "pushd"):  # reads nothing; later commands run there
            args = [w for w in prog[1:] if not w.startswith("-")]
            where = _resolve(args[0], where) if args else Path.home()
            continue
        if _verifier_allowed(words) is None:  # python checks/…
            continue
        if name == "ln":
            return "the verifier makes no links"
        if MENTION.search(" ".join(words)):
            return _verifier_allowed(words)
        # globs, braces, recursive reads and symlinks name no blocked segment: judge the
        # paths each word stands for (`grep -r key <course>`, `cat ex*/*.md`)
        for word in prog:
            for path in _word_paths(word, where):
                why = _word_blocked(path)
                if why:
                    return f"`{word}`: {why}"
        if _recursive(name, prog[1:]) and not any(
            _resolve(w, where).exists() for w in prog[1:] if not w.startswith("-")
        ):  # no path given: it searches the working directory
            why = _word_blocked(where)
            if why:
                return f"`{name}` in {where}: {why}"
    return None


RECURSIVE_TOOLS = {"rg", "ag", "ack", "find", "tree", "fd", "fdfind", "du"}


def _recursive(name: str, args: list[str]) -> bool:
    """True if the command walks a directory tree (the working directory without a path)."""
    if name in RECURSIVE_TOOLS:
        return True
    flags = [a for a in args if a.startswith("-") and not a.startswith("--")]
    if name in ("grep", "egrep", "fgrep"):
        return any(a in ("--recursive", "--dereference-recursive") for a in args) or any(
            "r" in f or "R" in f for f in flags
        )
    return name == "ls" and any("R" in f for f in flags)


# --- the hooks -----------------------------------------------------------------------------

GUARD_HINT = (
    " The verifier works blind: read `studykit blind <course> <id>` (_build/blind/<id>.md), "
    "compute in Python, write checks/<id>.py or .json and run `studykit verify`."
)


def verifier_guard(payload: dict[str, Any]) -> dict[str, Any] | None:
    tool = payload.get("tool_name")
    data = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    cwd = Path(payload["cwd"]) if isinstance(payload.get("cwd"), str) else Path.cwd()
    if tool == "Read":
        raw = data.get("file_path")
        if isinstance(raw, str) and raw:
            why = blocked_path(_resolve(raw, cwd))
            if why:
                return deny(f"verifier-guard: {raw}: {why}." + GUARD_HINT)
        return None
    if tool in ("Grep", "Glob"):
        raw = data.get("path") if isinstance(data.get("path"), str) and data.get("path") else "."
        root = _resolve(raw, cwd)
        why = blocked_path(root)
        if why is None and contains_course(root):
            why = "the search would cover course items"
        pattern = " ".join(str(data.get(k) or "") for k in ("pattern", "glob"))
        if why is None and tool == "Glob" and MENTION.search(pattern):
            why = "the pattern names course item paths"
        if why is None and tool == "Grep" and data.get("glob") and MENTION.search(data["glob"]):
            why = "the glob names course item paths"
        if why:
            return deny(f"verifier-guard: {tool} {raw}: {why}." + GUARD_HINT)
        return None
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        raw = data.get("file_path") or data.get("notebook_path")
        if not isinstance(raw, str) or not raw:
            return None
        path = Path(os.path.realpath(_resolve(raw, cwd)))  # where the write would land
        root = course_root(path.parent)
        if root is None or path.relative_to(root).parts[0] != "checks":
            return deny(
                f"verifier-guard: {raw}: the verifier writes only into a course's checks/."
                + GUARD_HINT
            )
        text = "\n".join(str(data.get(k) or "") for k in ("content", "new_string", "new_source"))
        if CODE_MENTION.search(text):
            return deny(
                f"verifier-guard: {raw}: a check must not read course item files; compute "
                "from the blind view." + GUARD_HINT
            )
        return None
    if tool == "Bash":
        command = data.get("command")
        if isinstance(command, str):
            why = verifier_bash(command, cwd)
            if why:
                return deny(f"verifier-guard: {why}." + GUARD_HINT)
    return None


GIT_OPTS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}


def _git(words: list[str], cwd: Path) -> tuple[str, list[str], Path] | None:
    """(subcommand, its arguments, working directory) of a git command line."""
    words = _strip_env(words)
    if not words or os.path.basename(words[0]) != "git":
        return None
    i, where = 1, cwd
    while i < len(words) and words[i].startswith("-"):
        if words[i] == "-C" and i + 1 < len(words):
            where = _resolve(words[i + 1], where)
        i += 2 if words[i] in GIT_OPTS_WITH_VALUE else 1
    if i >= len(words):
        return None
    return words[i], words[i + 1 :], where


def repo_root(where: Path) -> Path:
    for parent in [where, *where.parents]:
        if (parent / ".git").exists():
            return parent
    return where


def course_path(arg: str, where: Path) -> bool:
    """True if a git path argument points into courses/ (README.md excepted)."""
    root = repo_root(where)
    text = arg.split(")", 1)[-1] if arg.startswith(":(") else arg.lstrip(":/")
    path = _resolve(text, where) if not arg.startswith((":/", ":(top)")) else root / text
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        return False
    if rel == "courses/README.md":
        return False
    return rel == "courses" or rel.startswith("courses/")


def _staged_courses(where: Path) -> list[str]:
    try:
        proc = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "-z"],
            cwd=where,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except OSError, subprocess.TimeoutExpired:
        return []
    names = [n for n in proc.stdout.split("\0") if n] if proc.returncode == 0 else []
    return [n for n in names if n.startswith("courses/") and n != "courses/README.md"]


COMMIT_OPTS_WITH_VALUE = {
    "-m",
    "--message",
    "-F",
    "--file",
    "-C",
    "--reuse-message",
    "-c",
    "--reedit-message",
    "--author",
    "--date",
    "--fixup",
    "--squash",
    "-t",
    "--template",
    "--cleanup",
    "-S",
    "--trailer",
    "--pathspec-from-file",
}

SHORT_WITH_VALUE = set("mFCctS")
NO_VERIFY = "pre-git: `git commit --no-verify` would skip the course guard of the pre-commit hook."
GIT_HINT = (
    " Course material stays local: courses/ is gitignored and only courses/README.md is "
    "tracked (CLAUDE.md)."
)


def pre_git(payload: dict[str, Any]) -> dict[str, Any] | None:
    if payload.get("tool_name") != "Bash":
        return None
    data = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    command = data.get("command")
    if not isinstance(command, str):
        return None
    cwd = Path(payload["cwd"]) if isinstance(payload.get("cwd"), str) else Path.cwd()
    for words in segments(command):
        parsed = _git(words, cwd)
        if parsed is None:
            continue
        sub, args, where = parsed
        if sub in ("add", "stage"):
            for arg in args:
                if arg == "--force" or (re.fullmatch(r"-[A-Za-z]+", arg) and "f" in arg[1:]):
                    return deny("pre-git: `git add -f` is never allowed." + GIT_HINT)
            paths = [a for a in args if not a.startswith("-") or a.startswith(":")]
            bad = [a for a in paths if course_path(a, where)]
            if bad:
                return deny(f"pre-git: `git {sub}` of course paths ({', '.join(bad)})." + GIT_HINT)
        elif sub == "commit":
            paths, i = [], 0
            while i < len(args):
                arg = args[i]
                if arg == "--":
                    paths.extend(args[i + 1 :])
                    break
                if arg == "--no-verify":
                    return deny(NO_VERIFY)
                if arg in COMMIT_OPTS_WITH_VALUE:
                    i += 2
                    continue
                if re.fullmatch(r"-[A-Za-z]+", arg):  # a cluster of short flags: -am, -nm
                    for ch in arg[1:]:
                        if ch == "n":
                            return deny(NO_VERIFY)
                        if ch in SHORT_WITH_VALUE:
                            i += 1 if arg.endswith(ch) else 0  # the value is the next word
                            break
                    i += 1
                    continue
                if not arg.startswith("-"):
                    paths.append(arg)
                i += 1
            bad = [a for a in paths if course_path(a, where)]
            staged = _staged_courses(where)
            if bad or staged:
                shown = ", ".join(bad or staged[:5])
                return deny(f"pre-git: the commit would include course files ({shown})." + GIT_HINT)
    return None


HOOKS: dict[str, Callable[[dict[str, Any]], dict[str, Any] | None]] = {
    "verifier-guard": verifier_guard,
    "pre-git": pre_git,
}


def run(name: str, stdin_text: str) -> str:
    """The hook's stdout: a decision as JSON, or '' for no decision."""
    try:
        payload = json.loads(stdin_text or "{}")
    except json.JSONDecodeError:
        return ""
    if not isinstance(payload, dict):
        return ""
    decision = HOOKS[name](payload)
    return json.dumps(decision, ensure_ascii=False) + "\n" if decision else ""
