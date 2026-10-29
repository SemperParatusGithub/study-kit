import numpy as np

from studykit.figures import plot


def build():
    t = np.linspace(0, 2e-3, 500)
    return plot.signals(
        t,
        {"u_1": np.sin(2 * np.pi * 1e3 * t), "u_2": 0.5 * np.cos(2 * np.pi * 1e3 * t)},
        y_label="u",
        y_unit="V",
    )
