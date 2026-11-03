"""Non-inverting amplifier R1 = 2 kΩ, R2 = 48 kΩ (ex-iopv-mindest-leerlaufverstaerkung)."""

from studykit.figures import circuit

ALT = (
    "Nichtinvertierender Verstärker: Die Eingangsspannung Ue liegt am nichtinvertierenden "
    "Eingang des OPV. Der Spannungsteiler aus R2 = 48 kΩ (vom Ausgang zum invertierenden "
    "Eingang) und R1 = 2 kΩ (vom invertierenden Eingang nach Masse) führt einen Teil der "
    "Ausgangsspannung Ua zurück."
)


def build():
    return circuit.opamp("non_inverting", "2 kΩ", "48 kΩ", alt=ALT)
