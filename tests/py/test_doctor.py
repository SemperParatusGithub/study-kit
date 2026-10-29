from pathlib import Path

from studykit import doctor


def _checkout(path: Path, commit_msg: str = "#!/bin/sh\n") -> Path:
    hooks = path / ".githooks"
    hooks.mkdir(parents=True)
    (hooks / "commit-msg").write_text(commit_msg)
    (hooks / "pre-commit").write_text("#!/bin/sh\n")
    return path


def test_hooks_path_relative_or_absolute(tmp_path):
    root = _checkout(tmp_path / "repo")
    assert doctor.hooks_installed(root, ".githooks")
    assert doctor.hooks_installed(root, str(root / ".githooks"))
    assert not doctor.hooks_installed(root, "")
    assert not doctor.hooks_installed(root, "hooks")


def test_hooks_path_of_another_checkout_counts_when_its_hooks_match(tmp_path):
    # a git worktree shares the main checkout's config, so core.hooksPath may point there
    main = _checkout(tmp_path / "main")
    worktree = _checkout(tmp_path / "worktree")
    assert doctor.hooks_installed(worktree, str(main / ".githooks"))
    stale = _checkout(tmp_path / "stale", commit_msg="#!/bin/sh\nexit 0\n")
    assert not doctor.hooks_installed(worktree, str(stale / ".githooks"))
