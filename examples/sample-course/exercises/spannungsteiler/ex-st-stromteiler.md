---
id: ex-st-stromteiler
title: Stromteiler
topic: spannungsteiler
difficulty: 2
kind: compute
minutes: 10
answers:
  - {key: I1, label: 'Teilstrom $I_1$', value: 30, unit: mA, rtol: 5.0e-3}
  - {key: I2, label: 'Teilstrom $I_2$', value: 20, unit: mA, rtol: 5.0e-3}
  - {key: U, label: 'Spannung $U$ an der Parallelschaltung', value: 6.6, unit: V, rtol: 5.0e-3}
---

Eine ideale Stromquelle mit $I_0 = 50\,\mathrm{mA}$ speist die Parallelschaltung aus
$R_1 = 220\,\Omega$ und $R_2 = 330\,\Omega$.

![Stromteiler: Eine Stromquelle speist zwei parallel geschaltete Widerstände](fig:st-stromteiler)

**a)** Berechnen Sie den Teilstrom $I_1$ durch $R_1$.

**b)** Berechnen Sie den Teilstrom $I_2$ durch $R_2$.

**c)** Welche Spannung $U$ liegt an der Parallelschaltung?

::: hint
An beiden Widerständen liegt dieselbe Spannung. Deshalb verhalten sich die Ströme umgekehrt
wie die Widerstände.
:::

::: hint
In der Stromteilerregel steht im Zähler der Widerstand des jeweils anderen Zweigs.
:::

::: solution
**a)** $I_1 = I_0 \cdot \frac{R_2}{R_1 + R_2} = 50\,\mathrm{mA} \cdot \frac{330}{550} = 30\,\mathrm{mA}$

**b)** $I_2 = I_0 \cdot \frac{R_1}{R_1 + R_2} = 50\,\mathrm{mA} \cdot \frac{220}{550} = 20\,\mathrm{mA}$.
Kontrolle mit der Knotenregel: $I_1 + I_2 = 50\,\mathrm{mA} = I_0$.

**c)** $U = I_1 R_1 = 30\,\mathrm{mA} \cdot 220\,\Omega = 6{,}6\,\mathrm{V}$; ebenso
$I_2 R_2 = 20\,\mathrm{mA} \cdot 330\,\Omega = 6{,}6\,\mathrm{V}$.
:::
