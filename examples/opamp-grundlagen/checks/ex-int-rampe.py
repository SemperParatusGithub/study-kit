# Integrator R = 15 kOhm, C = 220 nF, Ua(0) = 0, Ue = 0.3 V from t = 0, output +-12 V.
from studykit.check import answers

R, C, Ue, Usat = 15e3, 220e-9, 0.3, 12.0
I = Ue / R
slope = -Ue / (R * C)
answers(
    I=I * 1e6,
    slope=slope,
    Ua20=slope * 20e-3,
    tsat=Usat / abs(slope) * 1e3,
    method="Ua(t) = -Ue t/(R C)",
)
