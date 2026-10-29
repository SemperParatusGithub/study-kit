"""Network of the mock exam task pk1-t1: divider R1, R2 plus R3 in series to terminal A."""

from studykit.figures import circuit

ALT = (
    "Schaltbild: Die Spannungsquelle U0 = 24 V speist über R1 = 2 kΩ den Querwiderstand "
    "R2 = 6 kΩ. Vom Verbindungspunkt führt R3 = 1 kΩ zur Klemme A; die Klemme B liegt am "
    "unteren Leiter. Die Klemmen sind offen. Zählpfeile: U0 an der Quelle und UAB von A "
    "nach B."
)


def build():
    h = 2.5
    with circuit.drawing(alt=ALT) as c:
        src = c.source_v("U_0", "24 V", nodes=("1", "0")).at((0, h)).down(h)
        c.resistor("R_1", "2 kΩ", nodes=("1", "2"), loc="top").at((0, h)).right(3.5)
        c.resistor("R_2", "6 kΩ", nodes=("2", "0"), loc="left").at((3.5, h)).down(h)
        c.resistor("R_3", "1 kΩ", nodes=("2", "A"), loc="top").at((3.5, h)).right(3.5)
        c.wire((7, 0), (0, 0))
        c.dot((3.5, h))
        c.dot((3.5, 0))
        c.terminal((7, h))
        c.terminal((7, 0))
        c.text((7, h + 0.35), "$A$")
        c.text((7, -0.4), "$B$")
        circuit.zaehlpfeil_u(src, r"U_0 = 24\,\mathrm{V}", side="left")
        circuit.zaehlpfeil_u(((7, h), (7, 0)), r"U_\mathrm{AB}", side="right", nodes=("A", "0"))
    return c.figure
