from studykit.figures import plot


def build():
    return plot.pole_zero("(s + 2)/((s + 1)*(s**2 + 2*s + 5))")
