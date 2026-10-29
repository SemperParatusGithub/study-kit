---
id: ex-st-belastet
title: Belasteter Spannungsteiler
topic: spannungsteiler
difficulty: 2
kind: compute
minutes: 12
answers:
  - {key: Rp, label: 'Ersatzwiderstand $R_2 \parallel R_\mathrm{L}$', value: 1.65, unit: kΩ, rtol: 5.0e-3}
  - {key: U2, label: 'Ausgangsspannung $U_2$ mit Last', value: 6.2857, unit: V, rtol: 5.0e-3}
  - {key: drop, label: 'Rückgang von $U_2$ gegenüber dem Leerlauf', value: 23.81, unit: '%', rtol: 1.0e-2}
  - {key: IL, label: 'Laststrom $I_\mathrm{L}$', value: 1.9048, unit: mA, rtol: 5.0e-3}
---

Der Spannungsteiler aus der Übung [Unbelasteter Spannungsteiler](ex:ex-st-unbelastet)
mit $U_0 = 12\,\mathrm{V}$, $R_1 = 1{,}5\,\mathrm{k\Omega}$ und
$R_2 = 3{,}3\,\mathrm{k\Omega}$ wird nun mit dem Lastwiderstand
$R_\mathrm{L} = 3{,}3\,\mathrm{k\Omega}$ belastet. Im Leerlauf lieferte er
$U_2 = 8{,}25\,\mathrm{V}$.

![Belasteter Spannungsteiler an 12 V aus 1,5 kΩ und 3,3 kΩ mit einer Last von 3,3 kΩ](fig:st-teiler-12v-last)

**a)** Berechnen Sie den Ersatzwiderstand $R_2 \parallel R_\mathrm{L}$.

**b)** Berechnen Sie die Ausgangsspannung $U_2$ mit Last.

**c)** Um wie viel Prozent sinkt $U_2$ gegenüber dem Leerlauf?

**d)** Welcher Strom $I_\mathrm{L}$ fließt durch die Last?

::: hint
Die Last liegt parallel zu $R_2$. In der Teilerregel tritt die Parallelschaltung an die
Stelle von $R_2$.
:::

::: hint
Zwei gleich große Widerstände parallel ergeben den halben Widerstandswert.
:::

::: solution
**a)** $R_2 \parallel R_\mathrm{L} = \frac{R_2 R_\mathrm{L}}{R_2 + R_\mathrm{L}} = \frac{3{,}3 \cdot 3{,}3}{3{,}3 + 3{,}3}\,\mathrm{k\Omega} = 1{,}65\,\mathrm{k\Omega}$

**b)** Teilerregel mit dem Ersatzwiderstand:

$$
U_2 = U_0 \cdot \frac{R_2 \parallel R_\mathrm{L}}{R_1 + R_2 \parallel R_\mathrm{L}} = 12\,\mathrm{V} \cdot \frac{1{,}65}{3{,}15} \approx 6{,}29\,\mathrm{V}
$$

**c)** $\frac{8{,}25\,\mathrm{V} - 6{,}286\,\mathrm{V}}{8{,}25\,\mathrm{V}} \approx 0{,}238$, also sinkt
$U_2$ um rund $23{,}8\,\%$.

**d)** $I_\mathrm{L} = \frac{U_2}{R_\mathrm{L}} = \frac{6{,}286\,\mathrm{V}}{3{,}3\,\mathrm{k\Omega}} \approx 1{,}90\,\mathrm{mA}$.
Durch $R_2$ fließt derselbe Strom, weil $R_2 = R_\mathrm{L}$ ist.
:::
