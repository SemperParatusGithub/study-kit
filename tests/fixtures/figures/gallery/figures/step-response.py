from studykit.figures import plot


def build():
    return plot.step_response("25/(s**2 + 4*s + 25)")
