# Integrator R = 68 kOhm, C = 150 nF, +-11 V, Ue = -0.8 V from t = 0, Ua(0) = 0.
import math

from studykit.check import answers

R, C, Ue, Usat = 68e3, 150e-9, -0.8, 11.0
tau = R * C
slope = -Ue / tau
f1 = 1 / (2 * math.pi * tau)
answers(
    slope=slope,
    tsat=Usat / abs(slope) * 1e3,
    f1=f1,
    H50=1 / (2 * math.pi * 50 * tau),
    method="Ua = -Ue t/(R C); |H| = 1/(w R C)",
)
