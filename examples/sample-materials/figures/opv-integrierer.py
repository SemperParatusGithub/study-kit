"""Integrator of lecture 3 and the script (R = 10 kΩ, C = 100 nF, tau = 1 ms)."""

from studykit.figures import circuit


def build():
    return circuit.opamp("integrator", R="10 kΩ", C="100 nF")
