"""Findings: the one error format of every check (docs/architecture.md §4.3).

A finding prints as `path:line:col SK-CODE message (fix: …)`. Warnings and notes keep
that shape and put `warning:` or `info:` in front of the message. Every code is listed in
docs/content-format/errors.md.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Literal

Severity = Literal["error", "warning", "info"]

# `path:line:col SK-CODE message (fix: …)`, also when embedded in other output such as a
# pandoc filter error.
FINDING_RE = re.compile(
    r"^(?P<path>[^\s:][^:]*):(?P<line>\d+):(?P<col>\d+) (?P<code>SK-[A-Z0-9-]+) "
    r"(?:(?P<severity>warning|info): )?(?P<message>.*?)(?: \(fix: (?P<fix>.*)\))?$",
    re.MULTILINE,
)


@dataclass(frozen=True, order=True)
class Finding:
    path: str
    line: int
    col: int
    code: str
    message: str
    fix: str = ""
    severity: Severity = "error"

    def format(self) -> str:
        prefix = "" if self.severity == "error" else f"{self.severity}: "
        fix = f" (fix: {self.fix})" if self.fix else ""
        return f"{self.path}:{self.line}:{self.col} {self.code} {prefix}{self.message}{fix}"

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def is_error(self) -> bool:
        return self.severity == "error"


def parse(text: str) -> list[Finding]:
    """Findings embedded in tool output (for example a Lua filter error)."""
    return [
        Finding(
            path=m["path"],
            line=int(m["line"]),
            col=int(m["col"]),
            code=m["code"],
            message=m["message"],
            fix=m["fix"] or "",
            severity=m["severity"] or "error",  # type: ignore[arg-type]
        )
        for m in FINDING_RE.finditer(text)
    ]


def dumps(findings: list[Finding]) -> str:
    return json.dumps([f.to_dict() for f in findings], ensure_ascii=False, indent=2)
