"""Reactances of L = 10 mH and C = 1 µF over frequency, with R = 100 Ω for reference."""

import math

import numpy as np

from studykit.figures import axis_label, color, plot

L, C, R = 10e-3, 1e-6, 100.0
ALT = (
    "Doppelt logarithmisches Diagramm der Blindwiderstände über der Frequenz von 10 Hz bis "
    "100 kHz: XL = ωL einer Spule mit 10 mH steigt mit der Frequenz, XC = 1/(ωC) eines "
    "Kondensators mit 1 µF fällt. Beide schneiden sich bei 1,59 kHz bei 100 Ω, wo auch die "
    "waagerechte Linie des frequenzunabhängigen Widerstands R = 100 Ω liegt."
)


def build():
    f = np.logspace(1, 5, 400)
    w = 2 * math.pi * f
    x_l, x_c = w * L, 1 / (w * C)
    f_x = 1 / (2 * math.pi * math.sqrt(L * C))
    with plot.custom(alt=ALT) as c:
        ax = c.ax
        ax.loglog(f, x_l, color=color(0), zorder=4)
        ax.loglog(f, x_c, color=color(1), zorder=4)
        ax.axhline(R, color=color("muted"), lw=1.0, ls=(0, (4, 2)), zorder=3)
        ax.plot([f_x], [math.sqrt(L / C)], "o", ms=3.5, color=color("fg"), zorder=5)
        style = {"textcoords": "offset points", "fontsize": 9}
        ax.annotate(r"$X_L = \omega L$", (3e4, 2 * math.pi * 3e4 * L), xytext=(-4, 2),
                    ha="right", va="bottom", color=color(0), **style)
        ax.annotate(r"$X_C = 1/(\omega C)$", (30, 1 / (2 * math.pi * 30 * C)), xytext=(4, 2),
                    ha="left", va="bottom", color=color(1), **style)
        ax.annotate("$R$", (1e5, R), xytext=(-2, 3), ha="right", va="bottom",
                    color=color("muted"), **style)
        ax.set_xlim(10, 1e5)
        ax.set_ylim(0.5, 2e4)
        ax.set_xlabel(axis_label("f", "Hz"))
        ax.set_ylabel(axis_label("X", r"$\Omega$"))
        ax.grid(True, which="major")
        c.facts.update(
            {"L_H": L, "C_F": C, "R_ohm": R, "f_equal_Hz": f_x, "X_at_f_equal_ohm": math.sqrt(L / C)}
        )
    return c.figure
