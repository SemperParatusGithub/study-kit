from studykit.figures import plot


def build():
    # Series RL circuit: the current is the reference phasor, drawn to its own scale.
    return plot.phasor({"U_R": (60, 0), "U_L": (80, 90)}, chain=True, reference={"I": (2, 0)})
