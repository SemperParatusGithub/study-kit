# Inverting integrator R = 4.7 kOhm, C = 10 nF: H(jw) = -1/(jw R C).
import cmath
import math

from studykit.check import answers

R, C = 4.7e3, 10e-9


def H(f):
    return -1 / (1j * 2 * math.pi * f * R * C)


f1 = 1 / (2 * math.pi * R * C)
answers(
    f1=f1,
    Hdb=20 * math.log10(abs(H(1e3))),
    phi=math.degrees(cmath.phase(H(1e3))),  # -1/(j x) = +j/x: +90 degrees, output leads
    f20=10 * f1 / 1e3,  # |H| = f1/f = 0.1; kHz
    method="complex frequency response, cmath",
)
