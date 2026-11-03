# Integrator R = 39k, C = 330n, +-11 V, Ue = 0.6 V from t = 0, Ua(0) = 0: simulate the ODE.
import numpy as np
from scipy.integrate import solve_ivp

from studykit.check import answers

R, C, Ue, Usat = 39e3, 330e-9, 0.6, 11.0
sol = solve_ivp(lambda t, y: [-Ue / (R * C)], (0, 0.4), [0.0], max_step=1e-4, dense_output=True)
t = np.linspace(0, 0.4, 400001)
ua = sol.sol(t)[0]
slope = (ua[1000] - ua[0]) / (t[1000] - t[0])
tsat = np.interp(-Usat, ua[::-1], t[::-1])
w = 2 * np.pi * np.logspace(-1, 3, 200001)
mag = np.abs(-1 / (1j * w * R * C))
f1 = np.interp(1.0, mag[::-1], (w / (2 * np.pi))[::-1])
answers(
    slope=slope,
    tsat=tsat * 1e3,
    f1=f1,
    H40=abs(-1 / (1j * 2 * np.pi * 40 * R * C)),
    method="numeric ODE integration and frequency sweep",
)
