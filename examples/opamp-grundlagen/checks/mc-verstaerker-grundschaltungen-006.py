from studykit.check import mc_numeric

R1, R2, Usat, Ue = 2e3, 18e3, 12.0, 1.5
lin = -R2 / R1 * Ue
mc_numeric(
    correct=max(-Usat, min(Usat, lin)),
    options={"A": -13.5, "B": 12.0, "C": -12.0, "D": 0.0},
    mistakes={"A": lin, "B": Usat, "D": 0.0},
    method="-R2/R1 Ue = -13.5 V clipped at -12 V",
)
