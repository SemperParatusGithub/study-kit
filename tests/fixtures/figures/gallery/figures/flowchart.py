from studykit.figures import graph


def build():
    return graph.flowchart(
        [
            ("start", "start", "Start"),
            ("read", "io", "Messwert lesen"),
            ("check", "decision", "$U > U_{max}$?"),
            ("alarm", "process", "Alarm setzen"),
            ("end", "end", "Ende"),
        ],
        [
            ("start", "read"),
            ("read", "check"),
            ("check", "end", "nein"),
            ("check", "alarm", "ja"),
            ("alarm", "read"),
        ],
    )
