from math import pi

from studykit.check import mc_numeric

R, C, Ue = 10e3, 47e-9, 0.2
s = -Ue / (R * C)  # V/s
mc_numeric(
    correct=s,
    options={"A": 425.5, "B": -42.55, "C": -425.5, "D": -2674.0},
    mistakes={"A": -s, "B": s / 10, "D": 2 * pi * s},
    method="dUa/dt = -Ue/(R C); sign, power of ten, extra 2 pi",
)
