---
id: ex-vg-invertierer-saettigung
title: Invertierender Verstärker mit Sättigung und Innenwiderstand
topic: verstaerker-grundschaltungen
difficulty: 4
kind: compute
minutes: 24
source: {doc: klausur-ws2025-26, page: 2, relation: inspired}
answers:
  - {key: V, label: 'Spannungsverstärkung $V$', value: -6.9231, rtol: 5.0e-3}
  - {key: Ua1, label: '$U_a$ für $U_e = 0.6\,\mathrm{V}$', value: -4.1538, unit: V, rtol: 5.0e-3}
  - {key: Ua2, label: '$U_a$ für $U_e = -1.8\,\mathrm{V}$', value: 10, unit: V, rtol: 5.0e-3}
  - {key: Uemax, label: 'Größter Betrag $U_{e,\mathrm{max}}$ im linearen Bereich', value: 1.4444, unit: V, rtol: 5.0e-3}
  - {key: VU0, label: 'Verstärkung $U_a/U_0$ mit Innenwiderstand', value: -5.2941, rtol: 5.0e-3}
---

Ein invertierender Verstärker besteht aus einem idealen OPV mit
$R_1 = 3.9\,\mathrm{k\Omega}$ und $R_2 = 27\,\mathrm{k\Omega}$. Die Ausgangsspannung ist auf
$\pm 10\,\mathrm{V}$ begrenzt.

![Invertierender Verstärker mit R1 im Eingangszweig und R2 im Rückkopplungszweig](fig:verstaerker-grundschaltungen-invertierer)

**a)** Leiten Sie $V = U_a/U_e$ mit den Regeln des idealen OPV her.

**b)** Berechnen Sie $V$.

**c)** Berechnen Sie $U_a$ für $U_e = 0.6\,\mathrm{V}$.

**d)** Welche Ausgangsspannung stellt sich für $U_e = -1.8\,\mathrm{V}$ ein? Begründen Sie.

**e)** Bis zu welchem Betrag der Eingangsspannung arbeitet die Schaltung linear?

**f)** Die Eingangsspannung kommt aus einer Quelle mit Innenwiderstand
$R_i = 1.2\,\mathrm{k\Omega}$. Wie groß ist die Verstärkung $U_a/U_0$ bezogen auf die
Leerlaufspannung $U_0$ der Quelle?

::: hint
Nennen Sie zuerst die beiden Regeln ($I_n = 0$, $U_d = 0$) und was daraus für $U_n$ folgt.
:::

::: hint
Prüfen Sie bei d), ob der rechnerische Wert $V \cdot U_e$ innerhalb der Ausgangsgrenze liegt.
:::

::: hint
Bei f) liegt $R_i$ in Reihe zu $R_1$.
:::

::: solution
**a)** Bei Gegenkopplung im linearen Betrieb gilt $I_n = 0$ und $U_d = 0$. Da $U_p = 0$ ist,
liegt auch $U_n = 0$ (virtuelle Masse). Die Knotenregel am invertierenden Eingang ergibt

$$
\frac{U_e}{R_1} + \frac{U_a}{R_2} = 0 \quad\Rightarrow\quad V = \frac{U_a}{U_e} = -\frac{R_2}{R_1}
$$

**b)** $V = -27\,\mathrm{k\Omega}/3.9\,\mathrm{k\Omega} \approx -6.923$

**c)** $U_a = -6.923 \cdot 0.6\,\mathrm{V} \approx -4.154\,\mathrm{V}$; das liegt innerhalb von
$\pm 10\,\mathrm{V}$.

**d)** Rechnerisch $U_a = -6.923 \cdot (-1.8\,\mathrm{V}) \approx 12.46\,\mathrm{V}$. Das
überschreitet die Grenze, der Ausgang geht in die positive Sättigung:
$U_a = +10\,\mathrm{V}$. Die virtuelle Masse gilt dann nicht mehr.

**e)** $|U_e|_\mathrm{max} = 10\,\mathrm{V}/6.923 \approx 1.444\,\mathrm{V}$

**f)** $R_i$ und $R_1$ liegen in Reihe vor der virtuellen Masse:

$$
\frac{U_a}{U_0} = -\frac{R_2}{R_1 + R_i} = -\frac{27\,\mathrm{k\Omega}}{5.1\,\mathrm{k\Omega}} \approx -5.294
$$
:::
