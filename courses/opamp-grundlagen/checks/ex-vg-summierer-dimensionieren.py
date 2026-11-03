# Summing amplifier Ua = -(2 U1 + 0.5 U2), RF = 20 kOhm, output limited to +-10 V.
from studykit.check import answers

RF, Usat = 20e3, 10.0
R1, R2 = RF / 2, RF / 0.5


def out(u1, u2):
    return max(-Usat, min(Usat, -(RF / R1 * u1 + RF / R2 * u2)))


answers(R1=R1 / 1e3, R2=R2 / 1e3, Ua1=out(1.2, -3), Ua2=out(3.5, 8), method="Ua = -RF sum Ui/Ri")
