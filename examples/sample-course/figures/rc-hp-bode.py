"""Bode diagram of the RC high-pass R = 1 kΩ, C = 100 nF with asymptotes (summary)."""

from studykit.figures import plot

ALT = (
    "Bode-Diagramm des RC-Hochpasses mit R = 1 kΩ und C = 100 nF von 10 Hz bis 100 kHz. "
    "Betrag: unterhalb der Grenzfrequenz 1,59 kHz Anstieg mit 20 dB pro Dekade, dort -3 dB, "
    "darüber nahe 0 dB; gestrichelt die Asymptoten. Phase: von +90 Grad über +45 Grad bei "
    "der Grenzfrequenz gegen 0 Grad."
)


def build():
    tau = 1e3 * 100e-9
    g = f"{tau!r}*s/(1 + {tau!r}*s)"
    return plot.bode(g, w=(10, 1e5), unit="Hz", asymptotes=True, alt=ALT)
