"""Non-inverting amplifier with symbolic R1 and R2 (summary and exercises of verstaerker-grundschaltungen)."""

from studykit.figures import circuit

ALT = (
    "Schaltbild des nichtinvertierenden Verstärkers: Die Eingangsspannung Ue liegt am "
    "nichtinvertierenden Eingang. Der Spannungsteiler aus R2 (vom Ausgang zum invertierenden "
    "Eingang) und R1 (vom invertierenden Eingang nach Masse) führt einen Teil von Ua zurück. "
    "Zählpfeile Ue und Ua jeweils gegen Masse."
)


def build():
    return circuit.opamp("non_inverting", alt=ALT)
