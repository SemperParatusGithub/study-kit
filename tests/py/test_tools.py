import hashlib
import tarfile
from pathlib import Path

import pytest

from studykit import tools


def test_parse_version_compares_numerically():
    assert tools.parse_version("1.59.0") == (1, 59, 0)
    assert tools.parse_version("v24.17.0") > tools.parse_version("24.9.9")
    assert tools.parse_version("0.15.1 (9dfd3a08)") == (0, 15, 1)


def test_toolchain_pins_every_binary_for_both_platforms():
    toolchain = tools.load_toolchain(tools.repo_root())
    for name, spec in toolchain["binaries"].items():
        assert set(spec["platforms"]) == {"macos-arm64", "linux-x86_64"}, name
        for asset in spec["platforms"].values():
            assert len(asset["sha256"]) == 64, name
            assert spec["version"] in asset["url"], name


def _fake_tool(tmp_path: Path) -> tuple[Path, str]:
    script = tmp_path / "src" / "faketool"
    script.parent.mkdir()
    script.write_text("#!/bin/sh\necho 'faketool 1.2.3'\n")
    script.chmod(0o755)
    archive = tmp_path / "faketool.tar.gz"
    with tarfile.open(archive, "w:gz") as tf:
        tf.add(script, arcname="faketool-1.2.3/faketool")
    return archive, hashlib.sha256(archive.read_bytes()).hexdigest()


def _spec(archive: Path, sha: str) -> dict:
    asset = {"url": archive.as_uri(), "sha256": sha, "binary": "faketool-1.2.3/faketool"}
    return {
        "version": "1.2.3",
        "version_args": [],
        "version_regex": r"^faketool (\S+)",
        "platforms": {tools.platform_key(): asset},
    }


def test_install_binary_verifies_and_links(tmp_path):
    archive, sha = _fake_tool(tmp_path)
    root = tmp_path / "repo"
    result = tools.install_binary(root, "faketool", _spec(archive, sha))
    assert result.action == "installed"
    assert tools.bin_path(root, "faketool").is_symlink()
    again = tools.install_binary(root, "faketool", _spec(archive, sha))
    assert again.action == "kept"


def test_install_binary_rejects_checksum_mismatch(tmp_path):
    archive, _ = _fake_tool(tmp_path)
    root = tmp_path / "repo"
    with pytest.raises(tools.ToolchainError, match="sha256 mismatch"):
        tools.install_binary(root, "faketool", _spec(archive, "0" * 64))
    assert not tools.bin_path(root, "faketool").exists()
