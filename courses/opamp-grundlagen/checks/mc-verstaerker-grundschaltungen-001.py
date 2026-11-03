from studykit.check import mc_numeric

R1, R2 = 4.7e3, 22e3
mc_numeric(
    correct=-R2 / R1,
    options={"A": 4.681, "B": -0.2136, "C": -4.681, "D": 5.681},
    mistakes={"A": R2 / R1, "B": -R1 / R2, "D": 1 + R2 / R1},
    method="V = -R2/R1; sign lost, ratio inverted, non-inverting formula",
)
