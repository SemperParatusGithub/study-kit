"""Magnitude response of the RC low-pass used in the summary and the exercise."""

import numpy as np

from studykit.figures import plot


def build():
    r, c = 1e3, 100e-9
    fg = 1 / (2 * np.pi * r * c)
    f = np.logspace(1, 6, 400)
    magnitude_db = 20 * np.log10(1 / np.sqrt(1 + (f / fg) ** 2))
    alt = "Betrag des RC-Tiefpasses in dB über der Frequenz; -3 dB bei f_g = 1,59 kHz."
    with plot.custom(alt=alt) as c_:
        c_.ax.semilogx(f, magnitude_db)
        c_.ax.axvline(fg, linestyle="--")
        c_.facts["fg_hz"] = float(fg)
    return c_.figure
