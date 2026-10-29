# Check-script recipes

Each recipe is a complete `checks/<id>.py` that ran green with `studykit verify`. They run
with the course directory as working directory and the project's Python (NumPy, SciPy,
SymPy, python-control). Copy the structure, not the numbers: every value comes from the
blind view of your item.

## Contents

- [Nodal analysis (MNA) and the mesh second method](#nodal-analysis-mna)
- [Phasors (complex AC)](#phasors)
- [Laplace and step responses](#laplace-and-step-responses)
- [Stability margins](#stability-margins)
- [Numeric MC questions](#numeric-mc-questions)
- [Conceptual MC questions and items without keys](#conceptual-mc-and-review)

Units: return each value in the unit the blind view names for its key (`I` in mA →
multiply amperes by 1e3), or wrap it as `quantity(value, "A")` in another unit of the same
kind. Angles in degrees when the key says °. Never return a complex number; give the
magnitude, angle or part the key asks for.

## Nodal analysis (MNA)

Bridged T network: U0 = 12 V at node 1, R1 1-2, R2 2-0, R3 2-3, R4 3-0, R5 1-3. Asked:
U2 and the current I3 through R3 from node 2 to node 3 (key unit mA).

```python
# Bridged T network: U0 = 12 V between node 1 and ground, R1 1-2, R2 2-0, R3 2-3, R4 3-0,
# R5 1-3. Asked: U2 (node 2) and the current I3 through R3 (node 2 to node 3).
import numpy as np

from studykit.check import answers

U0 = 12.0
R1, R2, R3, R4, R5 = 1e3, 2.2e3, 470.0, 1e3, 3.3e3
edges = [(1, 2, R1), (2, 0, R2), (2, 3, R3), (3, 0, R4), (1, 3, R5)]
n = 3  # unknown node voltages V1..V3; one voltage source between node 1 and ground
A = np.zeros((n + 1, n + 1))
z = np.zeros(n + 1)
for a, b, R in edges:
    g = 1 / R
    for i, j, s in ((a, a, 1), (b, b, 1), (a, b, -1), (b, a, -1)):
        if i and j:
            A[i - 1, j - 1] += s * g
A[0, n] = A[n, 0] = 1.0  # source current into node 1; V1 = U0
z[n] = U0
x = np.linalg.solve(A, z)
V1, V2, V3 = x[:n]
answers(U2=V2, I3=(V2 - V3) / R3 * 1e3, method="modified nodal analysis, numpy")
```

Second method (`checks/<id>.mesh.py`, run with `--confirm`): mesh currents, exact.

```python
# Second method for mna.py: mesh currents with SymPy, exact.
import sympy as sp

from studykit.check import answers

U0 = sp.Integer(12)
R1, R2, R3, R4, R5 = 1000, 2200, 470, 1000, 3300
Ia, Ib, Ic = sp.symbols("I_a I_b I_c")
# mesh a: U0 -> R1 -> R2 -> ground; mesh b: R2, R3, R4; mesh c: R1, R5, R3
eqs = [
    sp.Eq(R1 * (Ia - Ic) + R2 * (Ia - Ib), U0),
    sp.Eq(R2 * (Ib - Ia) + R3 * (Ib - Ic) + R4 * Ib, 0),
    sp.Eq(R1 * (Ic - Ia) + R5 * Ic + R3 * (Ic - Ib), 0),
]
s = sp.solve(eqs, [Ia, Ib, Ic])
U2 = R2 * (s[Ia] - s[Ib])
I3 = s[Ib] - s[Ic]  # from node 2 to node 3 is the direction of mesh b in R3
answers(U2=sp.N(U2), I3=sp.N(I3) * 1000, method="mesh currents, sympy")
```

Other independent pairs for DC networks: superposition vs. nodal analysis; Thevenin
equivalent (open-circuit voltage and source-free resistance) vs. solving the full network.

## Phasors

RC series circuit at U = 10 V RMS, f = 1 kHz, R = 1 kΩ, C = 220 nF; the voltage is the
reference phasor.

```python
# RC series circuit: U = 10 V RMS, f = 1 kHz, R = 1 kΩ, C = 220 nF.
import cmath
import math

from studykit.check import answers

U, f, R, C = 10.0, 1e3, 1e3, 220e-9
w = 2 * math.pi * f
Zc = 1 / (1j * w * C)
Z = R + Zc
I_ph = U / Z  # U is the reference phasor (angle 0)
answers(
    Xc=abs(Zc),
    Z=abs(Z),
    phi=math.degrees(cmath.phase(Z)),
    I=abs(I_ph) * 1e3,  # key unit mA
    UR=abs(I_ph * R),
    UC=abs(I_ph * Zc),
    method="complex phasors, Python cmath",
)
```

Second method: the same circuit with SymPy (`sp.I`, exact `sp.Abs`, `sp.arg`), or the
power triangle (`P = I² R`, `Q = I² X_C`, `|S| = U I` must agree). RMS vs. amplitude: say in
a comment which one the statement gives and keep it through the whole script.

## Laplace and step responses

RC low-pass with τ = 1 ms driven by a 5 V step: u_C(t) (a symbolic key in t), u_C(1 ms)
and the time to reach 4 V (key unit ms).

```python
# Step response of the RC low-pass, tau = R*C = 1 ms, U0 = 5 V: u_C(t) and the time to 4 V.
import sympy as sp

from studykit.check import answers

s, t = sp.symbols("s t", positive=True)
R, C, U0 = sp.Integer(1000), sp.Rational(1, 10**6), sp.Integer(5)
H = 1 / (1 + s * R * C)
Uc = sp.inverse_laplace_transform(H * U0 / s, s, t)  # step of height U0
(t4,) = sp.solveset(sp.Eq(Uc, 4), t, domain=sp.Interval(0, sp.oo))
answers(
    uC=sp.simplify(Uc),  # a symbolic key in t
    uC1=float(Uc.subs(t, sp.Rational(1, 1000))),
    t4=float(t4) * 1e3,  # key unit ms
    method="Laplace: inverse transform of H(s) U0/s with SymPy",
)
```

Second method: simulate numerically and compare.

```python
# Second method for laplace.py: simulate the step response numerically.
import control
import numpy as np

from studykit.check import answers

tau, U0 = 1e-3, 5.0
G = control.tf([1], [tau, 1])
t = np.linspace(0, 10 * tau, 200001)
_, y = control.step_response(U0 * G, T=t)
# the symbolic key: a candidate expression must match the simulated curve everywhere
uC = "5 - 5*exp(-1000*t)"
assert np.max(np.abs(y - (5 - 5 * np.exp(-1000 * t)))) < 1e-6
answers(
    uC=uC,
    uC1=np.interp(1e-3, t, y),
    t4=np.interp(4.0, y, t) * 1e3,  # y rises monotonically
    method="numeric step simulation with python-control",
)
```

For a symbolic key give a SymPy expression or string in the symbols the blind view lists;
`studykit verify` compares by simplification and at sample points. Partial fractions:
`sp.apart(F, s)`; final value: `sp.limit(s * F, s, 0)` (only for a stable system).

## Stability margins

Open loop G(s) = 10 / (s (s + 1) (s + 10)): gain margin in dB, phase margin in degrees,
gain crossover frequency in rad/s.

```python
# Open loop G(s) = 10 / (s (s + 1) (s + 10)): gain and phase margin, crossover frequency.
import control
import numpy as np
from scipy import optimize, signal

from studykit.check import answers

G = control.tf([10], [1, 11, 10, 0])
gm, pm, wcg, wcp = control.margin(G)

# second method inside the check: brentq on |G(jw)| = 1 and on arg G(jw) = -180 deg
num, den = [10], [1, 11, 10, 0]
mag = lambda w: abs(np.polyval(num, 1j * w) / np.polyval(den, 1j * w))  # noqa: E731
wc = optimize.brentq(lambda w: mag(w) - 1, 1e-3, 1e3)
# arg G = -180 deg where G(jw) is real and negative: Im of the denominator is 0
w180 = optimize.brentq(lambda w: np.polyval(den, 1j * w).imag, 1.0, 10.0)
_, phase = signal.freqresp(signal.lti(num, den), [wc])
assert abs(wc - wcp) < 1e-6 * wcp and abs(w180 - wcg) < 1e-6 * wcg

answers(
    GM=20 * np.log10(gm),  # key unit dB
    PM=pm,  # degrees
    wc=wcp,  # rad/s
    method="python-control margin, cross-checked with brentq",
)
```

`control.margin` returns the gain margin as a factor (`inf` when the phase never reaches
−180°) and the frequencies in rad/s; convert to Hz only when the key says Hz.

## Numeric MC questions

The blind view lists the options in source order A, B, …. Give each option's stated value
in SI units, the correct value, and for each distractor the value of the mistake you think
produced it (the misconception catalogue: a forgotten 2π, √2, dB vs. linear, a power of
ten, series vs. parallel, degrees vs. radians). A distractor you cannot explain stays out
of `mistakes` (that is a warning, not a dispute).

```python
from math import pi

from studykit.check import mc_numeric

R, C = 3.3e3, 10e-9
mc_numeric(
    correct=1 / (2 * pi * R * C),
    options={"A": 30.3e3, "B": 482.0, "C": 4.82e3, "D": 190e3},
    mistakes={"A": 1 / (R * C), "B": 1 / (2 * pi * R * 100e-9), "D": 2 * pi / (R * C)},
    method="fg = 1/(2 pi R C); distractors from the misconception catalogue",
)
```

## Conceptual MC and review

A conceptual question gets `checks/<id>.json`:

```json
{"answer": ["B", "D"], "confidence": "high", "ambiguous": false, "reason": "B: …; D: …"}
```

Kprim: the list of true statements, or `{"A": true, "B": false, "C": true, "D": false}`.
Set `"ambiguous": true` (with the reason) when a statement can be read two ways or two
options are right in a single-choice question: that disputes the question. A script may end
with `mc_answer(["B", "D"], reason="…")` instead when you computed something on the way.

An exercise without answer keys (a sketch, a pure derivation) is checked by deriving the
result yourself from the blind statement; you cannot see its solution. End the script with
`review(agree=True, reason="<your result in one or two lines>")` when the task is
well-posed and solvable as stated, `agree=False` with the reason when it is not
(missing data, contradictory values, two readings). The `/verify` command compares your
`reason` with the item's solution and records a dispute when they differ.
