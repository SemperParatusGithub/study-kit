"""Attacker's catch-up probability P against z for four hash-power shares, log scale."""

from math import exp, log

from studykit.figures import color, plot

ALT = (
    "Chance P that an attacker catches up against the number z of blocks on top of the "
    "payment's block, on a logarithmic axis from 1 down to 0.0000001, for attacker shares "
    "q = 0.1, 0.2, 0.3 and 0.4. All four curves start at P = 1 for z = 0 and fall almost "
    "as straight lines, the steeper the smaller q is. A dashed line marks P = 0.001, "
    "which the curves pass at z = 5, 11, 24 and 89; the last of these lies beyond the "
    "plotted range, which ends at z = 60, where q = 0.4 still has P of about 0.008."
)

SHARES = (0.1, 0.2, 0.3, 0.4)
FLOOR = 1e-7


def catch_up(q: float, z: int) -> float:
    """Finite form of the white paper's sum (p. 7), with the Poisson term built in logs."""
    p = 1 - q
    lam = z * q / p
    total = 1.0
    log_term = -lam
    for k in range(z + 1):
        if k:
            log_term += log(lam / k)
        total -= exp(log_term) * (1 - (q / p) ** (z - k))
    return total


def build():
    with plot.custom(alt=ALT) as c:
        ax = c.ax
        for i, q in enumerate(SHARES):
            zs, ps = [], []
            for z in range(61):
                value = catch_up(q, z)
                if value < FLOOR:
                    break
                zs.append(z)
                ps.append(value)
            ax.plot(zs, ps, color=color(i), zorder=3)
            c.facts[f"q={q}"] = {"last_z": zs[-1], "last_P": ps[-1]}
            ax.annotate(
                f"q = {q}",
                (zs[-1], ps[-1]),
                xytext=(5, 2) if q != 0.4 else (-14, 5),
                textcoords="offset points",
                ha="left",
                va="bottom",
                fontsize=7,
            )
        ax.axhline(1e-3, color=color("muted"), lw=0.9, ls=(0, (4, 2)), zorder=2)
        ax.annotate(
            "P = 0.001",
            (60, 1e-3),
            xytext=(-2, -3),
            textcoords="offset points",
            ha="right",
            va="top",
            fontsize=7,
            color=color("muted"),
        )
        ax.set_yscale("log")
        ax.set_xlim(0, 68)
        ax.set_ylim(FLOOR, 2)
        ax.set_xlabel("Blocks on top of the payment, z")
        ax.set_ylabel("Chance of catching up, P")
    return c.figure
