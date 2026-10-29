"""RC low-pass of ex-rc-tp-grenzfrequenz: R = 2,2 kΩ, C = 47 nF."""

from studykit.figures import circuit


def build():
    return circuit.rc("lowpass", "2,2 kΩ", "47 nF", phasors=True)
