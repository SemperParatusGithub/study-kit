"""Series RL circuit on the mains, U = 230 V at 50 Hz (ex-ws-rl-reihe)."""

from studykit.figures import circuit

ALT = (
    "Schaltbild einer RL-Reihenschaltung: Eine Wechselspannungsquelle mit U = 230 V speist "
    "die Reihenschaltung aus R = 40 Ω und L = 100 mH. Zählpfeile: Strom I im oberen Leiter, "
    "Teilspannungen UR an R und UL an L, Quellenspannung U an der Quelle."
)


def build():
    h = 2.5
    with circuit.drawing(alt=ALT) as c:
        src = c.source_v("U", "230 V", nodes=("1", "0"), ac=True).at((0, h)).down(h)
        top = c.wire((0, h), (1, h), nodes=("1", "1"))
        r = c.resistor("R", "40 Ω", nodes=("1", "2"), loc="top").at((1, h)).right(3)
        c.wire((4, h), (6.5, h))
        ind = c.inductor("L", "100 mH", nodes=("2", "0"), loc="left").at((6.5, h)).down(h)
        c.wire((6.5, 0), (0, 0))
        circuit.zaehlpfeil_u(src, r"\underline{U} = 230\,\mathrm{V}", side="left")
        circuit.zaehlpfeil_i(top, r"\underline{I}", side="bottom", nodes=("1", "2"))
        circuit.zaehlpfeil_u(r, r"\underline{U}_R", side="bottom")
        circuit.zaehlpfeil_u(ind, r"\underline{U}_L", side="right")
    return c.figure
