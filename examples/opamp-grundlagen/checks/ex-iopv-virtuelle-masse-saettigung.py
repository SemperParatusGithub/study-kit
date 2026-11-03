# Inverting amplifier, ideal op amp, R1 = 15 kOhm, R2 = 220 kOhm, output limited to +-12 V.
from studykit.check import answers

R1, R2, Usat = 15e3, 220e3, 12.0
V = -R2 / R1
Ua1 = V * 0.5
Uemax = Usat / abs(V)
Ue2 = 1.0
Ua2 = max(-Usat, min(Usat, V * Ue2))
# saturated: the op amp no longer holds Un at 0; R1 and R2 form a divider between Ue and Ua
Un = Ue2 + (Ua2 - Ue2) * R1 / (R1 + R2)
answers(Ua1=Ua1, Uemax=Uemax, Ua2=Ua2, Un=Un, method="ideal gain, clipping, divider R1-R2")
