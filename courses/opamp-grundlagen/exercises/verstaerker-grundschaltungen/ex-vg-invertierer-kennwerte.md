---
id: ex-vg-invertierer-kennwerte
title: Kennwerte eines invertierenden Verstärkers
topic: verstaerker-grundschaltungen
difficulty: 1
kind: compute
minutes: 8
source: {doc: uebung03-opv-grundschaltungen, page: 1, relation: adapted}
answers:
  - {key: V, label: 'Spannungsverstärkung $V$', value: -3.9706, rtol: 5.0e-3}
  - {key: Ua, label: 'Ausgangsspannung $U_a$', value: -1.3897, unit: V, rtol: 5.0e-3}
  - {key: Rein, label: 'Eingangswiderstand $R_\mathrm{ein}$', value: 6.8, unit: kΩ, rtol: 5.0e-3}
  - {key: Ie, label: 'Eingangsstrom $I_e$', value: 51.471, unit: µA, rtol: 5.0e-3}
---

Ein idealer OPV ist als invertierender Verstärker beschaltet, mit
$R_1 = 6.8\,\mathrm{k\Omega}$ und $R_2 = 27\,\mathrm{k\Omega}$. Am Eingang liegt
$U_e = 0.35\,\mathrm{V}$; der Ausgang ist nicht in der Sättigung.

![Invertierender Verstärker mit R1 im Eingangszweig und R2 im Rückkopplungszweig](fig:verstaerker-grundschaltungen-invertierer)

**a)** Stellen Sie die Knotengleichung am invertierenden Eingang auf und berechnen Sie die
Spannungsverstärkung $V = U_a/U_e$.

**b)** Wie groß ist die Ausgangsspannung $U_a$?

**c)** Welchen Eingangswiderstand $R_\mathrm{ein}$ sieht die Signalquelle?

**d)** Welcher Strom $I_e$ fließt in die Schaltung?

::: hint
Der nichtinvertierende Eingang liegt auf Masse; bei Gegenkopplung ist deshalb auch
$U_n = 0$ (virtuelle Masse), und in den OPV fließt kein Strom.
:::

::: hint
Die Summe der Ströme durch $R_1$ und $R_2$ in den Knoten am invertierenden Eingang ist null:
$U_e/R_1 + U_a/R_2 = 0$.
:::

::: solution
**a)** Mit $U_n = 0$ und $I_n = 0$:

$$
\frac{U_e}{R_1} + \frac{U_a}{R_2} = 0 \quad\Rightarrow\quad V = -\frac{R_2}{R_1} = -\frac{27\,\mathrm{k\Omega}}{6.8\,\mathrm{k\Omega}} \approx -3.971
$$

**b)** $U_a = V \cdot U_e \approx -3.971 \cdot 0.35\,\mathrm{V} \approx -1.390\,\mathrm{V}$. Der
Ausgang ist gegenphasig zum Eingang.

**c)** Die Quelle sieht $R_1$ gegen die virtuelle Masse: $R_\mathrm{ein} = R_1 = 6.8\,\mathrm{k\Omega}$.

**d)** $I_e = U_e/R_1 = 0.35\,\mathrm{V}/6.8\,\mathrm{k\Omega} \approx 51.47\,\mathrm{\mu A}$.
Derselbe Strom fließt durch $R_2$ weiter zum Ausgang.
:::
