"""Inverting summing amplifier with three inputs (verstaerker-grundschaltungen)."""

from studykit.figures import circuit

ALT = (
    "Schaltbild des Summierers: Drei Eingangsspannungen U1, U2 und U3 liegen über R1, R2 und "
    "R3 am gemeinsamen Knoten des invertierenden Eingangs (virtuelle Masse). RF führt vom "
    "Ausgang auf diesen Knoten zurück, der nichtinvertierende Eingang liegt auf Masse. "
    "Die Eingangsspannungen stehen an den Eingangsklemmen und zählen gegen Masse; "
    "Zählpfeil Ua vom Ausgang gegen Masse."
)


def build():
    with circuit.drawing(alt=ALT) as c:
        op = circuit.Opamp().anchor("minus").at((7.0, 4.0))
        minus, plus, out = op.minus, op.plus, op.out
        x_n = minus.x - 1.0
        ys = [minus.y + 2.0, minus.y, minus.y - 2.0]
        y_rail = -1.6
        for i, y in enumerate(ys, start=1):
            c.resistor(f"R_{i}", nodes=(f"e{i}", "n"), loc="top").at((1.2, y)).right(x_n - 1.2)
            c.wire((0, y), (1.2, y))
            c.terminal((0, y))
        c.wire((x_n, ys[0]), (x_n, ys[2]))
        c.wire((x_n, minus.y), minus)
        c.dot((x_n, minus.y))
        y_fb = op.top.y + 1.6
        c.wire((x_n, ys[0]), (x_n, y_fb))
        x_o = out.x + 0.8
        c.resistor("R_F", nodes=("n", "a"), loc="top").at((x_n, y_fb)).right(x_o - x_n)
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
        c.terminal((0, y_rail))
        c.terminal((x_t, out.y))
        c.terminal((x_t, y_rail))
        circuit.zaehlpfeil_u(((x_t, out.y), (x_t, y_rail)), "U_a", side="right", nodes=("a", "0"))
        c.text((-0.15, ys[0] + 0.4), "$U_1$", halign="left")
        c.text((-0.15, ys[1] + 0.4), "$U_2$", halign="left")
        c.text((-0.15, ys[2] + 0.4), "$U_3$", halign="left")
    return c.figure
