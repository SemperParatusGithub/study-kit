"""Phasor diagram of the mock exam task pk1-t2: R = 1 kΩ, C = 220 nF, U = 10 V at 1 kHz.

The current is the reference phasor on the positive real axis, drawn to its own scale just
beside the axis; U_R and U_C are chained head to tail, their sum U runs from the origin.
"""

import cmath
import math

from matplotlib.patches import Arc, FancyArrowPatch

from studykit.figures import color, fmt_number, plot

R, X = 1e3, -1 / (2 * math.pi * 1e3 * 220e-9)  # X_C at 1 kHz, capacitive
I_A = 10.0 / math.hypot(R, X)
U_X, PHI = r"\underline{U}_C", r"\varphi"
ALT = (
    "Zeigerdiagramm der RC-Reihenschaltung aus der Probeklausur: Der Strom I = 8,10 mA liegt "
    "als Bezugszeiger auf der positiven reellen Achse. UR = 8,10 V zeigt in dieselbe "
    "Richtung, UC = 5,86 V von dessen Spitze senkrecht nach unten. Die Summe U = 10 V eilt "
    "dem Strom um 35,9 Grad nach."
)


def arrow(ax, z0, z1, col, lw, scale, zorder=5):
    ax.add_patch(
        FancyArrowPatch(
            (z0.real, z0.imag),
            (z1.real, z1.imag),
            arrowstyle="-|>",
            mutation_scale=scale,
            color=col,
            lw=lw,
            shrinkA=0,
            shrinkB=0,
            zorder=zorder,
        )
    )


def label(ax, tex, at, direction, col, dist=6.0, size=9):
    """Text placed `dist` points from `at` in `direction`, anchored on the near side."""
    d = direction / abs(direction)
    ha = "left" if d.real > 0.35 else "right" if d.real < -0.35 else "center"
    va = "bottom" if d.imag > 0.35 else "top" if d.imag < -0.35 else "center"
    ax.annotate(
        f"${tex}$",
        (at.real, at.imag),
        xytext=(dist * d.real, dist * d.imag),
        textcoords="offset points",
        ha=ha,
        va=va,
        fontsize=size,
        color=col,
        zorder=7,
    )


def build():
    u_r = complex(I_A * R)
    u_x = 1j * I_A * X
    u = u_r + u_x
    phi = math.degrees(cmath.phase(u))
    side = 1.0 if X > 0 else -1.0  # the triangle lies above (L) or below (C) the real axis
    span = max(abs(u_r), abs(u_x))
    pad = 0.2 * span
    x0, x1 = -pad, u_r.real + pad
    y0, y1 = min(0.0, u.imag) - pad, max(0.0, u.imag) + pad
    fg = color("fg")
    with plot.custom(alt=ALT) as c:
        ax = c.ax
        # Widen (or heighten) the box to the figure's shape so equal scaling fills it.
        w_in, h_in = c.fig.get_size_inches()
        target = (w_in - 0.1) / (h_in - 0.1)
        if (x1 - x0) / (y1 - y0) < target:
            grow = (y1 - y0) * target - (x1 - x0)
            x0, x1 = x0 - grow / 2, x1 + grow / 2
        else:
            grow = (x1 - x0) / target - (y1 - y0)
            y0, y1 = y0 - grow / 2, y1 + grow / 2
        ax.set_axis_off()
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_aspect("equal", adjustable="box")
        arrow(ax, complex(x0, 0), complex(x1, 0), fg, 0.8, 8, 2)
        arrow(ax, complex(0, y0), complex(0, y1), fg, 0.8, 8, 2)
        label(ax, r"\mathrm{Re}", complex(x1, 0), complex(-0.5, -1), fg, 4, 8)
        label(ax, r"\mathrm{Im}", complex(0, y1), complex(-1, -0.5), fg, 4, 8)

        # Reference current: own scale, beside the axis on the side away from the triangle.
        i0 = complex(0, -side * 0.07 * span)
        i1 = i0 + 0.45 * abs(u_r)
        arrow(ax, i0, i1, color(2), 1.2, 9)
        label(ax, r"\underline{I}", i1, 1, color(2), 3)

        arrow(ax, 0j, u_r, color(0), 1.6, 10)
        arrow(ax, u_r, u, color(1), 1.6, 10)
        arrow(ax, 0j, u, fg, 2.0, 11, 6)
        label(ax, r"\underline{U}_R", 0.8 * u_r, complex(0, side), color(0), 4)
        label(ax, U_X, u_r + u_x / 2, 1, color(1))
        normal = 1j * u / abs(u)
        if (normal.conjugate() * (u_r - u / 2)).real > 0:  # point away from the triangle
            normal = -normal
        label(ax, r"\underline{U}", u / 2, normal, fg, 7)

        radius = 0.3 * abs(u)
        a0, a1 = sorted((0.0, phi))
        ax.add_patch(Arc((0, 0), 2 * radius, 2 * radius, theta1=a0, theta2=a1, color=fg, lw=0.8))
        mid = cmath.exp(1j * math.radians(phi / 2))
        label(ax, rf"{PHI} = {fmt_number(phi)}^\circ", radius * mid, mid, fg, 3, 7)
        c.facts.update(
            {
                "I_A": I_A,
                "I_angle_deg": 0.0,
                "R_ohm": R,
                "X_ohm": X,
                "U_R_V": abs(u_r),
                "U_X_V": abs(u_x),
                "U_V": abs(u),
                "phi_u_deg": phi,
                "current_drawn_to_own_scale": True,
            }
        )
    return c.figure
