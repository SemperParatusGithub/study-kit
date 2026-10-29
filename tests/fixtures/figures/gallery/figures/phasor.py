from studykit.figures import plot


def build():
    return plot.phasor({"U_R": (5, 0), "U_L": (3, 90)}, chain=True)
