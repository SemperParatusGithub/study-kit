"""Two conflicting payments reach two honest computers in opposite order (made-up delays)."""

from studykit.figures import axis_label, color, plot

# Illustrative transit times in ms; the chapter's example quotes the same values.
ARRIVALS = {
    "T1": {"A": 40, "B": 210},
    "T2": {"A": 190, "B": 60},
}
LANES = {"A": 2.0, "Alice": 1.0, "B": 0.0}

ALT = (
    "Timing diagram with time in milliseconds on the horizontal axis and three lanes: node A "
    "at the top, Alice in the middle, node B at the bottom. At time 0 Alice sends two "
    "conflicting payments, T1 as solid arrows and T2 as dashed arrows. Node A receives T1 "
    "after 40 ms and T2 after 190 ms, so it sees T1 first. Node B receives T2 after 60 ms and "
    "T1 after 210 ms, so it sees T2 first. The delays are made up for the illustration."
)


def build():
    with plot.custom(alt=ALT, size="full") as c:
        ax = c.ax
        fg, muted = color("fg"), color("muted")
        styles = {"T1": ("-", color(0)), "T2": ("--", color(1))}

        for y in LANES.values():
            ax.plot([-5, 240], [y, y], color=muted, linewidth=0.8, zorder=1)

        for name, arrivals in ARRIVALS.items():
            style, col = styles[name]
            for node, t in arrivals.items():
                y = LANES[node]
                ax.annotate(
                    "",
                    xy=(t, y),
                    xytext=(0, LANES["Alice"]),
                    arrowprops={"arrowstyle": "-|>", "color": col, "linestyle": style, "linewidth": 1.4},
                    zorder=2,
                )
                ax.plot([t], [y], marker="o", markersize=4, color=col, zorder=3)
                below = y < LANES["Alice"]
                ax.annotate(
                    f"{name}, {t} ms",
                    xy=(t, y),
                    xytext=(0, -11 if below else 9),
                    textcoords="offset points",
                    ha="center",
                    va="top" if below else "bottom",
                    color=fg,
                    fontsize=8,
                )
                c.facts[f"{name}_at_{node}_ms"] = t

        ax.text(246, LANES["A"], "sees T1 first", ha="left", va="center", color=fg, fontsize=8)
        ax.text(246, LANES["B"], "sees T2 first", ha="left", va="center", color=fg, fontsize=8)
        ax.text(246, LANES["Alice"], "sends both at 0 ms", ha="left", va="center", color=fg, fontsize=8)

        ax.set_xlim(-5, 310)
        ax.set_ylim(-0.55, 2.55)
        ax.set_yticks(list(LANES.values()))
        ax.set_yticklabels(["node A", "Alice", "node B"])
        ax.set_xticks([0, 50, 100, 150, 200, 250])
        ax.set_xlabel(axis_label("t", "ms"))
        ax.grid(False)
        ax.plot([], [], "-", color=styles["T1"][1], label="T1: Alice pays Bob")
        ax.plot([], [], "--", color=styles["T2"][1], label="T2: Alice pays Carol")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.2), ncol=2, frameon=False, fontsize=8)

        c.facts["gap_A_ms"] = ARRIVALS["T2"]["A"] - ARRIVALS["T1"]["A"]
        c.facts["gap_B_ms"] = ARRIVALS["T1"]["B"] - ARRIVALS["T2"]["B"]
    return c.figure
