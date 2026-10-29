"""Cheat-sheet sketch: magnitude of RC low-pass and high-pass over f/f_g with asymptotes."""

import numpy as np

from studykit.figures import color, plot

ALT = (
    "Betragsgang von RC-Tiefpass und RC-Hochpass in dB über der normierten Frequenz f/fg "
    "von 0,01 bis 100, mit gestrichelten Asymptoten. Beide Kurven gehen bei f = fg durch "
    "-3 dB; der Tiefpass fällt darüber mit 20 dB pro Dekade, der Hochpass steigt darunter "
    "mit 20 dB pro Dekade."
)


def build():
    x = np.logspace(-2, 2, 400)
    tp = 20 * np.log10(1 / np.sqrt(1 + x**2))
    hp = 20 * np.log10(x / np.sqrt(1 + x**2))
    dashed = {"lw": 0.8, "ls": (0, (3, 2)), "zorder": 3}
    with plot.custom(alt=ALT, size="cs") as c:
        ax = c.ax
        ax.semilogx(x, tp, color=color(0), label="TP", zorder=4)
        ax.semilogx(x, hp, color=color(1), label="HP", zorder=4)
        ax.semilogx(x, np.minimum(0, -20 * np.log10(x)), color=color(0), **dashed)
        ax.semilogx(x, np.minimum(0, 20 * np.log10(x)), color=color(1), **dashed)
        ax.plot([1], [-3.0103], "o", ms=2.5, color=color("fg"), zorder=5)
        ax.set_xlim(1e-2, 1e2)
        ax.set_ylim(-42, 5)
        ax.set_yticks([0, -20, -40])
        ax.set_xlabel(r"$f/f_\mathrm{g}$", labelpad=1)
        ax.set_ylabel("dB", labelpad=1)
        ax.legend(loc="lower center", ncols=2, handlelength=1.2, fontsize=6)
        ax.tick_params(labelsize=6)
        c.facts.update({"db_at_fg": -3.0103, "slope_db_per_decade": 20})
    return c.figure
