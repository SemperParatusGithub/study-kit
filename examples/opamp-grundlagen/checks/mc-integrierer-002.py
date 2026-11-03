from math import pi

from studykit.check import mc_numeric

R, C = 22e3, 47e-9
f1 = 1 / (2 * pi * R * C)
mc_numeric(
    correct=f1,
    options={"A": 15.39, "B": 153.9, "C": 967.1, "D": 1539.0},
    mistakes={"A": f1 / 10, "C": 1 / (R * C), "D": f1 * 10},
    method="f1 = 1/(2 pi R C); powers of ten, forgotten 2 pi",
)
