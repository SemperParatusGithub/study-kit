# Non-inverting, R1 = 1k, R2 = 19k, V0 = 1e4: relative gain error vs 1/k.
from studykit.check import mc_numeric

k, V0 = 1e3 / 20e3, 1e4
F = 1 / (1 + k * V0)
mc_numeric(
    correct=F,
    options={"A": 1e-4, "B": 0.05, "C": 2e-5, "D": 2e-3},
    mistakes={"A": 1 / V0, "B": k, "C": F / 100},
    method="F = 1/(1 + k V0); distractors: 1/V0, k, percent applied twice",
)
