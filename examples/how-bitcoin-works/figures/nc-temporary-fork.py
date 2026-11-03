"""A temporary fork in two moments: a tie at height 101, then block B wins and A goes stale."""

from matplotlib.patches import Rectangle

from studykit.figures import color, plot

ALT = (
    "Two moments of a temporary fork. Left, a tie: blocks 101 A and 101 B both build on "
    "block 100, and each node mines on the one it saw first. Right, the tie is broken: "
    "block 102 builds on 101 B, so every node switches to the chain with 100, 101 B and "
    "102. Block 101 A, drawn dashed, is now stale and its transactions go back to the "
    "mempool unless the winning chain already holds them."
)

W, H = 1.5, 0.72


def box(ax, x, y, text, *, stale=False):
    ax.add_patch(
        Rectangle(
            (x, y),
            W,
            H,
            fill=False,
            edgecolor=color("muted") if stale else color(0),
            linestyle=(0, (4, 2)) if stale else "solid",
            lw=1.1,
        )
    )
    ax.text(
        x + W / 2,
        y + H / 2,
        text,
        ha="center",
        va="center",
        fontsize=8,
        color=color("muted") if stale else color("fg"),
    )


def link(ax, left, right, *, stale=False):
    """Join the right edge of the block at `left` to the left edge of the block at `right`."""
    ax.plot(
        [left[0] + W, right[0]],
        [left[1] + H / 2, right[1] + H / 2],
        color=color("muted") if stale else color("fg"),
        lw=1.0,
        linestyle=(0, (4, 2)) if stale else "solid",
    )


def build():
    gap = 0.45
    upper, middle, lower = 1.3, 0.75, 0.2
    with plot.custom(alt=ALT, size="full") as c:
        ax = c.ax
        ax.set_axis_off()

        # Left panel: the tie.
        x0 = 0.0
        x1 = x0 + W + gap
        box(ax, x0, middle, "Block 100")
        box(ax, x1, upper, "Block 101 A")
        box(ax, x1, lower, "Block 101 B")
        link(ax, (x0, middle), (x1, upper))
        link(ax, (x0, middle), (x1, lower))
        ax.text(x0, 2.3, "Tie", fontsize=9, fontweight="bold", va="bottom")
        ax.text(x0, 2.28, "each node mines on the block it saw first", fontsize=8, va="top")

        # Right panel: the tie is broken.
        x2 = x1 + W + 0.95
        x3 = x2 + W + gap
        x4 = x3 + W + gap
        box(ax, x2, middle, "Block 100")
        box(ax, x3, upper, "Block 101 A\nstale", stale=True)
        box(ax, x3, lower, "Block 101 B")
        box(ax, x4, lower, "Block 102")
        link(ax, (x2, middle), (x3, upper), stale=True)
        link(ax, (x2, middle), (x3, lower))
        link(ax, (x3, lower), (x4, lower))
        ax.text(x2, 2.3, "Tie broken", fontsize=9, fontweight="bold", va="bottom")
        ax.text(x2, 2.28, "every node switches to the chain with more work", fontsize=8, va="top")
        ax.text(
            x3 + W + 0.12,
            upper + H / 2,
            "its transactions go\nback to the mempool",
            fontsize=8,
            va="center",
            color=color("muted"),
        )

        ax.set_xlim(-0.05, x4 + W + 0.05)
        ax.set_ylim(0.05, 2.65)
        c.facts["blocks_left"] = ["100", "101 A", "101 B"]
        c.facts["blocks_right"] = ["100", "101 A (stale)", "101 B", "102"]
    return c.figure
