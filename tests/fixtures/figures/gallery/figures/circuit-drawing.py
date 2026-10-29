from studykit.figures import circuit


def build():
    with circuit.drawing(alt="Reihenschaltung aus R und C an einer Gleichspannung") as c:
        src = c.source_v("U_0", "5 V", nodes=("1", "0")).at((0, 5)).down(5)
        c.wire((0, 5), (3, 5))
        r = c.resistor("R_1", "4.7 kΩ", nodes=("1", "2"), loc="left").at((3, 5)).down()
        cap = c.capacitor("C", "10 nF", nodes=("2", "0"), loc="left").down()
        c.wire((3, 0), (0, 0))
        circuit.zaehlpfeil_u(src, "U_0", side="left")
        circuit.zaehlpfeil_u(r, "U_R")
        circuit.zaehlpfeil_u(cap, "U_C", reverse=True)
        circuit.zaehlpfeil_i(r, "I")
    return c.figure
