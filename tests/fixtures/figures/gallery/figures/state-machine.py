from studykit.figures import graph


def build():
    return graph.state_machine(
        ["S0", "S1", "S2"],
        [("S0", "S1", "1/0"), ("S1", "S2", "1/0"), ("S2", "S0", "1/1"), ("S1", "S0", "0/0")],
        initial="S0",
        kind="mealy",
    )
