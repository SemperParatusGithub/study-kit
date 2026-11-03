from studykit.check import mc_numeric

RF, w = 47e3, 4.0
mc_numeric(
    correct=RF / w,
    options={"A": 188e3, "B": 1.175e3, "C": 15.67e3, "D": 11.75e3},
    mistakes={"A": RF * w, "B": RF / w / 10, "C": RF / (w - 1)},
    method="weight -RF/R1 = -4: R1 = RF/4",
)
