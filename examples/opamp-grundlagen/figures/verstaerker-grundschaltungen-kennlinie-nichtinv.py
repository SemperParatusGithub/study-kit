"""Transfer characteristic of the non-inverting amplifier of ex-vg-kennlinie-saettigung."""

import numpy as np

from studykit.figures import axis_label, color, plot

R1, R2, USAT = 3.9e3, 15e3, 12.0
V = 1 + R2 / R1
UE_MAX = USAT / V

ALT = (
    "Übertragungskennlinie Ua über Ue des nichtinvertierenden Verstärkers mit R1 = 3.9 kΩ und "
    "R2 = 15 kΩ (V = 4.85) bei einer Ausgangsbegrenzung von plus/minus 12 V. Zwischen "
    "Ue = -2.48 V und Ue = +2.48 V steigt die Kennlinie als Gerade durch den Ursprung mit der "
    "Steigung 4.85; darunter bleibt der Ausgang bei -12 V, darüber bei +12 V. Gepunktet: die "
    "Aussteuergrenzen."
)


def build():
    ue = np.linspace(-4, 4, 801)
    ua = np.clip(V * ue, -USAT, USAT)
    with plot.custom(alt=ALT) as c:
        ax = c.ax
        ax.plot(ue, ua, color=color(0))
        for x in (-UE_MAX, UE_MAX):
            ax.axvline(x, linestyle=":", color=color("muted"), linewidth=0.8)
        ax.axhline(0, color=color("fg"), linewidth=0.6)
        ax.axvline(0, color=color("fg"), linewidth=0.6)
        ax.set_xlim(-4, 4)
        ax.set_ylim(-15, 15)
        ax.set_xticks([-4, -3, -2, -1, 0, 1, 2, 3, 4])
        ax.set_yticks([-12, -8, -4, 0, 4, 8, 12])
        ax.set_xlabel(axis_label("U_e", "V"))
        ax.set_ylabel(axis_label("U_a", "V"))
        c.facts.update({"V": V, "Ue_max": UE_MAX, "Usat": USAT})
    return c.figure
