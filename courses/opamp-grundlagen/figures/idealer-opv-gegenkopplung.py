"""Block diagram of negative feedback: forward gain V0, feedback factor k (summary)."""

from studykit.figures import block

ALT = (
    "Wirkungsplan der Gegenkopplung: Die Eingangsspannung Ue führt auf eine Summierstelle, "
    "an der die zurückgeführte Spannung k·Ua abgezogen wird. Die Differenz Ud = Ue - k·Ua "
    "wird mit der Leerlaufverstärkung V0 zur Ausgangsspannung Ua verstärkt; der "
    "Rückkopplungszweig mit dem Faktor k führt Ua auf die Summierstelle zurück."
)


def build():
    return block.feedback_loop(
        forward=("V_0",),
        feedback="k",
        signals={"r": "U_e", "e": "U_d", "y": "U_a", "m": "k U_a"},
        alt=ALT,
    )
