---
id: ex-st-unbelastet
title: Unbelasteter Spannungsteiler
topic: spannungsteiler
difficulty: 1
kind: compute
minutes: 8
answers:
  - {key: I, label: 'Strom $I$', value: 2.5, unit: mA, rtol: 5.0e-3}
  - {key: U2, label: 'Teilspannung $U_2$', value: 8.25, unit: V, rtol: 5.0e-3}
  - {key: U1, label: 'Teilspannung $U_1$', value: 3.75, unit: V, rtol: 5.0e-3}
---

Ein Spannungsteiler aus $R_1 = 1{,}5\,\mathrm{k\Omega}$ und $R_2 = 3{,}3\,\mathrm{k\Omega}$
liegt an der Gleichspannung $U_0 = 12\,\mathrm{V}$. Der Ausgang ist unbelastet.

![Unbelasteter Spannungsteiler an 12 V aus 1,5 kΩ und 3,3 kΩ](fig:st-teiler-12v)

**a)** Berechnen Sie den Strom $I$.

**b)** Berechnen Sie die Spannung $U_2$ über $R_2$ mit der Spannungsteilerregel.

**c)** Wie groß ist $U_1$? Prüfen Sie Ihr Ergebnis mit der Maschenregel.

::: hint
In der Reihenschaltung fließt durch $R_1$ und $R_2$ derselbe Strom.
:::

::: hint
Der Gesamtwiderstand der Reihenschaltung ist $R_1 + R_2 = 4{,}8\,\mathrm{k\Omega}$.
:::

::: solution
**a)** $I = \frac{U_0}{R_1 + R_2} = \frac{12\,\mathrm{V}}{4{,}8\,\mathrm{k\Omega}} = 2{,}5\,\mathrm{mA}$

**b)** $U_2 = U_0 \cdot \frac{R_2}{R_1 + R_2} = 12\,\mathrm{V} \cdot \frac{3{,}3}{4{,}8} = 8{,}25\,\mathrm{V}$

**c)** $U_1 = I \cdot R_1 = 2{,}5\,\mathrm{mA} \cdot 1{,}5\,\mathrm{k\Omega} = 3{,}75\,\mathrm{V}$.
Maschenregel: $U_1 + U_2 = 3{,}75\,\mathrm{V} + 8{,}25\,\mathrm{V} = 12\,\mathrm{V} = U_0$.
:::
