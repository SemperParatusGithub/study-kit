"""Phasor diagram of the mock exam task pk1-t2: R = 1 kΩ, C = 220 nF, U = 10 V at 1 kHz.

The current is the reference phasor on the positive real axis, drawn to its own scale just
beside the axis; U_R and U_C are chained head to tail, their sum U runs from the origin.
"""

import math

from studykit.figures import plot

R, X_C = 1e3, 1 / (2 * math.pi * 1e3 * 220e-9)  # X_C = 1 / (2 pi f C) at 1 kHz
I_A = 10.0 / math.hypot(R, X_C)
ALT = (
    "Zeigerdiagramm der RC-Reihenschaltung aus der Probeklausur: Der Strom I = 8,10 mA liegt "
    "als Bezugszeiger auf der positiven reellen Achse. UR = 8,10 V zeigt in dieselbe "
    "Richtung, UC = 5,86 V von dessen Spitze senkrecht nach unten. Die Summe U = 10 V eilt "
    "dem Strom um 35,9 Grad nach."
)


def build():
    return plot.phasor(
        {"U_R": (I_A * R, 0), "U_C": (I_A * X_C, -90)},
        chain=True,
        reference={"I": (I_A, 0)},
        alt=ALT,
    )
