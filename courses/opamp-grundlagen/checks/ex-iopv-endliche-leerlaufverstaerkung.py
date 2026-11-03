# Non-inverting amplifier, R1 = 3 kOhm to ground, R2 = 68 kOhm feedback, V0 = 500, Ue = 0.15 V.
from studykit.check import answers

R1, R2, V0, Ue = 3e3, 68e3, 500.0, 0.15
k = R1 / (R1 + R2)
Vid = 1 / k
V = V0 / (1 + k * V0)  # closed loop with finite open-loop gain
F = (Vid - V) / Vid * 100  # percent below the ideal gain
Ua = V * Ue
Ud = Ua / V0 * 1e3  # mV
answers(k=k, Vid=Vid, V=V, F=F, Ua=Ua, Ud=Ud, method="V = V0/(1 + k V0), numeric")
