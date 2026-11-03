# Open-loop op amp: V0 = 2e5, Usat = 13.5 V, Up = 25.030 mV, Un = 25.000 mV, then Un = 24.900 mV.
from studykit.check import answers

V0, Usat = 2e5, 13.5
Up, Un, Un2 = 25.030e-3, 25.000e-3, 24.900e-3


def out(ud):
    return max(-Usat, min(Usat, V0 * ud))


Ud = Up - Un
answers(
    Ud=Ud * 1e6,  # µV
    Ua=out(Ud),
    Udmax=Usat / V0 * 1e6,  # µV
    Ua2=out(Up - Un2),
    method="Ua = V0 Ud clipped at +-Usat",
)
