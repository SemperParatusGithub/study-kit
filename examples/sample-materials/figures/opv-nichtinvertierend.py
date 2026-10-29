"""Non-inverting amplifier of lecture 3 (slides, R1 = 10 kΩ, R2 = 22 kΩ)."""

from studykit.figures import circuit


def build():
    return circuit.opamp("non_inverting", R1="10 kΩ", R2="22 kΩ")
