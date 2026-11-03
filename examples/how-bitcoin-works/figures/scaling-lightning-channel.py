"""A payment channel: two transactions on the chain, any number of states between them."""

from matplotlib.patches import FancyArrowPatch, Rectangle

from studykit.figures import color, plot

ALT = (
    "Timeline of a payment channel between Alice and Bob with two rows. The lower row is the "
    "blockchain, a line of blocks. An opening transaction in one block locks 0.1 BTC in a "
    "2-of-2 multisignature output; a closing transaction in a later block pays out the last "
    "balances. The upper row, off the chain, shows the signed states that are not published: "
    "state 1 with Alice 0.06 and Bob 0.04 BTC, state 2 with 0.05 and 0.05 BTC, and state 3 with "
    "0.052 and 0.048 BTC. Only state 3 is valid to publish at the close."
)

STATES = [
    (2.55, "State 1", "Alice 0.06\nBob 0.04"),
    (5.0, "State 2", "Alice 0.05\nBob 0.05"),
    (7.45, "State 3", "Alice 0.052\nBob 0.048"),
]


def _arrow(ax, start, end, col, style="-|>", dashed=False):
    ax.add_patch(
        FancyArrowPatch(start, end, arrowstyle=style, mutation_scale=9, linewidth=1.1, color=col,
                        linestyle="--" if dashed else "-", shrinkA=0, shrinkB=0)
    )


def build():
    fg, muted = color("fg"), color("muted")
    with plot.custom(alt=ALT, size="full") as c:
        ax = c.ax

        # Off the chain: the signed states.
        ax.text(8.6, 2.67, "Off the chain\n(signed, not\npublished)", ha="left", va="center",
                fontsize=8, color=muted)
        box_w, box_h = 1.75, 0.95
        for x, name, text in STATES:
            ax.add_patch(Rectangle((x - box_w / 2, 2.2), box_w, box_h, fill=False,
                                   edgecolor=color(0), linewidth=1.3))
            ax.text(x, 3.33, name, ha="center", va="center", fontsize=8, color=fg)
            ax.text(x, 2.67, text, ha="center", va="center", fontsize=8, color=fg)
        for (x0, _, _), (x1, _, _) in zip(STATES, STATES[1:]):
            _arrow(ax, (x0 + box_w / 2 + 0.03, 2.67), (x1 - box_w / 2 - 0.03, 2.67), fg)

        # On the chain: a row of blocks with the two transactions.
        ax.text(4.63, -0.72, "On the chain", ha="center", va="center", fontsize=8, color=muted)
        size = 0.42
        xs = [0.45 + 0.76 * i for i in range(13)]
        open_i, close_i = 2, 11
        for i, x in enumerate(xs):
            on_tx = i in (open_i, close_i)
            ax.add_patch(Rectangle((x - size / 2, -size / 2), size, size, fill=False,
                                   edgecolor=color(1) if on_tx else muted,
                                   linewidth=1.8 if on_tx else 0.9))
            if i:
                ax.plot([xs[i - 1] + size / 2, x - size / 2], [0, 0], color=muted, linewidth=0.9)

        x_open, x_close = xs[open_i], xs[close_i]
        _arrow(ax, (x_open, size / 2 + 0.03), (STATES[0][0] - 0.3, 2.17), fg)
        _arrow(ax, (STATES[2][0] + 0.3, 2.17), (x_close, size / 2 + 0.03), fg)
        ax.text(x_open, -0.72, "Open: lock 0.1 BTC\nin a 2-of-2 output", ha="center", va="center",
                fontsize=8, color=fg)
        ax.text(x_close, -0.72, "Close: pay out\nthe last state", ha="center", va="center",
                fontsize=8, color=fg)

        ax.set_xlim(-0.1, 10.2)
        ax.set_ylim(-1.15, 3.6)
        ax.axis("off")
        c.facts["capacity_btc"] = 0.1
        c.facts["states_btc"] = [[0.06, 0.04], [0.05, 0.05], [0.052, 0.048]]
    return c.figure
