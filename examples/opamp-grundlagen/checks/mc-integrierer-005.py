from math import log10

from studykit.check import mc_numeric

mc_numeric(
    correct=20 * log10(1 / 10),
    options={"A": -20.0, "B": -40.0, "C": -10.0, "D": -3.0},
    mistakes={"B": 40 * log10(1 / 10), "C": 10 * log10(1 / 10), "D": -3.0},
    method="|H| = f1/f = 0.1 -> 20 log10; second order, power dB, low-pass corner",
)
