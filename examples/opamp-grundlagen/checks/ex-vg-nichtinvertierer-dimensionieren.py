# Non-inverting amplifier V = 8.5, R1 = 2.2 kOhm to ground, Ue = 0.45 V.
from studykit.check import answers

V, R1, Ue = 8.5, 2.2e3, 0.45
R2 = (V - 1) * R1
I1 = Ue / R1  # Un = Up = Ue across R1
answers(R2=R2 / 1e3, Ua=V * Ue, I1=I1 * 1e6, method="V = 1 + R2/R1, Un = Ue")
