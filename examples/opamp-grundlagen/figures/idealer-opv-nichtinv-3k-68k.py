"""Non-inverting amplifier R1 = 3 kΩ, R2 = 68 kΩ (ex-iopv-endliche-leerlaufverstaerkung)."""

from studykit.figures import circuit

ALT = (
    "Nichtinvertierender Verstärker: Die Eingangsspannung Ue liegt am nichtinvertierenden "
    "Eingang des OPV. Der Spannungsteiler aus R2 = 68 kΩ (vom Ausgang zum invertierenden "
    "Eingang) und R1 = 3 kΩ (vom invertierenden Eingang nach Masse) führt einen Teil der "
    "Ausgangsspannung Ua zurück."
)


def build():
    return circuit.opamp("non_inverting", "3 kΩ", "68 kΩ", alt=ALT)
