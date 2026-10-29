from studykit.figures import plot


def build():
    return plot.bode("10/(s*(s + 1)*(s + 10))", asymptotes=True, margins=True)
