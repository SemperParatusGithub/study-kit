"""Bode diagram of the RC low-pass R = 1 kΩ, C = 100 nF with asymptotes.

A course figure script: figures/<slug>.py defines build() and returns the Figure of one
studykit.figures template. The alt text is in the course language and states what the
figure shows, with its key values.
"""

from studykit.figures import plot

ALT = (
    "Bode-Diagramm des RC-Tiefpasses mit R = 1 kΩ und C = 100 nF von 10 Hz bis 100 kHz. "
    "Betrag: bis zur Grenzfrequenz 1,59 kHz nahe 0 dB, dort -3 dB, darüber Abfall mit "
    "20 dB pro Dekade; gestrichelt die Asymptoten. Phase: von 0 Grad über -45 Grad bei der "
    "Grenzfrequenz gegen -90 Grad."
)


def build():
    tau = 1e3 * 100e-9
    return plot.bode(f"1/(1 + {tau!r}*s)", w=(10, 1e5), unit="Hz", asymptotes=True, alt=ALT)
