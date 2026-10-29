"""Normalised step response of the RC element of ex-rc-sprungantwort: tau = 47 ms.

The transfer function is written with s in 1/ms, so the time axis and the rise-time label
read in milliseconds like the exercise.
"""

from studykit.figures import plot

ALT = (
    "Sprungantwort h(t) eines RC-Glieds mit der Zeitkonstante 47 ms: Die Kurve steigt "
    "exponentiell von 0 gegen den Endwert 1. Markiert sind der Endwert und die "
    "Anstiegszeit von 10 auf 90 Prozent, rund 103 ms."
)


def build():
    tau_ms = 10e3 * 4.7e-6 * 1e3  # R = 10 kΩ, C = 4.7 µF
    return plot.step_response(
        f"1/(1 + {tau_ms!r}*s)", annotate=("final", "rise"), unit="ms", alt=ALT
    )
