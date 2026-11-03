from studykit.check import mc_numeric

R1, R2, Usat = 5.6e3, 39e3, 11.0
mc_numeric(
    correct=Usat * R1 / R2,
    options={"A": 1.381, "B": 3.159, "C": 76.61, "D": 1.579},
    mistakes={"A": Usat / (1 + R2 / R1), "B": 2 * Usat * R1 / R2, "C": Usat * R2 / R1},
    method="Ue,max = Usat/|V| with V = -R2/R1",
)
