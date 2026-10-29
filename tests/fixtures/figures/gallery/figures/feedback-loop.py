from studykit.figures import block


def build():
    return block.feedback_loop(forward=("G_R(s)", "G_S(s)"), feedback="H(s)", disturbance="Z(s)")
