"""The check-script API: what a verifier's `checks/<id>.py` calls (docs/architecture.md §2.10).

A check script computes an item's results from its blind view (`studykit blind`) and ends
with exactly one of these calls, which prints one JSON line that `studykit verify` reads:

    from studykit.check import answers
    R, C = 2.2e3, 47e-9
    tau = R * C
    answers(tau=tau * 1e6, fg=1 / (2 * pi * tau), method="tau = RC, fg = 1/(2 pi tau)")

- `answers(**values)`: an exercise or exam task; one value per answer key of the blind
  view, as a number in the unit the blind view names, as `quantity(x, "kHz")` in another
  unit of the same kind, or as a SymPy expression (or string) for a symbolic answer.
- `mc_answer(answer)`: an MC question answered blind; the letters of the correct options
  (single, multi) or the true statements (Kprim; a mapping letter -> bool works too).
- `mc_numeric(correct=…, options=…, mistakes=…)`: a numeric MC question; `studykit
  verify` checks that exactly the marked options match `correct`, that each distractor
  reproduces its named mistake and is well separated, and that each option's text reads
  as its stated value.
- `review(agree, reason)`: an item without answer keys (a derivation, a concept), checked
  by reading its solution against an independent working.

A `checks/<id>.json` file holds the same object directly, e.g.
`{"answer": ["A", "C"], "confidence": "high", "ambiguous": false, "reason": "…"}`.
"""

from __future__ import annotations

import json
import math
import sys
from collections.abc import Iterable, Mapping
from typing import Any

PROTOCOL = 1
MARK = "studykit-check"


def quantity(value: Any, unit: str) -> dict[str, Any]:
    """A value in a unit other than the blind view's (`quantity(1.54, "kHz")` for Hz)."""
    return {"value": _number(value), "unit": unit}


def _number(value: Any) -> float:
    if isinstance(value, bool):
        raise TypeError("a boolean is not a number")
    try:
        number = complex(value)
    except TypeError as exc:
        raise TypeError(f"not a number: {value!r}") from exc
    if abs(number.imag) > 1e-12 * max(1.0, abs(number.real)):
        raise TypeError(
            f"complex value {value!r}: give the magnitude, angle, real or imaginary part the "
            "answer key asks for"
        )
    if not math.isfinite(number.real):
        raise TypeError(f"not a finite number: {value!r}")
    return number.real


def _value(value: Any) -> Any:
    """JSON for one computed answer: a float, a {value, unit} mapping or an expression."""
    if isinstance(value, Mapping) and "value" in value:
        return {"value": _number(value["value"]), "unit": str(value.get("unit") or "")}
    if isinstance(value, str):
        return value
    free = getattr(value, "free_symbols", None)
    if free:  # a SymPy expression with symbols: a symbolic answer
        from studykit.calc import show

        return show(value)
    return _number(value)


def emit(payload: Mapping[str, Any]) -> None:
    """Print the result line `studykit verify` reads (the last JSON line of stdout)."""
    line = json.dumps({MARK: PROTOCOL, **payload}, ensure_ascii=False, allow_nan=False)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def answers(*, method: str | None = None, **values: Any) -> None:
    """Computed values of an exercise or exam task, one per answer key."""
    if not values:
        raise ValueError("answers() needs one value per answer key of the blind view")
    payload: dict[str, Any] = {
        "kind": "answers",
        "answers": {k: _value(v) for k, v in values.items()},
    }
    if method:
        payload["method"] = method
    emit(payload)


def _letters(answer: Iterable[str] | Mapping[str, bool] | str) -> Any:
    if isinstance(answer, str):
        return [answer.strip().upper()]
    if isinstance(answer, Mapping):
        return {str(k).upper(): bool(v) for k, v in answer.items()}
    return [str(a).strip().upper() for a in answer]


def mc_answer(
    answer: Iterable[str] | Mapping[str, bool] | str,
    *,
    confidence: str = "high",
    ambiguous: bool = False,
    reason: str = "",
    method: str | None = None,
) -> None:
    """A blind answer to an MC question, by the letters of the blind view (source order)."""
    payload: dict[str, Any] = {
        "kind": "mc",
        "answer": _letters(answer),
        "confidence": confidence,
        "ambiguous": bool(ambiguous),
        "reason": reason,
    }
    if method:
        payload["method"] = method
    emit(payload)


def mc_numeric(
    *,
    correct: Any,
    options: Mapping[str, Any],
    mistakes: Mapping[str, Any] | None = None,
    rtol: float = 5e-3,
    min_separation: float = 0.05,
    method: str | None = None,
) -> None:
    """A numeric MC question: the correct value, each option's stated value (SI units, in
    source order A, B, …) and, for each distractor, the value its named mistake gives."""
    payload: dict[str, Any] = {
        "kind": "mc-numeric",
        "correct": _number(correct),
        "options": {str(k).upper(): _number(v) for k, v in options.items()},
        "mistakes": {str(k).upper(): _number(v) for k, v in (mistakes or {}).items()},
        "rtol": float(rtol),
        "min_separation": float(min_separation),
    }
    if method:
        payload["method"] = method
    emit(payload)


def review(agree: bool, reason: str, *, method: str | None = None) -> None:
    """An item without answer keys: does the item's solution hold up?"""
    payload: dict[str, Any] = {"kind": "review", "agree": bool(agree), "reason": reason}
    if method:
        payload["method"] = method
    emit(payload)
