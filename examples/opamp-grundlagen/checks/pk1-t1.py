# Inverting amplifier R1 = 3.3k, R2 = 22k, +-11 V; source Ri = 0.68k. Nodal analysis with a finite
# open-loop gain A, then A -> oo, so the ideal rules are not assumed.
import sympy as sp

from studykit.check import answers

A, Ue, Un, Ua = sp.symbols("A U_e U_n U_a")
R1, R2, Ri, Usat = 3300, 22000, 680, 11


def gain(rin):
    s = sp.solve([sp.Eq((Ue - Un) / rin, (Un - Ua) / R2), sp.Eq(Ua, -A * Un)], [Un, Ua], dict=True)
    return sp.limit(s[0][Ua] / Ue, A, sp.oo)


V = float(gain(R1))


def out(ue):
    return max(-Usat, min(Usat, V * ue))


answers(
    V=V,
    Ua1=out(0.4),
    Ua2=out(-2.0),
    Uemax=Usat / abs(V),
    VU0=float(gain(R1 + Ri)),
    method="node equation with open-loop gain A -> infinity, sympy",
)
