from math import pi, sqrt

from studykit.check import mc_numeric

R, C, U, f = 10e3, 1e-6, 1.0, 50.0
w = 2 * pi * f
a = U / (w * R * C)
mc_numeric(
    correct=a,
    options={"A": 0.3183, "B": 3.142, "C": 0.2251, "D": 2.000},
    mistakes={"B": U * w * R * C, "C": a / sqrt(2), "D": U / (f * R * C)},
    method="amplitude U/(w R C); multiplied, RMS, forgotten 2 pi",
)
