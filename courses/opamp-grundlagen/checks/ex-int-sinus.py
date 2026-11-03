# Integrator R = 10 kOhm, C = 47 nF, Ue = 0.5 V sin(2 pi f t), output +-10 V, no DC.
import math

from studykit.check import answers

R, C, Uhat, Usat = 10e3, 47e-9, 0.5, 10.0


def amp(f):
    return Uhat / (2 * math.pi * f * R * C)


fmin = Uhat / (2 * math.pi * R * C * Usat)
answers(Uahat=amp(200), fmin=fmin, Ua12=amp(12), method="amplitude Uhat/(w R C)")
