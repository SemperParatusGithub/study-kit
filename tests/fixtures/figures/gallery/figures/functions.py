from studykit.figures import plot


def build():
    return plot.functions(
        [("f", "x**2 - 2"), ("g", "exp(-x)")],
        x=(-3, 3),
        mark=("roots", "intersections", "extrema"),
    )
