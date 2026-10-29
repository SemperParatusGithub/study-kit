"""Phasor diagram of ex-ws-zeigerdiagramm: I = 10 mA, R = 220 Ω, X_C = 330 Ω."""

from studykit.figures import plot

ALT = (
    "Zeigerdiagramm der RC-Reihenschaltung: UR = 2,2 V liegt in Richtung des Stroms auf der "
    "reellen Achse, UC = 3,3 V zeigt von dessen Spitze senkrecht nach unten. Die Summe "
    "U = 3,97 V eilt dem Strom um 56,3 Grad nach."
)


def build():
    i, r, x_c = 10e-3, 220.0, 330.0
    return plot.phasor({"U_R": (i * r, 0), "U_C": (i * x_c, -90)}, chain=True, alt=ALT)
