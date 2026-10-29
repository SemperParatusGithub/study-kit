"""RC high-pass as a two-port with phasor labels (summary, RC-Filter)."""

from studykit.figures import circuit


def build():
    return circuit.rc("highpass", phasors=True)
