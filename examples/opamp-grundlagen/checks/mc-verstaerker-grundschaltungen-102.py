from studykit.check import mc_numeric

Ue = 2.4
mc_numeric(
    correct=Ue,
    options={"A": 2.4, "B": -2.4, "C": 0.0, "D": 1.2},
    mistakes={"B": -Ue, "C": 0.0, "D": Ue / 2},
    method="follower V = 1",
)
