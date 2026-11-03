from studykit.check import mc_numeric

V, R1 = 12.0, 1.8e3
mc_numeric(
    correct=(V - 1) * R1,
    options={"A": 21.6e3, "B": 19.8e3, "C": 23.4e3, "D": 163.6},
    mistakes={"A": V * R1, "C": (V + 1) * R1, "D": R1 / (V - 1)},
    method="R2 = (V - 1) R1",
)
