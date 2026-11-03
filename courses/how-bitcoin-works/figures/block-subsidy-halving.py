"""Step chart of the block subsidy per era, from the halving-schedule chart."""

from studykit.figures import color, plot

# (start year, end year, subsidy in BTC); the years are approximate.
ERAS = [
    (2009, 2012, 50.0),
    (2012, 2016, 25.0),
    (2016, 2020, 12.5),
    (2020, 2024, 6.25),
    (2024, 2028, 3.125),
    (2028, 2032, 1.5625),
]

ALT = (
    "Step chart of the block subsidy, the new bitcoin per block, against the approximate year. "
    "It starts at 50 BTC from 2009 to 2012, then halves at each step: 25 BTC from 2012 to 2016, "
    "12.5 BTC from 2016 to 2020, 6.25 BTC from 2020 to 2024, 3.125 BTC from 2024 to 2028 and "
    "1.5625 BTC from 2028 to 2032. Each step lasts 210,000 blocks, about four years, and each "
    "drop is half the size of the one before."
)


def build():
    with plot.custom(alt=ALT, size="full") as c:
        for i, (start, end, subsidy) in enumerate(ERAS):
            c.ax.plot([start, end], [subsidy, subsidy], color=color(0), linewidth=2)
            if i + 1 < len(ERAS):
                c.ax.plot([end, end], [subsidy, ERAS[i + 1][2]], color=color(0), linewidth=2)
            c.ax.annotate(
                f"{subsidy:g} BTC",
                xy=((start + end) / 2, subsidy),
                xytext=(0, 5),
                textcoords="offset points",
                ha="center",
                va="bottom",
                color=color("fg"),
            )
        c.ax.set_xlim(2008, 2033)
        c.ax.set_ylim(0, 57)
        c.ax.set_xticks(range(2010, 2035, 5))
        c.ax.set_yticks(range(0, 60, 10))
        c.ax.set_xlabel("Year (approximate)")
        c.ax.set_ylabel("New bitcoin per block / BTC")
        c.facts["eras"] = [
            {"start": start, "end": end, "subsidy_btc": subsidy} for start, end, subsidy in ERAS
        ]
    return c.figure
