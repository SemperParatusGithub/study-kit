# Non-inverting amplifier R1 = 2 kOhm, R2 = 48 kOhm; gain at most 0.2 % below ideal.
from studykit.check import answers

R1, R2 = 2e3, 48e3
k = R1 / (R1 + R2)
Vid = 1 / k


def V(V0):
    return V0 / (1 + k * V0)


# F = 1 - V/Vid = 1/(1 + k V0) <= 0.002  ->  V0 >= (1/0.002 - 1)/k
V0min = (1 / 0.002 - 1) / k
F = (1 - V(1e5) / Vid) * 100
dV = (V(5e4) - V(1e5)) / V(1e5) * 100
fac = 50 / abs(dV)
answers(V0min=V0min, F=F, dV=dV, fac=fac, method="exact closed-loop gain V0/(1+k V0)")
