"""Step response of the integrator R = 22 kΩ, C = 100 nF to U_e = 0.5 V until -12 V saturation."""

import numpy as np

from studykit.figures import plot

R, C, UE, USAT = 22e3, 100e-9, 0.5, 12.0
T_SAT = USAT * R * C / UE  # 52.8 ms

ALT = (
    "Zeitverlauf am Integrierer mit R = 22 kΩ und C = 100 nF von 0 bis 80 ms. Die "
    "Eingangsspannung U_e springt bei t = 0 auf 0.5 V und bleibt dort. Die Ausgangsspannung "
    "U_a fällt ab t = 0 linear mit -227.3 V/s, erreicht nach 52.8 ms die Sättigung bei "
    "-12 V und bleibt danach konstant."
)


def build():
    t = np.linspace(-5e-3, 80e-3, 1701)
    ue = np.where(t >= 0, UE, 0.0)
    ua = np.clip(-UE / (R * C) * np.maximum(t, 0.0), -USAT, USAT)
    return plot.signals(t, {"U_e": ue, "U_a": ua}, y_label="U", y_unit="V", alt=ALT)
