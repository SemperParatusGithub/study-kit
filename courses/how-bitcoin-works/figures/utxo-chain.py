"""Outputs and the inputs that spend them across three transactions; what stays is the UTXO set."""

from matplotlib.patches import FancyArrowPatch, Rectangle

from studykit.figures import color, plot

ALT = (
    "Three transactions from left to right, each a column with its outputs. Transaction A has an "
    "output of 0.5 BTC locked to Alice, already spent. Transaction B has an input that points at "
    "that output, signed by Alice, and two outputs: 0.3 BTC locked to Bob, already spent, and "
    "0.1999 BTC locked to Alice, unspent. Transaction C has an input that points at Bob's output, "
    "signed by Bob, and two outputs: 0.25 BTC locked to Carol and 0.0498 BTC locked to Bob, both "
    "unspent. The three unspent outputs have a thick border. They are the UTXOs: Alice's balance "
    "is 0.1999 BTC, Bob's 0.0498 BTC and Carol's 0.25 BTC. Reading the arrows backwards leads from "
    "any output through a chain of signatures to where the coins came from."
)

COL_W = 3.1
ROW_H = 1.0
FEE_B = round(0.5 - 0.3 - 0.1999, 8)
FEE_C = round(0.3 - 0.25 - 0.0498, 8)


def cell(ax, x, y, lines, *, unspent=False, spent=False):
    """One input or output row whose lower left corner is (x, y)."""
    fg, muted = color("fg"), color("muted")
    ax.add_patch(
        Rectangle((x, y), COL_W, ROW_H, fill=False, edgecolor=color(0) if unspent else muted,
                  lw=2.2 if unspent else 0.9, linestyle="--" if spent else "-")
    )
    ax.text(x + COL_W / 2, y + 0.70, lines[0], ha="center", va="center", color=fg)
    ax.text(x + COL_W / 2, y + 0.30, lines[1], ha="center", va="center", color=muted)


def link(ax, start, end):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=10, lw=1.1,
                                 color=color("fg"), shrinkA=0, shrinkB=0,
                                 connectionstyle="arc3,rad=0"))


def build():
    with plot.custom(alt=ALT, size="full") as c:
        ax = c.ax
        ax.set_xlim(0, 11.4)
        ax.set_ylim(-0.1, 4.2)
        ax.set_aspect("auto")
        ax.axis("off")

        xs = [0.05, 4.15, 8.25]
        for x, name in zip(xs, ["Transaction A", "Transaction B", "Transaction C"]):
            ax.text(x + COL_W / 2, 3.95, name, ha="center", va="center", color=color("fg"))

        # Transaction A: its only output is spent by B.
        cell(ax, xs[0], 2.3, ["0.5 BTC to Alice", "output, spent"], spent=True)

        # Transaction B
        cell(ax, xs[1], 2.3, ["Input", "signed by Alice"])
        cell(ax, xs[1], 1.15, ["0.3 BTC to Bob", "output, spent"], spent=True)
        cell(ax, xs[1], 0.0, ["0.1999 BTC to Alice", "output, UTXO"], unspent=True)

        # Transaction C
        cell(ax, xs[2], 2.3, ["Input", "signed by Bob"])
        cell(ax, xs[2], 1.15, ["0.25 BTC to Carol", "output, UTXO"], unspent=True)
        cell(ax, xs[2], 0.0, ["0.0498 BTC to Bob", "output, UTXO"], unspent=True)

        link(ax, (xs[0] + COL_W, 2.8), (xs[1], 2.8))
        link(ax, (xs[1] + COL_W, 1.65), (xs[2], 2.8))

        c.facts["utxos_btc"] = {"Alice": 0.1999, "Bob": 0.0498, "Carol": 0.25}
        c.facts["fees_btc"] = {"B": FEE_B, "C": FEE_C}
    return c.figure
