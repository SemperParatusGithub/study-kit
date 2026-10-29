"""Normalised step response of the RC element of ex-rc-sprungantwort: tau = 47 ms."""

from studykit.figures import plot

ALT = (
    "Sprungantwort h(t) eines RC-Glieds mit der Zeitkonstante 47 ms: Die Kurve steigt "
    "exponentiell von 0 gegen den Endwert 1. Markiert sind der Endwert und die "
    "Anstiegszeit von 10 auf 90 Prozent, rund 103 ms."
)


def build():
    tau = 10e3 * 4.7e-6
    return plot.step_response(f"1/(1 + {tau!r}*s)", annotate=("final", "rise"), alt=ALT)
