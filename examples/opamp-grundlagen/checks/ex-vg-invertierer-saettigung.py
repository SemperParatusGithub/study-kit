# Inverting amplifier R1 = 3.9 kOhm, R2 = 27 kOhm, output limited to +-10 V, source Ri = 1.2 kOhm.
from studykit.check import answers

R1, R2, Usat, Ri = 3.9e3, 27e3, 10.0, 1.2e3
V = -R2 / R1


def out(ue):
    return max(-Usat, min(Usat, V * ue))


answers(
    V=V,
    Ua1=out(0.6),
    Ua2=out(-1.8),
    Uemax=Usat / abs(V),
    VU0=-R2 / (R1 + Ri),
    method="ideal inverting gain with clipping; Ri in series with R1",
)
