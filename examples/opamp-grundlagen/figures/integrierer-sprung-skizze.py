"""Solution sketch: integrator R = 68 kΩ, C = 150 nF, U_e = -0.8 V from t = 0, U_sat = 11 V."""

import numpy as np

from studykit.figures import plot

R, C, UE, USAT = 68e3, 150e-9, -0.8, 11.0
T_SAT = USAT * R * C / abs(UE)  # 140.25 ms

ALT = (
    "Skizze zur Lösung: Die Eingangsspannung U_e springt bei t = 0 auf -0.8 V und bleibt "
    "dort. Die Ausgangsspannung U_a steigt ab t = 0 linear mit 78.43 V/s, erreicht bei "
    "t = 140.25 ms die positive Sättigung +11 V und bleibt bis 200 ms dort."
)


def build():
    t = np.linspace(-10e-3, 200e-3, 2101)
    ue = np.where(t >= 0, UE, 0.0)
    ua = np.clip(-UE / (R * C) * np.maximum(t, 0.0), -USAT, USAT)
    # the axis in ms: plot.signals switches to seconds from 200 ms on
    return plot.signals(
        t * 1e3, {"U_e": ue, "U_a": ua}, unit="ms", y_label="U", y_unit="V", alt=ALT
    )
