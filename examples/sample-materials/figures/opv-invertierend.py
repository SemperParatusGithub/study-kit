"""Inverting amplifier of lecture 3 (slides, R1 = 10 kΩ, R2 = 47 kΩ)."""

from studykit.figures import circuit


def build():
    return circuit.opamp("inverting", R1="10 kΩ", R2="47 kΩ")
