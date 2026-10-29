from studykit.figures import plot


def build():
    # A reference at an angle other than 0 degrees: it runs beside U_R, so the names of I,
    # U_R and the phase angle have to find room around the shared axis.
    return plot.phasor({"U_R": (6, 30), "U_L": (8, 120)}, chain=True, reference={"I": (2, 30)})
