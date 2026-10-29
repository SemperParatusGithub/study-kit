"""Phasor diagram of ex-ws-rl-reihe: 230 V, 50 Hz, R = 40 Ω, L = 100 mH (current at 0°).

The current is the reference phasor on the positive real axis, drawn to its own scale just
beside the axis; U_R and U_L are chained head to tail, their sum U runs from the origin.
"""

import math

from studykit.figures import plot

R, X_L = 40.0, 2 * math.pi * 50.0 * 0.1  # X_L = 2 pi f L
I_A = 230.0 / math.hypot(R, X_L)
ALT = (
    "Zeigerdiagramm der RL-Reihenschaltung am Netz: Der Strom I = 4,52 A liegt als "
    "Bezugszeiger auf der positiven reellen Achse. UR = 180,9 V zeigt in dieselbe Richtung, "
    "UL = 142,1 V steht senkrecht darauf. Ihre Summe U = 230 V eilt dem Strom um 38,1 Grad "
    "voraus."
)


def build():
    return plot.phasor(
        {"U_R": (I_A * R, 0), "U_L": (I_A * X_L, 90)},
        chain=True,
        reference={"I": (I_A, 0)},
        alt=ALT,
    )
