from studykit.check import mc_numeric

R1, R2 = 2e3, 10e3
mc_numeric(
    correct=1 + R2 / R1,
    options={"A": 5.0, "B": -5.0, "C": 0.1667, "D": 6.0},
    mistakes={"A": R2 / R1, "B": -R2 / R1, "C": R1 / (R1 + R2)},
    method="V = 1 + R2/R1",
)
