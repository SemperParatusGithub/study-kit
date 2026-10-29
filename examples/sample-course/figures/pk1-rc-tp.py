"""RC low-pass of the mock exam task pk1-t3: R = 8,2 kΩ, C = 1 nF."""

from studykit.figures import circuit


def build():
    return circuit.rc("lowpass", "8,2 kΩ", "1 nF", phasors=True)
