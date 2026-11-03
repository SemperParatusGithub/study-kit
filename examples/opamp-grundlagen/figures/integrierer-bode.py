"""Bode diagram of the inverting integrator H = -1/(jωRC) with RC = 2.2 ms (f_1 = 72.3 Hz).

plot.custom instead of plot.bode: the bode template anchors the phase of a negative gain
at -180° and so draws -270°; the lecture writes the equivalent +90° (-1/j = +j).
"""

import numpy as np

from studykit.figures import color, plot

RC = 22e3 * 100e-9
F1 = 1 / (2 * np.pi * RC)

ALT = (
    "Bode-Diagramm des Integrierers mit R = 22 kΩ und C = 100 nF von 1 Hz bis 10 kHz. "
    "Betrag: eine Gerade, die mit 20 dB pro Dekade fällt und bei f_1 = 72.3 Hz durch 0 dB "
    "geht; bei 1 Hz liegt sie bei etwa +37 dB, bei 10 kHz bei etwa -43 dB. Phase: bei allen "
    "Frequenzen konstant +90 Grad, der Ausgang eilt dem Eingang also um 90 Grad vor."
)


def build():
    f = np.logspace(0, 4, 400)
    H = -1 / (1j * 2 * np.pi * f * RC)
    mag = 20 * np.log10(np.abs(H))
    ph = np.degrees(np.angle(H))
    with plot.custom(alt=ALT, nrows=2, sharex=True) as c:
        ax_m, ax_p = c.ax
        c.fig.set_size_inches(c.fig.get_size_inches()[0], c.fig.get_size_inches()[1] * 1.5)
        ax_m.semilogx(f, mag, color=color(0))
        ax_m.axhline(0, color=color("muted"), lw=0.8)
        ax_m.plot([F1], [0], "o", color=color(1), ms=4)
        ax_m.annotate(r"$f_1$", (F1, 0), xytext=(6, 6), textcoords="offset points", color=color("fg"))
        ax_m.set_ylim(-50, 45)
        ax_m.set_yticks([-40, -20, 0, 20, 40])
        ax_m.set_ylabel("Betrag in dB")
        ax_p.semilogx(f, ph, color=color(0))
        ax_p.set_ylim(0, 180)
        ax_p.set_yticks([0, 45, 90, 135, 180])
        ax_p.set_ylabel("Phase in °")
        ax_p.set_xlabel("Frequenz $f$ in Hz")
        ax_p.set_xlim(1, 1e4)
        c.fig.align_ylabels([ax_m, ax_p])
        c.facts.update({"RC_s": RC, "f1_Hz": float(F1), "phase_deg": float(ph[0]),
                        "mag_db_at_1Hz": float(mag[0]), "mag_db_at_10kHz": float(mag[-1])})
    return c.figure
