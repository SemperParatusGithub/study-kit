"""Alice's payment: one 0.5 BTC input, two outputs, and a fee that is not an output at all."""

from matplotlib.patches import FancyArrowPatch, Rectangle

from studykit.figures import color, plot

ALT = (
    "One transaction with one input on the left and two outputs on the right. The input spends "
    "Alice's earlier output of 0.5 BTC. Output 0 pays 0.3 BTC to Bob. Output 1 returns 0.1999 BTC "
    "to Alice as change. Below the outputs, a dashed box with no arrow from the transaction marks "
    "the remaining 0.0001 BTC, or 10,000 satoshis: it appears in no output and is the fee that "
    "the miner collects."
)

INPUT_BTC = 0.5
PAY_BTC = 0.3
CHANGE_BTC = 0.1999


def box(ax, x, y, w, h, lines, *, dashed=False):
    """A labelled box with its lower left corner at (x, y); the first line is the heading."""
    fg, muted = color("fg"), color("muted")
    ax.add_patch(
        Rectangle((x, y), w, h, fill=False, edgecolor=muted if dashed else fg, lw=1.0,
                  linestyle="--" if dashed else "-")
    )
    step = 0.42
    top = y + h / 2 + step * (len(lines) - 1) / 2
    for i, line in enumerate(lines):
        ax.text(x + w / 2, top - i * step, line, ha="center", va="center",
                color=muted if i else fg)


def arrow(ax, start, end):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=10, lw=1.1,
                                 color=color("fg"), shrinkA=0, shrinkB=0))


def build():
    with plot.custom(alt=ALT, size="full") as c:
        ax = c.ax
        ax.set_xlim(0, 12)
        ax.set_ylim(0, 5.6)
        ax.set_aspect("auto")
        ax.axis("off")

        box(ax, 0.1, 2.6, 3.1, 1.5, ["Input: 0.5 BTC", "Alice's earlier", "output"])
        box(ax, 4.2, 2.8, 2.2, 1.1, ["Transaction"])
        arrow(ax, (3.2, 3.35), (4.2, 3.35))

        box(ax, 7.6, 3.95, 4.3, 1.5, ["Output 0: 0.3 BTC", "to Bob"])
        box(ax, 7.6, 2.05, 4.3, 1.5, ["Output 1: 0.1999 BTC", "back to Alice (change)"])
        arrow(ax, (6.4, 3.6), (7.6, 4.7))
        arrow(ax, (6.4, 3.1), (7.6, 2.8))

        box(ax, 7.6, 0.15, 4.3, 1.5, ["Left over: 0.0001 BTC", "the fee, not an output"],
            dashed=True)

        c.facts["input_btc"] = INPUT_BTC
        c.facts["outputs_btc"] = [PAY_BTC, CHANGE_BTC]
        c.facts["fee_btc"] = round(INPUT_BTC - PAY_BTC - CHANGE_BTC, 8)
    return c.figure
