from studykit.check import mc_numeric

RF, R1, R2, U1, U2 = 20e3, 10e3, 40e3, 0.5, 1.2
mc_numeric(
    correct=-RF * (U1 / R1 + U2 / R2),
    options={"A": -1.7, "B": -1.6, "C": 1.6, "D": -2.65},
    mistakes={"A": -(U1 + U2), "C": RF * (U1 / R1 + U2 / R2), "D": -(R1 / RF * U1 + R2 / RF * U2)},
    method="Ua = -RF sum Ui/Ri",
)
