"""Phasor diagram of the summary's RL example: I = 2 A, R = 30 Ω, X_L = 40 Ω."""

from studykit.figures import plot

ALT = (
    "Zeigerdiagramm der RL-Reihenschaltung: Der Zeiger UR = 60 V liegt in Richtung des "
    "Stroms auf der reellen Achse, UL = 80 V steht um 90 Grad gedreht an seiner Spitze. "
    "Die Summe U = 100 V eilt dem Strom um 53,1 Grad voraus."
)


def build():
    return plot.phasor({"U_R": (60, 0), "U_L": (80, 90)}, chain=True, alt=ALT)
