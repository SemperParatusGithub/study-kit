"""Equivalent voltage source (U_q, R_i) with a load R_L at the terminals A, B (summary)."""

from studykit.figures import circuit

ALT = (
    "Schaltbild der Ersatzspannungsquelle: Die ideale Spannungsquelle Uq liegt in Reihe mit "
    "dem Innenwiderstand Ri zwischen den Klemmen A und B. An den Klemmen hängt der "
    "Lastwiderstand RL. Zählpfeile: Uq an der Quelle, Lastspannung UL an der Last und "
    "Laststrom IL von A zur Last."
)


def build():
    h = 2.5
    with circuit.drawing(alt=ALT) as c:
        src = c.source_v("U_q", nodes=("q", "B")).at((0, h)).down(h)
        c.resistor(r"R_\mathrm{i}", nodes=("q", "A"), loc="top").at((0, h)).right(3)
        top = c.wire((3, h), (5.5, h), nodes=("A", "A"))
        rl = c.resistor(r"R_\mathrm{L}", nodes=("A", "B"), loc="left").at((5.5, h)).down(h)
        c.wire((5.5, 0), (0, 0))
        c.terminal((3, h))
        c.terminal((3, 0))
        c.text((3, h + 0.35), "$A$")
        c.text((3, -0.4), "$B$")
        circuit.zaehlpfeil_u(src, r"U_\mathrm{q}", side="left")
        circuit.zaehlpfeil_i(top, r"I_\mathrm{L}", side="top", nodes=("A", "B"))
        circuit.zaehlpfeil_u(rl, r"U_\mathrm{L}", side="right")
    return c.figure
