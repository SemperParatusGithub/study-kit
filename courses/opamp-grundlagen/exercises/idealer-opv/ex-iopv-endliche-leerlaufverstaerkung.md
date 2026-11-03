---
id: ex-iopv-endliche-leerlaufverstaerkung
title: Nichtinvertierender Verstärker mit endlicher Leerlaufverstärkung
topic: idealer-opv
difficulty: 2
kind: compute
minutes: 14
source: {doc: altes-uebungsblatt02-scan, page: 1, relation: adapted}
answers:
  - {key: k, label: 'Rückkopplungsfaktor $k$', value: 0.042254, rtol: 5.0e-3}
  - {key: Vid, label: 'Ideale Verstärkung $1/k$', value: 23.667, rtol: 5.0e-3}
  - {key: V, label: 'Verstärkung $V$ mit $V_0 = 500$', value: 22.597, rtol: 5.0e-3}
  - {key: F, label: 'Relativer Fehler $F$ gegenüber $1/k$', value: 4.5194, unit: '%', rtol: 5.0e-3}
  - {key: Ua, label: 'Ausgangsspannung $U_a$', value: 3.3896, unit: V, rtol: 5.0e-3}
  - {key: Ud, label: 'Differenzspannung $U_d$', value: 6.7791, unit: mV, rtol: 5.0e-3}
---

Ein nichtinvertierender Verstärker ist mit $R_1 = 3\,\mathrm{k\Omega}$ (vom
invertierenden Eingang nach Masse) und $R_2 = 68\,\mathrm{k\Omega}$ (vom Ausgang zum
invertierenden Eingang) aufgebaut. Bei der verwendeten Signalfrequenz hat der OPV nur noch
die Leerlaufverstärkung $V_0 = 500$. Die Sättigung spielt keine Rolle.

![Nichtinvertierender Verstärker mit R1 = 3 kΩ nach Masse und R2 = 68 kΩ in der Rückführung](fig:idealer-opv-nichtinv-3k-68k)

**a)** Berechnen Sie den Rückkopplungsfaktor $k$.

**b)** Welche Verstärkung $1/k$ hätte die Schaltung mit einem idealen OPV?

**c)** Berechnen Sie die Verstärkung $V$ mit $V_0 = 500$.

**d)** Um wie viel Prozent ist $V$ kleiner als der ideale Wert?

**e)** Am Eingang liegt $U_e = 0.15\,\mathrm{V}$. Berechnen Sie die Ausgangsspannung $U_a$
und die Differenzspannung $U_d$ zwischen den Eingängen.

::: hint
Der Spannungsteiler aus $R_2$ und $R_1$ führt den Anteil $k$ von $U_a$ auf den
invertierenden Eingang zurück.
:::

::: hint
Setzen Sie $U_p = U_e$ und $U_n = k U_a$ in $U_a = V_0 (U_p - U_n)$ ein und lösen Sie nach
$U_a/U_e$ auf.
:::

::: hint
Die Schleifenverstärkung $k V_0$ ist hier nur etwa 21, also nicht sehr groß gegen 1.
:::

::: solution
**a)** $k = \frac{R_1}{R_1 + R_2} = \frac{3\,\mathrm{k\Omega}}{71\,\mathrm{k\Omega}} \approx 0.04225$

**b)** $\frac{1}{k} = \frac{71}{3} = 1 + \frac{R_2}{R_1} \approx 23.67$

**c)** Mit $U_a = V_0 (U_e - k U_a)$ folgt $V = V_0/(1 + k V_0)$. Die
Schleifenverstärkung ist $k V_0 = 500 \cdot 3/71 \approx 21.13$:

$$
V = \frac{500}{1 + 21.13} \approx 22.60
$$

**d)** $F = \frac{1/k - V}{1/k} = \frac{1}{1 + k V_0} = \frac{1}{22.13} \approx 0.0452 = 4.52\,\%$

**e)** $U_a = V \cdot U_e = 22.60 \cdot 0.15\,\mathrm{V} \approx 3.39\,\mathrm{V}$ und

$$
U_d = \frac{U_a}{V_0} = \frac{3.39\,\mathrm{V}}{500} \approx 6.78\,\mathrm{mV}
$$

Bei so kleinem $V_0$ ist $U_d$ nicht mehr vernachlässigbar: Die Regel $U_p = U_n$ setzt
eine große Schleifenverstärkung voraus. Mit $V_0 = 10^5$ wäre der Fehler nur rund
$0.02\,\%$.
:::
