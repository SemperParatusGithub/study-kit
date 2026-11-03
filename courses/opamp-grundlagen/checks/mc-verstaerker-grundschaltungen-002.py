from studykit.check import mc_numeric

R1, R2 = 1.5e3, 6.8e3
mc_numeric(
    correct=1 + R2 / R1,
    options={"A": 4.533, "B": -4.533, "C": 0.1807, "D": 5.533},
    mistakes={"A": R2 / R1, "B": -R2 / R1, "C": R1 / (R1 + R2)},
    method="V = 1 + R2/R1; R2/R1 alone, inverting formula, k instead of 1/k",
)
