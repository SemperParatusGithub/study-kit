# Inverting integrator with constant Ue from t = 0 and Ua(0) = Ua0: node equation Ue/R = -C dUa/dt.
import sympy as sp

from studykit.check import answers

Ue, R, C, t, Ua0, Usat = sp.symbols("Ue R C t Ua0 Usat", positive=True)
Ua = sp.Function("Ua")
sol = sp.dsolve(sp.Eq(Ue / R, -C * Ua(t).diff(t)), Ua(t), ics={Ua(0): Ua0}).rhs
(tsat,) = sp.solve(sp.Eq(sol, -Usat), t)
answers(Ua=sp.simplify(sol), tsat=sp.simplify(tsat), method="ODE from the node equation, sympy dsolve")
