# Open loop: V0 = 1e5, Usat = 12 V; largest |Ud| in the linear range.
from studykit.check import mc_numeric

V0, Usat = 1e5, 12.0
mc_numeric(
    correct=Usat / V0,
    options={"A": 1.2e-3, "B": 120e-6, "C": 240e-6, "D": 12e-6},
    mistakes={"A": Usat / 1e4, "C": 2 * Usat / V0, "D": Usat / 1e6},
    method="Ud,max = Usat/V0; power of ten, full swing 2 Usat",
)
