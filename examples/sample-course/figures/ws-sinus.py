"""A sinusoidal voltage with amplitude, RMS value and period marked (summary)."""

import math

import numpy as np

from studykit.figures import axis_label, color, plot

U_HAT, F = 10.0, 1e3  # 10 V amplitude at 1 kHz
ALT = (
    "Verlauf der Sinusspannung u(t) = 10 V cos(2π · 1 kHz · t) über zwei Perioden von "
    "0 bis 2 ms. Markiert sind die Amplitude 10 V, der Effektivwert 7,07 V als gestrichelte "
    "Linie und die Periodendauer T = 1 ms zwischen zwei Maxima."
)


def build():
    t = np.linspace(0, 2 / F, 801)
    u = U_HAT * np.cos(2 * math.pi * F * t)
    u_eff = U_HAT / math.sqrt(2)
    t_ms = t * 1e3
    with plot.custom(alt=ALT) as c:
        ax = c.ax
        ax.plot(t_ms, u, color=color(0), zorder=4)
        ax.axhline(0, color=color("fg"), lw=0.7, zorder=2)
        ax.axhline(u_eff, color=color(1), lw=1.0, ls=(0, (4, 2)), zorder=3)
        ax.annotate(
            rf"$U \approx {u_eff:.2f}\,\mathrm{{V}}$".replace(".", "{,}"),
            (0.5, u_eff),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
            color=color(1),
        )
        # amplitude: arrow from the axis to the second maximum
        ax.annotate(
            "",
            (1.0, U_HAT),
            xytext=(1.0, 0),
            arrowprops={
                "arrowstyle": "<|-|>",
                "color": color("fg"),
                "lw": 0.8,
                "shrinkA": 0,
                "shrinkB": 0,
                "mutation_scale": 7,
            },
        )
        ax.annotate(
            r"$\hat{u}$",
            (1.0, U_HAT / 2),
            xytext=(-3, 0),
            textcoords="offset points",
            ha="right",
            va="center",
            fontsize=9,
        )
        # period: between the minima at 0.5 ms and 1.5 ms
        y_t = -U_HAT * 1.12
        ax.annotate(
            "",
            (1.5, y_t),
            xytext=(0.5, y_t),
            arrowprops={
                "arrowstyle": "<|-|>",
                "color": color("fg"),
                "lw": 0.8,
                "shrinkA": 0,
                "shrinkB": 0,
                "mutation_scale": 7,
            },
        )
        ax.annotate(
            "$T$",
            (1.0, y_t),
            xytext=(0, 2),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
        )
        ax.set_xlim(0, 2)
        ax.set_ylim(-U_HAT * 1.3, U_HAT * 1.2)
        ax.set_xlabel(axis_label("t", "ms"))
        ax.set_ylabel(axis_label("u", "V"))
        c.facts.update({"u_hat_V": U_HAT, "f_Hz": F, "T_ms": 1e3 / F, "U_eff_V": u_eff})
    return c.figure
