"""Who keeps the books: one private ledger at a bank against many copies of a public one."""

import math

from matplotlib.patches import FancyBboxPatch

from studykit.figures import color, plot

ALT = (
    "Two ways of keeping a ledger, side by side. Left, a private ledger: four customers are "
    "connected only to a bank in the middle, and only the bank holds the ledger, so every "
    "payment passes through it. Right, a public ledger: six nodes are connected to one "
    "another with no centre, and each of them holds its own full copy of the ledger."
)


def _box(ax, x, y, w, h, *, ledger=False):
    """A rounded box centred on (x, y); a ledger box has a thick edge in the accent colour."""
    ax.add_patch(
        FancyBboxPatch(
            (x - w / 2, y - h / 2),
            w,
            h,
            boxstyle="round,pad=0,rounding_size=0.06",
            facecolor=color("bg"),
            edgecolor=color(0) if ledger else color("fg"),
            linewidth=2.0 if ledger else 1.0,
            zorder=3,
        )
    )


def _holder(ax, x, y, name):
    """A box named `name` with a ledger inside it."""
    fg = color("fg")
    _box(ax, x, y, 0.85, 0.72)
    ax.text(x, y + 0.17, name, ha="center", va="center", color=fg, fontsize=8, zorder=4)
    _box(ax, x, y - 0.14, 0.62, 0.26, ledger=True)
    ax.text(x, y - 0.14, "ledger", ha="center", va="center", color=fg, fontsize=8, zorder=4)


def _ring(cx, cy, r, n, start):
    return [
        (cx + r * math.cos(start + 2 * math.pi * i / n), cy + r * math.sin(start + 2 * math.pi * i / n))
        for i in range(n)
    ]


def build():
    with plot.custom(alt=ALT, size="full") as c:
        ax = c.ax
        ax.set_axis_off()
        ax.set_xlim(0, 8)
        ax.set_ylim(-0.15, 4.0)
        ax.set_aspect("equal")
        fg, muted = color("fg"), color("muted")

        ax.text(1.9, 3.85, "Private ledger", ha="center", va="center", color=fg, fontweight="bold")
        centre = (1.9, 1.75)
        for x, y in _ring(*centre, 1.3, 4, math.pi / 4):
            ax.plot([centre[0], x], [centre[1], y], color=muted, linewidth=1.0, zorder=1)
            _box(ax, x, y, 0.95, 0.38)
            ax.text(x, y, "customer", ha="center", va="center", color=fg, fontsize=8, zorder=4)
        _holder(ax, *centre, "bank")

        ax.text(6.0, 3.85, "Public ledger", ha="center", va="center", color=fg, fontweight="bold")
        nodes = _ring(6.0, 1.75, 1.4, 6, math.pi / 2)
        links = [(i, (i + 1) % 6) for i in range(6)] + [(0, 2), (1, 4), (2, 5), (3, 5)]
        for a, b in links:
            ax.plot(
                [nodes[a][0], nodes[b][0]],
                [nodes[a][1], nodes[b][1]],
                color=muted,
                linewidth=1.0,
                zorder=1,
            )
        for x, y in nodes:
            _holder(ax, x, y, "node")

        c.facts["customers"] = 4
        c.facts["ledger_copies_private"] = 1
        c.facts["ledger_copies_public"] = len(nodes)
    return c.figure
