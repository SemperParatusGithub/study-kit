from studykit.check import mc_numeric

RC, Ue, Usat, UB = 2e-3, 0.5, 10.0, 12.0
mc_numeric(
    correct=Usat * RC / Ue,
    options={"A": 48e-3, "B": 0.1e-3, "C": 80e-3, "D": 40e-3},
    mistakes={"A": UB * RC / Ue, "B": Ue * RC / Usat, "C": 2 * Usat * RC / Ue},
    method="tsat = Usat RC/Ue; supply instead of Usat, inverted ratio, full swing",
)
