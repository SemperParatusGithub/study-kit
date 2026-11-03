"""Inverting amplifier driven by a source with internal resistance Ri (verstaerker-grundschaltungen)."""

from studykit.figures import circuit

ALT = (
    "Schaltbild: Eine Quelle mit Leerlaufspannung U0 und Innenwiderstand Ri ist an die "
    "Eingangsklemme eines invertierenden Verstärkers angeschlossen. Ri und R1 liegen damit in "
    "Reihe vor dem invertierenden Eingang; R2 führt vom Ausgang auf den invertierenden Eingang "
    "zurück, der nichtinvertierende Eingang liegt auf Masse. Zählpfeile: U0 an der Quelle, Ue "
    "an der Eingangsklemme und Ua am Ausgang, jeweils gegen Masse."
)


def build():
    with circuit.drawing(alt=ALT, size="full") as c:
        op = circuit.Opamp().anchor("minus").at((9.0, 3.6))
        minus, plus, out = op.minus, op.plus, op.out
        y = minus.y
        y_rail = op.bottom.y - 0.8
        src = c.source_v("U_0", nodes=("q", "0")).at((0, y)).down(y - y_rail)
        c.resistor("R_i", nodes=("q", "e"), loc="top").at((0, y)).right(3.0)
        c.wire((3.0, y), (4.0, y))
        c.dot((4.0, y))
        x_n = minus.x - 1.0
        c.resistor("R_1", nodes=("e", "n"), loc="top").at((4.0, y)).right(x_n - 0.5 - 4.0)
        c.wire((x_n - 0.5, y), minus)
        c.dot((x_n, y))
        y_fb = op.top.y + 1.2
        x_o = out.x + 0.8
        c.wire((x_n, y), (x_n, y_fb))
        c.resistor("R_2", nodes=("n", "a"), loc="top").at((x_n, y_fb)).right(x_o - x_n)
        c.wire((x_o, y_fb), (x_o, out.y))
        c.dot((x_o, out.y))
        x_t = x_o + 1.5
        c.wire(out, (x_t, out.y))
        x_g = plus.x - 0.5
        c.wire(plus, (x_g, plus.y))
        c.wire((x_g, plus.y), (x_g, y_rail))
        c.dot((x_g, y_rail))
        c.ground((x_g, y_rail))
        c.wire((0, y_rail), (x_t, y_rail))
        c.dot((4.0, y_rail))
        c.terminal((x_t, out.y))
        c.terminal((x_t, y_rail))
        circuit.zaehlpfeil_u(src, "U_0", side="left")
        circuit.zaehlpfeil_u(((4.0, y), (4.0, y_rail)), "U_e", side="right", nodes=("e", "0"))
        circuit.zaehlpfeil_u(((x_t, out.y), (x_t, y_rail)), "U_a", side="right", nodes=("a", "0"))
    return c.figure
