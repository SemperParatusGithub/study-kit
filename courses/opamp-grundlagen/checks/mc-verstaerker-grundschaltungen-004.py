from studykit.check import mc_numeric

RF, R1, R2, U1, U2 = 10e3, 10e3, 5e3, 0.6, 0.4
mc_numeric(
    correct=-(RF / R1 * U1 + RF / R2 * U2),
    options={"A": -1.0, "B": 1.4, "C": -1.4, "D": -0.8},
    mistakes={"A": -(U1 + U2), "B": RF / R1 * U1 + RF / R2 * U2, "D": -(U1 + R2 / RF * U2)},
    method="Ua = -RF (U1/R1 + U2/R2); weights ignored, sign lost, weight inverted",
)
