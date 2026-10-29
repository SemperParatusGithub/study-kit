"""Divider seen from the terminals A, B across R2 (ex-st-ersatzquelle)."""

from studykit.figures import circuit

ALT = (
    "Schaltbild: Die Spannungsquelle U0 = 10 V speist über R1 = 6 kΩ den Widerstand "
    "R2 = 4 kΩ. Die Klemmen A und B liegen parallel zu R2 und sind offen. Zählpfeile: U0 an "
    "der Quelle und die Klemmenspannung UAB von A nach B."
)


def build():
    h = 2.5
    with circuit.drawing(alt=ALT) as c:
        src = c.source_v("U_0", "10 V", nodes=("1", "0")).at((0, h)).down(h)
        c.resistor("R_1", "6 kΩ", nodes=("1", "A"), loc="top").at((0, h)).right(3.5)
        c.resistor("R_2", "4 kΩ", nodes=("A", "0"), loc="left").at((3.5, h)).down(h)
        c.wire((3.5, h), (5.5, h))
        c.wire((5.5, 0), (0, 0))
        c.dot((3.5, h))
        c.dot((3.5, 0))
        c.terminal((5.5, h))
        c.terminal((5.5, 0))
        c.text((5.5, h + 0.35), "$A$")
        c.text((5.5, -0.4), "$B$")
        circuit.zaehlpfeil_u(src, r"U_0 = 10\,\mathrm{V}", side="left")
        circuit.zaehlpfeil_u(
            ((5.5, h), (5.5, 0)), r"U_\mathrm{AB}", side="right", nodes=("A", "0")
        )
    return c.figure
