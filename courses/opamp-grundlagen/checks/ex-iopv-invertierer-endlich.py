# Inverting amplifier with finite open-loop gain V0: Ua = V0 (Up - Un), Up = 0, no input currents.
import sympy as sp

from studykit.check import answers

R1, R2, V0, Ue, Un, Ua = sp.symbols("R1 R2 V0 U_e U_n U_a", positive=True)
Un_s, Ua_s = sp.symbols("Un Ua")
sol = sp.solve(
    [sp.Eq((Ue - Un_s) / R1, (Un_s - Ua_s) / R2), sp.Eq(Ua_s, V0 * (0 - Un_s))],
    [Un_s, Ua_s],
    dict=True,
)[0]
Vexpr = sp.simplify(sol[Ua_s] / Ue)
assert sp.simplify(sp.limit(Vexpr, V0, sp.oo) + R2 / R1) == 0
vals = {R1: 4.7e3, R2: 100e3, V0: 1000, Ue: 0.2}
V = float(Vexpr.subs(vals))
ideal = 100e3 / 4.7e3
dev = (ideal - abs(V)) / ideal * 100
Un_val = float(sol[Un_s].subs(vals)) * 1e3  # mV
answers(Vexpr=Vexpr, V=V, dev=dev, Un=Un_val, method="node equation at Un with Ua = -V0 Un, sympy")
