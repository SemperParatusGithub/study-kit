from studykit.figures import circuit


def build():
    return circuit.rlc("series", "10 Ω", "10 mH", "1 µF", U0="230 V")
