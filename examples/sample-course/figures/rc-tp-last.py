"""RC low-pass loaded with R_L across C (ex-rc-tp-belastet)."""

from studykit.figures import circuit

ALT = (
    "Schaltbild eines belasteten RC-Tiefpasses: R = 10 kΩ im Längszweig, C = 10 nF im "
    "Querzweig und parallel dazu der Lastwiderstand RL = 10 kΩ. Zählpfeile: "
    "Eingangsspannung Ue an den Eingangsklemmen und Ausgangsspannung Ua an RL, jeweils von "
    "oben nach unten."
)


def build():
    h = 2.5
    with circuit.drawing(alt=ALT) as c:
        c.resistor("R", "10 kΩ", nodes=("e", "a"), loc="top").at((0, h)).right(3)
        c.capacitor("C", "10 nF", nodes=("a", "0"), loc="left").at((3, h)).down(h)
        c.wire((3, h), (6, h))
        rl = c.resistor(r"R_\mathrm{L}", "10 kΩ", nodes=("a", "0"), loc="left")
        rl.at((6, h)).down(h)
        c.wire((6, 0), (0, 0))
        c.dot((3, h))
        c.dot((3, 0))
        c.terminal((0, h))
        c.terminal((0, 0))
        circuit.zaehlpfeil_u(
            ((0, h), (0, 0)), r"\underline{U}_\mathrm{e}", side="left", nodes=("e", "0")
        )
        circuit.zaehlpfeil_u(rl, r"\underline{U}_\mathrm{a}", side="right")
    return c.figure
