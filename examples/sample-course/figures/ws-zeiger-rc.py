"""Phasor diagram of ex-ws-zeigerdiagramm: I = 10 mA, R = 220 Ω, X_C = 330 Ω.

The current is the reference phasor on the positive real axis, drawn to its own scale just
beside the axis; U_R and U_C are chained head to tail, their sum U runs from the origin.
"""

from studykit.figures import plot

I_A, R, X_C = 10e-3, 220.0, 330.0
ALT = (
    "Zeigerdiagramm der RC-Reihenschaltung: Der Strom I = 10 mA liegt als Bezugszeiger auf "
    "der positiven reellen Achse. UR = 2,2 V zeigt in dieselbe Richtung, UC = 3,3 V von "
    "dessen Spitze senkrecht nach unten. Die Summe U = 3,97 V eilt dem Strom um "
    "56,3 Grad nach."
)


def build():
    return plot.phasor(
        {"U_R": (I_A * R, 0), "U_C": (I_A * X_C, -90)},
        chain=True,
        reference={"I": (I_A, 0)},
        angle_name=r"\varphi_u",
        alt=ALT,
    )
