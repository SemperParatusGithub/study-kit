"""Bode diagram of the RC low-pass of ex-rc-tp-bode: R = 3,3 kΩ, C = 4,7 nF."""

from studykit.figures import plot

ALT = (
    "Bode-Diagramm des RC-Tiefpasses mit R = 3,3 kΩ und C = 4,7 nF von 100 Hz bis 1 MHz. "
    "Betrag: bis zur Grenzfrequenz 10,3 kHz nahe 0 dB, darüber Abfall mit 20 dB pro "
    "Dekade, bei 103 kHz rund -20 dB; gestrichelt die Asymptoten. Phase: -5,7 Grad bei "
    "1,03 kHz, -45 Grad bei der Grenzfrequenz und -84,3 Grad bei 103 kHz."
)


def build():
    tau = 3.3e3 * 4.7e-9
    return plot.bode(f"1/(1 + {tau!r}*s)", w=(100, 1e6), unit="Hz", asymptotes=True, alt=ALT)
