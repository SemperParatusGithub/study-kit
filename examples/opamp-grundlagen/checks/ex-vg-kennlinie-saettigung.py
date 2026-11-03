# Non-inverting amplifier R1 = 3.9 kOhm to ground, R2 = 15 kOhm feedback, Usat = 12 V.
from studykit.check import answers

R1, R2, Usat = 3.9e3, 15e3, 12.0
V = 1 + R2 / R1


def out(ue):
    return max(-Usat, min(Usat, V * ue))


answers(V=V, Uemax=Usat / V, Ua3=out(3.0), Uapeak=out(2.0), method="V = 1 + R2/R1, clipping")
