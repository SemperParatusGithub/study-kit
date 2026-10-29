"""Output voltage of two dividers with the same ratio over the load resistance (summary)."""

import numpy as np

from studykit.figures import axis_label, color, plot

U0 = 10.0
ALT = (
    "Ausgangsspannung U2 zweier Spannungsteiler an U0 = 10 V über dem Lastwiderstand RL "
    "von 100 Ω bis 1 MΩ, logarithmisch aufgetragen. Beide haben R1 = R2 und damit im "
    "Leerlauf 5 V (gestrichelt). Der niederohmige Teiler mit 1 kΩ erreicht die "
    "Leerlaufspannung schon bei viel kleineren Lastwiderständen als der Teiler mit 10 kΩ."
)


def u2(r, r_l):
    """Loaded divider with R1 = R2 = r: U2 = U0 * (r || RL) / (r + r || RL)."""
    p = r * r_l / (r + r_l)
    return U0 * p / (r + p)


def build():
    r_l = np.logspace(2, 6, 400)
    with plot.custom(alt=ALT) as c:
        ax = c.ax
        ax.axhline(U0 / 2, color=color("muted"), lw=1.0, ls=(0, (4, 2)), zorder=2)
        for i, r in enumerate((1e3, 10e3)):
            label = r"$R_1 = R_2 = {}\,\mathrm{{k\Omega}}$".format(int(r / 1e3))
            ax.semilogx(r_l, u2(r, r_l), color=color(i), label=label, zorder=4)
        ax.annotate(
            "Leerlauf",
            (1.2e2, U0 / 2),
            xytext=(0, 3),
            textcoords="offset points",
            ha="left",
            va="bottom",
            fontsize=8,
            color=color("muted"),
        )
        ax.set_xlim(1e2, 1e6)
        ax.set_ylim(0, 6)
        ax.set_xlabel(axis_label(r"R_\mathrm{L}", r"$\Omega$"))
        ax.set_ylabel(axis_label("U_2", "V"))
        ax.legend(loc="lower right")
        c.facts.update(
            {
                "U0_V": U0,
                "U2_open_V": U0 / 2,
                "U2_at_RL_1k_V": {"R_1k": u2(1e3, 1e3), "R_10k": u2(10e3, 1e3)},
                "U2_at_RL_100k_V": {"R_1k": u2(1e3, 1e5), "R_10k": u2(10e3, 1e5)},
            }
        )
    return c.figure
