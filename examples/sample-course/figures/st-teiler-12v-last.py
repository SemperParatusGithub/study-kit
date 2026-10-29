"""Loaded divider of ex-st-belastet: the divider of ex-st-unbelastet with RL = 3,3 kΩ."""

from studykit.figures import circuit


def build():
    return circuit.voltage_divider("1,5 kΩ", "3,3 kΩ", "12 V", RL="3,3 kΩ")
