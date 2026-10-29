---
id: ex-ws-impedanz-rc
title: Impedanz einer RC-Reihenschaltung
topic: wechselstrom
difficulty: 2
kind: compute
minutes: 12
answers:
  - {key: Xc, label: 'Blindwiderstand $X_C$ (Betrag)', value: 79.577, unit: Ω, rtol: 5.0e-3}
  - {key: Z, label: 'Betrag $|\underline{Z}|$', value: 127.80, unit: Ω, rtol: 5.0e-3}
  - {key: phi, label: 'Winkel $\varphi$ der Impedanz', value: -38.51, unit: °, atol: 0.5}
  - {key: I, label: 'Strom $I$ (Effektivwert)', value: 78.248, unit: mA, rtol: 5.0e-3}
---

Ein Widerstand $R = 100\,\Omega$ und ein Kondensator $C = 10\,\mathrm{\mu F}$ liegen in Reihe
an einer Sinusspannung mit dem Effektivwert $U = 10\,\mathrm{V}$ und der Frequenz
$f = 200\,\mathrm{Hz}$.

**a)** Berechnen Sie den Betrag $X_C$ des Blindwiderstands des Kondensators.

**b)** Geben Sie die Impedanz $\underline{Z}$ in algebraischer Form an und berechnen Sie
Betrag und Winkel.

**c)** Welcher Strom $I$ fließt? Eilt er der Spannung vor oder nach?

::: hint
Der Kondensator hat die Impedanz $1/(\mathrm{j}\omega C)$. In Reihe addieren sich die
Impedanzen.
:::

::: hint
Schreiben Sie $\underline{Z} = R - \mathrm{j}X_C$. Den Betrag liefert der Satz des
Pythagoras, den Winkel $\arctan(\mathrm{Im}/\mathrm{Re})$.
:::

::: solution
**a)** $X_C = \frac{1}{2\pi f C} = \frac{1}{2\pi \cdot 200\,\mathrm{Hz} \cdot 10\,\mathrm{\mu F}} \approx 79{,}6\,\Omega$

**b)** $\underline{Z} = R - \mathrm{j}X_C \approx (100 - \mathrm{j}\,79{,}6)\,\Omega$ mit

$$
|\underline{Z}| = \sqrt{100^2 + 79{,}6^2}\,\Omega \approx 127{,}8\,\Omega, \qquad \varphi = -\arctan\frac{79{,}6}{100} \approx -38{,}5^\circ
$$

**c)** $I = \frac{U}{|\underline{Z}|} = \frac{10\,\mathrm{V}}{127{,}8\,\Omega} \approx 78{,}2\,\mathrm{mA}$.
Wegen $\varphi = \varphi_u - \varphi_i < 0$ eilt der Strom der Spannung um $38{,}5^\circ$
vor: Die Schaltung verhält sich ohmsch-kapazitiv.
:::
