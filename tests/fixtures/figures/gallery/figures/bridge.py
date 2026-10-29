from studykit.figures import circuit


def build():
    return circuit.bridge("wheatstone", "1 kΩ", "2 kΩ", "1 kΩ", "2 kΩ", "10 V")
