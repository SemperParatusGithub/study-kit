# Integrator R = 20 kOhm, C = 100 nF, Ua(0) = 1.5 V; Ue = 0.6 V for t < 8 ms, then -0.25 V.
from studykit.check import answers

R, C, Ua0 = 20e3, 100e-9, 1.5
tau = R * C
s1 = -0.6 / tau  # V/s
s2 = 0.25 / tau
t0a = Ua0 / -s1
Ua8 = Ua0 + s1 * 8e-3
Ua20 = Ua8 + s2 * 12e-3
t0b = 8e-3 + (-Ua8) / s2
assert all(abs(v) < 10 for v in (Ua8, Ua20))
answers(t0a=t0a * 1e3, Ua8=Ua8, Ua20=Ua20, t0b=t0b * 1e3, method="piecewise linear ramps")
