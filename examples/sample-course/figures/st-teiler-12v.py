"""Unloaded divider of ex-st-unbelastet: U0 = 12 V, R1 = 1,5 kΩ, R2 = 3,3 kΩ."""

from studykit.figures import circuit


def build():
    return circuit.voltage_divider("1,5 kΩ", "3,3 kΩ", "12 V")
