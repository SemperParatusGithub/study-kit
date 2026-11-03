# Open loop: V0 = 2e5, Usat = 13 V, Ud = 0.1 mV.
from studykit.check import mc_numeric

V0, Usat, Ud = 2e5, 13.0, 0.1e-3
mc_numeric(
    correct=min(Usat, V0 * Ud),
    options={"A": 20.0, "B": 2.0, "C": 13.0, "D": 0.0},
    mistakes={"A": V0 * Ud, "B": V0 * Ud / 10, "D": 0.0},
    method="Ua = V0 Ud = 20 V clipped at Usat; distractors: no clipping, power of ten, virtual ground",
)
