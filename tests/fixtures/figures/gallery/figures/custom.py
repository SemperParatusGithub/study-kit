import numpy as np

from studykit.figures import axis_label, plot


def build():
    t = np.linspace(0, 5e-3, 400)
    u = 10 * (1 - np.exp(-t / 1e-3))
    with plot.custom(alt="Ladekurve eines Kondensators mit tau = 1 ms") as c:
        c.ax.plot(t * 1e3, u)
        c.ax.set_xlabel(axis_label("t", "ms"))
        c.ax.set_ylabel(axis_label("u_C", "V"))
        c.facts["u_end"] = float(u[-1])
    return c.figure
