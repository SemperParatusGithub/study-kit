"""Series RC circuit of the mock exam task pk1-t2: U = 10 V at 1 kHz."""

from studykit.figures import circuit

ALT = (
    "Schaltbild einer RC-Reihenschaltung: Eine Wechselspannungsquelle mit U = 10 V speist "
    "die Reihenschaltung aus R = 1 kΩ und C = 220 nF. Zählpfeile: Strom I im oberen Leiter, "
    "Teilspannungen UR an R und UC an C, Quellenspannung U an der Quelle."
)


def build():
    h = 2.5
    with circuit.drawing(alt=ALT) as c:
        src = c.source_v("U", "10 V", nodes=("1", "0"), ac=True).at((0, h)).down(h)
        top = c.wire((0, h), (1, h), nodes=("1", "1"))
        r = c.resistor("R", "1 kΩ", nodes=("1", "2"), loc="top").at((1, h)).right(3)
        c.wire((4, h), (6.5, h))
        cap = c.capacitor("C", "220 nF", nodes=("2", "0"), loc="left").at((6.5, h)).down(h)
        c.wire((6.5, 0), (0, 0))
        circuit.zaehlpfeil_u(src, r"\underline{U} = 10\,\mathrm{V}", side="left")
        circuit.zaehlpfeil_i(top, r"\underline{I}", side="bottom", nodes=("1", "2"))
        circuit.zaehlpfeil_u(r, r"\underline{U}_R", side="bottom")
        circuit.zaehlpfeil_u(cap, r"\underline{U}_C", side="right")
    return c.figure
