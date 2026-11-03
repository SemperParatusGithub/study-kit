from math import pi, sqrt

from studykit.check import mc_numeric

R, C, f = 10e3, 100e-9, 1e3
x = 2 * pi * f * R * C
mc_numeric(
    correct=1 / x,
    options={"A": 6.283, "B": 0.1592, "C": 1.592, "D": 0.1125},
    mistakes={"A": x, "C": 1 / (2 * pi * 100 * R * C), "D": 1 / x / sqrt(2)},
    method="|H| = 1/(w R C)",
)
