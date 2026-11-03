# Inverting, R1 = 10k, R2 = 100k, Usat = 12 V, Ue = 1.5 V: output saturates, Un = divider.
from studykit.check import mc_numeric

R1, R2, Usat, Ue = 10e3, 100e3, 12.0, 1.5
Ua = max(-Usat, min(Usat, -R2 / R1 * Ue))
Un = Ue + (Ua - Ue) * R1 / (R1 + R2)
mc_numeric(
    correct=Un,
    options={"A": 0.0, "B": 0.273, "C": 1.5, "D": -1.09},
    mistakes={"A": 0.0, "C": Ue, "D": Ua * R1 / (R1 + R2)},
    method="saturated output, divider R1-R2 between Ue and Ua",
)
