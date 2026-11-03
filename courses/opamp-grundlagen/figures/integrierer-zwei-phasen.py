"""Piecewise constant input of the integrator exercise: 0.6 V for 0..8 ms, then -0.25 V."""

import numpy as np

from studykit.figures import plot

ALT = (
    "Zeitverlauf der Eingangsspannung U_e von -2 bis 25 ms: vor t = 0 ist U_e = 0, von "
    "t = 0 bis t = 8 ms beträgt sie 0.6 V, ab t = 8 ms -0.25 V."
)


def build():
    t = np.linspace(-2e-3, 25e-3, 2701)
    ue = np.where(t < 0, 0.0, np.where(t < 8e-3, 0.6, -0.25))
    return plot.signals(t, {"U_e": ue}, y_unit="V", alt=ALT)
