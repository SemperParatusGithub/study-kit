"""Pinned external toolchain: install pandoc/typst into .tools/bin and check versions.

`toolchain.toml` is the single source of truth. Archives are downloaded with curl,
verified by sha256 and unpacked under `.tools/<name>-<version>/`; `.tools/bin/<name>`
is a symlink to the unpacked binary.
"""

from __future__ import annotations

import hashlib
import os
import platform
import re
import shutil
import subprocess
import tarfile
import tomllib
import zipfile
from dataclasses import dataclass
from pathlib import Path


class ToolchainError(RuntimeError):
    pass


def repo_root() -> Path:
    """The repository root: the nearest ancestor of this file that has toolchain.toml."""
    env = os.environ.get("STUDYKIT_ROOT")
    if env:
        return Path(env).resolve()
    for parent in Path(__file__).resolve().parents:
        if (parent / "toolchain.toml").is_file():
            return parent
    raise ToolchainError("cannot find toolchain.toml above the studykit package")


def load_toolchain(root: Path) -> dict:
    with (root / "toolchain.toml").open("rb") as fh:
        return tomllib.load(fh)


def platform_key() -> str:
    system, machine = platform.system(), platform.machine().lower()
    if system == "Darwin" and machine in {"arm64", "aarch64"}:
        return "macos-arm64"
    if system == "Linux" and machine in {"x86_64", "amd64"}:
        return "linux-x86_64"
    raise ToolchainError(f"unsupported platform: {system} {machine}")


def parse_version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", text)[:3])


def tool_version(executable: str | Path, args: list[str], regex: str) -> str | None:
    """Run `<executable> <args>` and extract the version, or None if it cannot run."""
    try:
        proc = subprocess.run(
            [str(executable), *args], capture_output=True, text=True, timeout=30, check=False
        )
    except OSError, subprocess.TimeoutExpired:
        return None
    output = (proc.stdout or proc.stderr).strip()
    match = re.search(regex, output, re.MULTILINE)
    return match.group(1) if match else None


def tools_dir(root: Path) -> Path:
    return root / ".tools"


def bin_path(root: Path, name: str) -> Path:
    return tools_dir(root) / "bin" / name


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_suffix(dest.suffix + ".part")
    subprocess.run(
        ["curl", "-fsSL", "--retry", "3", "-o", str(partial), url], check=True, timeout=600
    )
    partial.replace(dest)


def _extract(archive: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    if archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(dest)
            # zipfile drops permission bits; restore them from the archive metadata.
            for info in zf.infolist():
                mode = info.external_attr >> 16
                if mode:
                    (dest / info.filename).chmod(mode & 0o777)
    else:
        with tarfile.open(archive) as tf:
            tf.extractall(dest, filter="data")


@dataclass
class InstallResult:
    name: str
    version: str
    action: str  # "kept" | "installed"
    path: Path


def install_binary(root: Path, name: str, spec: dict, force: bool = False) -> InstallResult:
    version = spec["version"]
    target = bin_path(root, name)
    current = tool_version(target, spec["version_args"], spec["version_regex"])
    if current == version and not force:
        return InstallResult(name, version, "kept", target)

    platforms = spec["platforms"]
    key = platform_key()
    if key not in platforms:
        raise ToolchainError(f"{name}: no pinned asset for platform {key}")
    asset = platforms[key]

    archive = root / ".cache" / "downloads" / asset["url"].rsplit("/", 1)[-1]
    if not archive.is_file() or sha256_file(archive) != asset["sha256"]:
        _download(asset["url"], archive)
    actual = sha256_file(archive)
    if actual != asset["sha256"]:
        archive.unlink(missing_ok=True)
        raise ToolchainError(
            f"{name}: sha256 mismatch for {asset['url']}\n"
            f"  expected {asset['sha256']}\n  got      {actual}"
        )

    unpacked = tools_dir(root) / f"{name}-{version}"
    _extract(archive, unpacked)
    binary = unpacked / asset["binary"]
    if not binary.is_file():
        raise ToolchainError(f"{name}: {asset['binary']} not found in {archive.name}")
    binary.chmod(binary.stat().st_mode | 0o111)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.unlink(missing_ok=True)
    target.symlink_to(binary.relative_to(target.parent, walk_up=True))

    installed = tool_version(target, spec["version_args"], spec["version_regex"])
    if installed != version:
        raise ToolchainError(f"{name}: installed binary reports {installed!r}, want {version}")
    return InstallResult(name, version, "installed", target)


def install_all(root: Path, force: bool = False) -> list[InstallResult]:
    toolchain = load_toolchain(root)
    return [
        install_binary(root, name, spec, force=force)
        for name, spec in toolchain.get("binaries", {}).items()
    ]
