from studykit.figures import plot


def build():
    return plot.root_locus("1/(s*(s + 2)*(s + 4))")
