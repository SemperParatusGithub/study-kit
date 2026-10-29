from studykit.figures import circuit


def build():
    return circuit.voltage_divider("4,7 kΩ", "2,2 kΩ", "12 V", RL="10 kΩ")
