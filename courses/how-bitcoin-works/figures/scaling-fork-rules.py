"""Which blocks old and new software accept, in a soft fork and in a hard fork."""

from matplotlib.patches import Circle

from studykit.figures import color, plot

ALT = (
    "Two diagrams of the sets of blocks that software accepts as valid. Soft fork, on the left: "
    "the blocks valid under the new rules form a small circle inside the large circle of blocks "
    "valid under the old rules, so a new block is accepted by old and new nodes alike. Hard fork, "
    "on the right: the blocks valid under the old rules form the small circle inside the large "
    "circle of blocks valid under the new rules, and a new block can lie outside the old circle, "
    "so old nodes reject it."
)


def _panel(ax, cx, title, outer, inner, outer_col, inner_col, block_y, note_dy):
    fg, muted = color("fg"), color("muted")
    ax.text(cx, 2.42, title, ha="center", va="center", fontsize=10, fontweight="bold", color=fg)
    ax.add_patch(Circle((cx, 0), 2.0, fill=False, edgecolor=outer_col, linewidth=1.6))
    ax.add_patch(Circle((cx, -0.55), 1.15, fill=False, edgecolor=inner_col, linewidth=1.6))
    ax.text(cx, 1.58, outer, ha="center", va="center", fontsize=8, color=fg)
    ax.text(cx, -0.1, inner, ha="center", va="center", fontsize=8, color=fg)
    ax.plot(cx, block_y, marker="s", markersize=6, color=fg, linestyle="none")
    ax.text(cx, block_y + note_dy, "new block", ha="center", va="center", fontsize=8, color=muted)


def build():
    old, new = color(0), color(1)
    with plot.custom(alt=ALT, size="full") as c:
        ax = c.ax
        _panel(ax, -2.6, "Soft fork", "valid under old rules", "valid under\nnew rules",
               old, new, -0.85, -0.3)
        _panel(ax, 2.6, "Hard fork", "valid under new rules", "valid under\nold rules",
               new, old, 0.86, 0.3)
        ax.set_xlim(-4.9, 4.9)
        ax.set_ylim(-2.25, 2.7)
        ax.set_aspect("equal")
        ax.axis("off")
        c.facts["soft_fork_new_block_old_nodes"] = "accept"
        c.facts["hard_fork_new_block_old_nodes"] = "reject"
    return c.figure
