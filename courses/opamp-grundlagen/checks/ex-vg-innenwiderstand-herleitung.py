# Inverting amplifier fed by a source U0 with internal resistance Ri (in series with R1).
import sympy as sp

from studykit.check import answers

R1, R2, Ri = sp.symbols("R1 R2 Ri", positive=True)
VU0 = -R2 / (R1 + Ri)  # virtual ground: the input current is U0/(Ri + R1)
# |VU0| >= 0.98 R2/R1  <=>  R1/(R1 + Ri) >= 0.98
r1 = sp.solve(sp.Eq(R1 / (R1 + Ri), sp.Rational(98, 100)), R1)[0]
R1min = float(r1.subs(Ri, 1.5)) # kOhm
answers(VU0=VU0, R1min=R1min, R2=5 * R1min, method="virtual ground, series Ri + R1, sympy")
