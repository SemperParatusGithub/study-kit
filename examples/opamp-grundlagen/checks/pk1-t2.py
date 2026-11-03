# Non-inverting V = 9, R1 = 1.5k; sensor U0 = 0.75 V, Ri = 56k, load 2.2k.
import sympy as sp

from studykit.check import answers

R2 = sp.symbols("R2", positive=True)
r2 = sp.solve(sp.Eq(1 + R2 / 1500, 9), R2)[0]
U0, Ri, RL = 0.75, 56e3, 2.2e3
I = U0 / (Ri + RL)  # series loop source - Ri - RL
answers(
    R2=float(r2) / 1e3,
    Ua=9 * 0.55,
    UL1=I * RL * 1e3,  # mV
    UL2=U0,  # ideal follower: no current from the sensor
    method="V = 1 + R2/R1 solved with sympy; loop current for the load",
)
