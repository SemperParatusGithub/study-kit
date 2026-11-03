from studykit.check import mc_numeric

R1, R2, Ri = 10e3, 56e3, 2.5e3
mc_numeric(
    correct=-R2 / (R1 + Ri),
    options={"A": -5.6, "B": -4.48, "C": -5.85, "D": -7.467},
    mistakes={"A": -R2 / R1, "C": -(R2 + Ri) / R1, "D": -R2 / (R1 - Ri)},
    method="Ri in series with R1: -R2/(R1 + Ri)",
)
