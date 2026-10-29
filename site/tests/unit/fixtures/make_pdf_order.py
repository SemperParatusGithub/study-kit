"""Write pdf-order.json: studykit.validate.pdf_order for many ids, the parity fixture of
site/src/lib/shuffle.ts (the website must show MC options in the same order as mc.pdf).

Regenerate from the repository root:
    uv run --frozen python site/tests/unit/fixtures/make_pdf_order.py
"""

from __future__ import annotations

import json
from pathlib import Path

from studykit.validate import _fnv1a, _mulberry32, pdf_order

HERE = Path(__file__).resolve().parent
N = (2, 3, 4, 5, 6)


def ids() -> list[str]:
    out: list[str] = []
    topics = ["rc-filter", "rc-tiefpass", "spannungsteiler", "gleichstrom", "wechselstrom", "x"]
    for topic in topics:
        for num in range(1, 21):
            out.append(f"mc-{topic}-{num:03d}")
    out += [f"pk{e}-mc-{n:02d}" for e in range(1, 4) for n in range(1, 13)]
    # Not valid ids, but the hash must agree on any UTF-8 input.
    out += ["", "a", "mc-ä-001", "Übung–7", "µ∑€😀", "mc-rc-filter-003 "]
    return out


def main() -> None:
    # orders[id] lists the order as a digit string for n = 2…6, each without and with pin-last.
    orders = {
        qid: ["".join(map(str, pdf_order(qid, n, pin))) for n in N for pin in (False, True)]
        for qid in ids()
    }
    rand = _mulberry32(_fnv1a("mc-rc-tiefpass-001"))
    data = {
        "fnv1a": {qid: _fnv1a(qid) for qid in ids()[:50] + ids()[-6:]},
        "mulberry32": {"seed_id": "mc-rc-tiefpass-001", "values": [rand() for _ in range(20)]},
        "n": list(N),
        "orders": orders,
    }
    text = json.dumps(data, ensure_ascii=False, indent=0, separators=(",", ":"))
    (HERE / "pdf-order.json").write_text(text + "\n", "utf-8")


if __name__ == "__main__":
    main()
