"""Current divider: a current source feeding R1 and R2 in parallel (summary, exercise)."""

from studykit.figures import circuit

ALT = (
    "Schaltbild eines Stromteilers: Die Stromquelle I0 speist die Parallelschaltung aus R1 "
    "und R2. Zählpfeile: Quellstrom I0 nach oben, Teilströme I1 durch R1 und I2 durch R2 "
    "jeweils von oben nach unten, Spannung U über der Parallelschaltung."
)


def build():
    h = 5.0
    with circuit.drawing(alt=ALT) as c:
        src = c.source_i("I_0", nodes=("0", "1")).at((0, 0)).up(h)
        c.wire((0, h), (6, h))
        r1 = c.resistor("R_1", nodes=("1", "0"), loc="left").at((3, h)).down(h)
        r2 = c.resistor("R_2", nodes=("1", "0"), loc="left").at((6, h)).down(h)
        c.wire((6, 0), (0, 0))
        c.dot((3, h))
        c.dot((3, 0))
        circuit.zaehlpfeil_i(src, "I_0", end="end", side="left")
        circuit.zaehlpfeil_i(r1, "I_1", side="right")
        circuit.zaehlpfeil_i(r2, "I_2", side="right")
        circuit.zaehlpfeil_u(r2, "U", side="right")
    return c.figure
