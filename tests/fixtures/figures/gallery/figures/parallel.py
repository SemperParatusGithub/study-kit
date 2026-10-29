from studykit.figures import block


def build():
    return block.parallel(["G_1(s)", "G_2(s)"], signs="+-")
