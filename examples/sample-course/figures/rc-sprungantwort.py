"""Normalised charging curve of a capacitor with the tangent at t = 0 (summary)."""

import math

import numpy as np

from studykit.figures import color, plot

ALT = (
    "Normierte Ladekurve uC/U0 = 1 - exp(-t/τ) über t/τ von 0 bis 5. Die Tangente im "
    "Ursprung erreicht den Endwert 1 genau bei t = τ; dort hat die Kurve 63,2 Prozent "
    "erreicht. Weitere Marken: 86,5 Prozent bei 2τ, 95,0 Prozent bei 3τ und 99,3 Prozent "
    "bei 5τ."
)


def build():
    x = np.linspace(0, 5, 501)
    y = 1 - np.exp(-x)
    marks = {k: 1 - math.exp(-k) for k in (1, 2, 3, 5)}
    with plot.custom(alt=ALT) as c:
        ax = c.ax
        ax.axhline(1, color=color("muted"), lw=0.9, ls=(0, (4, 2)), zorder=2)
        ax.plot([0, 1], [0, 1], color=color(1), lw=1.0, zorder=3)
        ax.plot(x, y, color=color(0), zorder=4)
        ax.plot([1, 1], [0, marks[1]], color=color("muted"), lw=0.8, ls=":", zorder=2)
        for k, v in marks.items():
            ax.plot([k], [v], "o", ms=3.5, color=color("fg"), zorder=5)
            text = f"{100 * v:.1f} %".replace(".", ",")
            offset = (5, -9) if k == 1 else (0, -11)
            ax.annotate(
                text,
                (k, v),
                xytext=offset,
                textcoords="offset points",
                ha="left" if k == 1 else "center",
                va="center",
                fontsize=7,
            )
        ax.annotate(
            "Tangente",
            (0.9, 1.0),
            xytext=(-3, 3),
            textcoords="offset points",
            ha="right",
            va="bottom",
            fontsize=7,
            color=color(1),
        )
        ax.set_xlim(0, 5)
        ax.set_ylim(0, 1.1)
        ax.set_xlabel(r"$t/\tau$")
        ax.set_ylabel(r"$u_C/U_0$")
        c.facts.update({"fractions_at_t_over_tau": {str(k): v for k, v in marks.items()}})
    return c.figure
