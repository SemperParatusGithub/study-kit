"""Inverting amplifier with symbolic R1 and R2 (summary and exercises of verstaerker-grundschaltungen)."""

from studykit.figures import circuit

ALT = (
    "Schaltbild des invertierenden Verstärkers: Die Eingangsspannung Ue liegt über R1 am "
    "invertierenden Eingang, R2 führt vom Ausgang auf den invertierenden Eingang zurück, der "
    "nichtinvertierende Eingang liegt auf Masse. Zählpfeile Ue und Ua jeweils gegen Masse."
)


def build():
    return circuit.opamp("inverting", alt=ALT)
