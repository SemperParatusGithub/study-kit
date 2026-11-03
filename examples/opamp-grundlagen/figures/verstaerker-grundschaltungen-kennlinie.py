"""Transfer characteristic Ua(Ue) of an inverting amplifier with output saturation (verstaerker-grundschaltungen)."""

import numpy as np

from studykit.figures import axis_label, color, plot

R1, R2, USAT = 12e3, 68e3, 12.0
V = -R2 / R1
UE_MAX = USAT / abs(V)

ALT = (
    "Übertragungskennlinie Ua über Ue des invertierenden Verstärkers mit R1 = 12 kΩ und "
    "R2 = 68 kΩ (V = -5.67) bei einer Ausgangsbegrenzung von plus/minus 12 V. Zwischen "
    "Ue = -Usat/|V| und Ue = +Usat/|V| (etwa plus/minus 2.12 V) ist die Kennlinie eine fallende "
    "Gerade durch den Ursprung mit der Steigung V; außerhalb bleibt der Ausgang konstant bei "
    "+12 V (für negative Ue) bzw. -12 V (für positive Ue). Gestrichelt: der rechnerische "
    "Verlauf ohne Begrenzung."
)


def build():
    ue = np.linspace(-4, 4, 801)
    ua_lin = V * ue
    ua = np.clip(ua_lin, -USAT, USAT)
    with plot.custom(alt=ALT) as c:
        ax = c.ax
        ax.plot(ue, ua_lin, linestyle="--", color=color("muted"), linewidth=1.0)
        ax.plot(ue, ua, color=color(0))
        for x in (-UE_MAX, UE_MAX):
            ax.axvline(x, linestyle=":", color=color("muted"), linewidth=0.8)
        ax.axhline(0, color=color("fg"), linewidth=0.6)
        ax.axvline(0, color=color("fg"), linewidth=0.6)
        ax.set_xlim(-4, 4)
        ax.set_ylim(-16, 16)
        ax.set_xticks([-UE_MAX, 0, UE_MAX])
        ax.set_xticklabels([r"$-U_\mathrm{sat}/|V|$", "0", r"$U_\mathrm{sat}/|V|$"])
        ax.set_yticks([-USAT, 0, USAT])
        ax.set_yticklabels([r"$-U_\mathrm{sat}$", "0", r"$U_\mathrm{sat}$"])
        ax.set_xlabel(axis_label("U_e", "V"))
        ax.set_ylabel(axis_label("U_a", "V"))
        c.facts.update({"V": V, "Ue_max": UE_MAX, "Usat": USAT})
    return c.figure
