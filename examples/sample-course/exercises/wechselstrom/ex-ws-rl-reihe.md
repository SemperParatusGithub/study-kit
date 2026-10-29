---
id: ex-ws-rl-reihe
title: RL-Reihenschaltung am Netz
topic: wechselstrom
difficulty: 2
kind: compute
minutes: 15
answers:
  - {key: XL, label: 'Blindwiderstand $X_L$', value: 31.416, unit: Ω, rtol: 5.0e-3}
  - {key: Z, label: 'Betrag $|\underline{Z}|$', value: 50.862, unit: Ω, rtol: 5.0e-3}
  - {key: phi, label: 'Phasenwinkel $\varphi$', value: 38.15, unit: °, atol: 0.5}
  - {key: I, label: 'Strom $I$ (Effektivwert)', value: 4.522, unit: A, rtol: 5.0e-3}
  - {key: UR, label: 'Teilspannung $U_R$', value: 180.88, unit: V, rtol: 5.0e-3}
  - {key: UL, label: 'Teilspannung $U_L$', value: 142.06, unit: V, rtol: 5.0e-3}
---

Eine Spule mit $L = 100\,\mathrm{mH}$ und ein Widerstand $R = 40\,\Omega$ liegen in Reihe
am Netz mit $U = 230\,\mathrm{V}$ und $f = 50\,\mathrm{Hz}$.

![RL-Reihenschaltung mit R = 40 Ω und L = 100 mH an einer Wechselspannung von 230 V](fig:ws-rl-reihe)

**a)** Berechnen Sie den Blindwiderstand $X_L$ der Spule.

**b)** Berechnen Sie Betrag und Winkel der Impedanz $\underline{Z}$.

**c)** Welcher Strom $I$ fließt?

**d)** Berechnen Sie die Teilspannungen $U_R$ und $U_L$.

**e)** Zeichnen Sie das Zeigerdiagramm mit $\underline{I}$ als Bezugszeiger. Warum ist
$U_R + U_L$ größer als $230\,\mathrm{V}$?

::: hint
Der Strom ist allen Bauteilen gemeinsam und dient als Bezug. Es gilt
$\underline{Z} = R + \mathrm{j}\omega L$.
:::

::: hint
Jede Teilspannung ist der Strom mal dem Betrag der jeweiligen Impedanz. Die Spannung an
der Spule steht senkrecht auf der Spannung am Widerstand.
:::

::: solution
**a)** $X_L = 2\pi f L = 2\pi \cdot 50\,\mathrm{Hz} \cdot 0{,}1\,\mathrm{H} \approx 31{,}4\,\Omega$

**b)** $|\underline{Z}| = \sqrt{40^2 + 31{,}4^2}\,\Omega \approx 50{,}9\,\Omega$ und
$\varphi = \arctan\frac{31{,}4}{40} \approx 38{,}1^\circ$.

**c)** $I = \frac{U}{|\underline{Z}|} = \frac{230\,\mathrm{V}}{50{,}9\,\Omega} \approx 4{,}52\,\mathrm{A}$

**d)** $U_R = I R \approx 180{,}9\,\mathrm{V}$ und $U_L = I X_L \approx 142{,}1\,\mathrm{V}$.

**e)** $\underline{U}_R$ liegt in Richtung von $\underline{I}$, $\underline{U}_L$ ist um
$90^\circ$ gedreht. Die Zeiger addieren sich geometrisch:
$\sqrt{180{,}9^2 + 142{,}1^2}\,\mathrm{V} \approx 230\,\mathrm{V}$. Die algebraische Summe
der Beträge, rund $323\,\mathrm{V}$, hat keine physikalische Bedeutung.

![Zeigerdiagramm: UR = 180,9 V und UL = 142,1 V ergeben U = 230 V bei 38,1°](fig:ws-zeiger-rl-230v)
:::
