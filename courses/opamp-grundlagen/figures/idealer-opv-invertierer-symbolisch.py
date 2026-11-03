"""Inverting amplifier with symbolic R1 and R2 (summary and ex-iopv-invertierer-endlich)."""

from studykit.figures import circuit

ALT = (
    "Invertierender Verstärker: Die Eingangsspannung Ue liegt über R1 am invertierenden "
    "Eingang des OPV, R2 verbindet den Ausgang mit dem invertierenden Eingang "
    "(Gegenkopplung), der nichtinvertierende Eingang liegt auf Masse. Die "
    "Ausgangsspannung Ua wird gegen Masse gemessen."
)


def build():
    return circuit.opamp("inverting", "R_1", "R_2", alt=ALT)
