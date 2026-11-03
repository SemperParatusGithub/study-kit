"""Transfer characteristic U_a(U_d) of an op-amp without feedback: V0 = 1e5, U_sat = 12 V.

Used in the summary chapter of idealer-opv: the linear region is only ±120 µV wide.
"""

import numpy as np

from studykit.figures import axis_label, color, plot

V0 = 1e5
U_SAT = 12.0
ALT = (
    "Übertragungskennlinie eines OPV ohne Rückkopplung mit der Leerlaufverstärkung "
    "V0 = 10^5 und der Sättigungsspannung 12 V: Ausgangsspannung Ua über der "
    "Differenzspannung Ud von -250 µV bis 250 µV. Zwischen Ud = -120 µV und Ud = 120 µV "
    "steigt Ua als Gerade mit der Steigung V0 von -12 V auf 12 V (linearer Bereich); "
    "außerhalb bleibt Ua konstant auf +12 V oder -12 V (Sättigung, gestrichelt markiert)."
)


def build():
    ud_max = U_SAT / V0
    ud = np.linspace(-250e-6, 250e-6, 1001)
    ua = np.clip(V0 * ud, -U_SAT, U_SAT)
    with plot.custom(alt=ALT) as c:
        ax = c.ax
        for level in (U_SAT, -U_SAT):
            ax.axhline(level, color=color("muted"), lw=1.0, ls=(0, (4, 2)), zorder=2)
        ax.axvspan(-ud_max * 1e6, ud_max * 1e6, color=color(1), alpha=0.12, lw=0, zorder=1)
        ax.plot(ud * 1e6, ua, color=color(0), zorder=4)
        ax.annotate(
            "linearer Bereich",
            (0, -U_SAT),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
            color=color("muted"),
        )
        ax.annotate(
            r"$+U_\mathrm{sat}$",
            (-245, U_SAT),
            xytext=(0, -4),
            textcoords="offset points",
            ha="left",
            va="top",
            fontsize=8,
            color=color("muted"),
        )
        ax.annotate(
            r"$-U_\mathrm{sat}$",
            (245, -U_SAT),
            xytext=(0, 4),
            textcoords="offset points",
            ha="right",
            va="bottom",
            fontsize=8,
            color=color("muted"),
        )
        ax.set_xlim(-250, 250)
        ax.set_ylim(-15, 15)
        ax.set_xticks([-240, -120, 0, 120, 240])
        ax.set_xlabel(axis_label("U_d", r"$\mathrm{\mu V}$"))
        ax.set_ylabel(axis_label("U_a", "V"))
        c.facts.update({"V0": V0, "U_sat_V": U_SAT, "U_d_linear_max_uV": ud_max * 1e6})
    return c.figure
