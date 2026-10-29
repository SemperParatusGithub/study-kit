"""Phasor diagram of the summary's RL example: I = 2 A, R = 30 Ω, X_L = 40 Ω.

The current is the reference phasor on the positive real axis, drawn to its own scale just
beside the axis; U_R and U_L are chained head to tail, their sum U runs from the origin.
"""

from studykit.figures import plot

I_A, R, X_L = 2.0, 30.0, 40.0
ALT = (
    "Zeigerdiagramm der RL-Reihenschaltung: Der Strom I = 2 A liegt als Bezugszeiger auf der "
    "positiven reellen Achse. UR = 60 V zeigt in dieselbe Richtung, UL = 80 V steht um "
    "90 Grad gedreht an seiner Spitze. Die Summe U = 100 V eilt dem Strom um 53,1 Grad voraus."
)


def build():
    return plot.phasor(
        {"U_R": (I_A * R, 0), "U_L": (I_A * X_L, 90)},
        chain=True,
        reference={"I": (I_A, 0)},
        alt=ALT,
    )
