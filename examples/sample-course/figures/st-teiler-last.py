"""Loaded voltage divider with symbolic values (summary, belasteter Teiler)."""

from studykit.figures import circuit


def build():
    return circuit.voltage_divider(RL=True)
