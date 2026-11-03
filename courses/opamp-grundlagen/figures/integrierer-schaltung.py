"""Inverting integrator: R from the input to the inverting input, C in the feedback path."""

from studykit.figures import circuit

ALT = (
    "Schaltbild des invertierenden Integrierers: Die Eingangsspannung U_e liegt über den "
    "Widerstand R am invertierenden Eingang des Operationsverstärkers, der Kondensator C "
    "verbindet den Ausgang mit dem invertierenden Eingang, der nichtinvertierende Eingang "
    "liegt auf Masse. Die Zählpfeile von U_e und U_a zeigen jeweils gegen Masse."
)


def build():
    return circuit.opamp("integrator", alt=ALT)
