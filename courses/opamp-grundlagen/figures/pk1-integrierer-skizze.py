"""Solution sketch of pk1-t3: integrator R = 39 kΩ, C = 330 nF, U_e = 0.6 V from t = 0, U_sat = 11 V."""

import numpy as np

from studykit.figures import plot

R, C, UE, USAT = 39e3, 330e-9, 0.6, 11.0
T_SAT = USAT * R * C / abs(UE)  # 235.95 ms

ALT = (
    "Skizze zur Lösung: Die Eingangsspannung U_e springt bei t = 0 auf 0.6 V und bleibt "
    "dort. Die Ausgangsspannung U_a fällt ab t = 0 linear mit -46.62 V/s, erreicht bei "
    "t = 235.95 ms die negative Sättigung -11 V und bleibt bis 300 ms dort."
)


def build():
    t = np.linspace(-10e-3, 300e-3, 3101)
    ue = np.where(t >= 0, UE, 0.0)
    ua = np.clip(-UE / (R * C) * np.maximum(t, 0.0), -USAT, USAT)
    # the axis in ms: plot.signals switches to seconds from 200 ms on
    return plot.signals(
        t * 1e3, {"U_e": ue, "U_a": ua}, unit="ms", y_label="U", y_unit="V", alt=ALT
    )
