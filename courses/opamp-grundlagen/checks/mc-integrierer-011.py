from studykit.check import mc_numeric

RC, Usat, Ua0, Ue = 1e-3, 10.0, -2.0, 0.4
slope = -Ue / RC  # V/s, falls towards -Usat
mc_numeric(
    correct=(-Usat - Ua0) / slope,
    options={"A": 25e-3, "B": 30e-3, "C": 20e-3, "D": 50e-3},
    mistakes={"A": Usat / -slope, "B": (Usat - Ua0) / -slope, "D": 2 * Usat / -slope},
    method="Ua0 + slope t = -Usat; start ignored, wrong direction, full swing",
)
