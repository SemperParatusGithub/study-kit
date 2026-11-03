"""Voltage follower between a source with internal resistance and a load (verstaerker-grundschaltungen)."""

from studykit.figures import circuit

ALT = (
    "Schaltbild: Eine Quelle mit Leerlaufspannung U0 und Innenwiderstand Ri speist den "
    "nichtinvertierenden Eingang eines Spannungsfolgers. Der Ausgang ist direkt mit dem "
    "invertierenden Eingang verbunden und speist den Lastwiderstand RL nach Masse. "
    "Zählpfeile: U0 an der Quelle und die Lastspannung UL über RL."
)


def build():
    with circuit.drawing(alt=ALT) as c:
        op = circuit.Opamp(plus_top=True).anchor("plus").at((5.0, 4.2))
        plus, minus, out = op.plus, op.minus, op.out
        src = c.source_v("U_0", nodes=("q", "0")).at((0, plus.y)).down(plus.y)
        c.resistor("R_i", nodes=("q", "p"), loc="top").at((0, plus.y)).right(plus.x)
        x_fb = minus.x - 0.6
        y_fb = op.bottom.y - 0.7
        x_o = out.x + 0.8
        c.wire(minus, (x_fb, minus.y))
        c.wire((x_fb, minus.y), (x_fb, y_fb))
        c.wire((x_fb, y_fb), (x_o, y_fb))
        c.wire(out, (x_o + 1.5, out.y))
        c.wire((x_o, out.y), (x_o, y_fb))
        c.dot((x_o, out.y))
        x_l = x_o + 1.5
        rl = c.resistor("R_L", nodes=("a", "0"), loc="left").at((x_l, out.y)).down(out.y)
        c.wire((0, 0), (x_l, 0))
        c.dot((x_fb + 0.9, 0))
        c.ground((x_fb + 0.9, 0))
        circuit.zaehlpfeil_u(src, "U_0", side="left")
        circuit.zaehlpfeil_u(rl, "U_L", side="right")
    return c.figure
