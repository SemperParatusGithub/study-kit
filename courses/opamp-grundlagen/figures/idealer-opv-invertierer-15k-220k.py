"""Inverting amplifier R1 = 15 kΩ, R2 = 220 kΩ (ex-iopv-virtuelle-masse-saettigung)."""

from studykit.figures import circuit

ALT = (
    "Invertierender Verstärker: Die Eingangsspannung Ue liegt über R1 = 15 kΩ am "
    "invertierenden Eingang des OPV, R2 = 220 kΩ verbindet den Ausgang mit dem "
    "invertierenden Eingang, der nichtinvertierende Eingang liegt auf Masse. Die "
    "Ausgangsspannung Ua wird gegen Masse gemessen."
)


def build():
    return circuit.opamp("inverting", "15 kΩ", "220 kΩ", alt=ALT)
