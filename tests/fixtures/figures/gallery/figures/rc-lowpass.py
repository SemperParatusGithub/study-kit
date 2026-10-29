from studykit.figures import circuit


def build():
    return circuit.rc("lowpass", "1 kΩ", "100 nF")
