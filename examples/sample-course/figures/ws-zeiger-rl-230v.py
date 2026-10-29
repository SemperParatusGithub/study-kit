"""Phasor diagram of ex-ws-rl-reihe: 230 V, 50 Hz, R = 40 Ω, L = 100 mH (current at 0°)."""

import math

from studykit.figures import plot

ALT = (
    "Zeigerdiagramm der RL-Reihenschaltung am Netz: UR = 180,9 V liegt in Richtung des "
    "Stroms auf der reellen Achse, UL = 142,1 V steht senkrecht darauf. Ihre Summe "
    "U = 230 V eilt dem Strom um 38,1 Grad voraus."
)


def build():
    r, l_h, f, u = 40.0, 0.1, 50.0, 230.0
    x_l = 2 * math.pi * f * l_h
    i = u / math.hypot(r, x_l)
    return plot.phasor({"U_R": (i * r, 0), "U_L": (i * x_l, 90)}, chain=True, alt=ALT)
