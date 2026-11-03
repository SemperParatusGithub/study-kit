# Inverting integrator R = 33 kOhm, C = 47 nF.
import math

from studykit.check import answers

R, C = 33e3, 47e-9
tau = R * C
f1 = 1 / (2 * math.pi * tau)
H500 = 1 / (2 * math.pi * 500 * tau)
answers(RC=tau * 1e3, f1=f1, H500=H500, method="|H| = 1/(w R C)")
