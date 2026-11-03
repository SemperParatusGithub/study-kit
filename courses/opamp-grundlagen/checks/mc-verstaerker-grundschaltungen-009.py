from studykit.check import mc_numeric

U0, Ri, RL = 2.5, 39e3, 4.7e3
mc_numeric(
    correct=U0 * RL / (Ri + RL),
    options={"A": 2.5, "B": 2.231, "C": 0.3013, "D": 0.2689},
    mistakes={"A": U0, "B": U0 * Ri / (Ri + RL), "C": U0 * RL / Ri},
    method="voltage divider Ri-RL",
)
