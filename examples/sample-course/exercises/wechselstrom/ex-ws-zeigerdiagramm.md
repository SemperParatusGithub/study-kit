---
id: ex-ws-zeigerdiagramm
title: Zeigerdiagramm einer RC-Reihenschaltung
topic: wechselstrom
difficulty: 1
kind: sketch
minutes: 10
answers:
  - {key: UR, label: 'Teilspannung $U_R$', value: 2.2, unit: V, rtol: 5.0e-3}
  - {key: UC, label: 'Teilspannung $U_C$', value: 3.3, unit: V, rtol: 5.0e-3}
  - {key: U, label: 'Gesamtspannung $U$', value: 3.9661, unit: V, rtol: 5.0e-3}
  - {key: phi, label: 'Nullphase $\varphi_u$ der Gesamtspannung', value: -56.31, unit: °, atol: 0.5}
---

Durch die Reihenschaltung aus $R = 220\,\Omega$ und einem Kondensator mit dem
Blindwiderstand $X_C = 330\,\Omega$ fließt der Strom $\underline{I} = 10\,\mathrm{mA}$ mit
der Nullphase $0^\circ$.

**a)** Berechnen Sie die Effektivwerte $U_R$ und $U_C$ der Teilspannungen.

**b)** Zeichnen Sie das Zeigerdiagramm mit $\underline{I}$, $\underline{U}_R$,
$\underline{U}_C$ und der Gesamtspannung $\underline{U}$.

**c)** Lesen Sie Betrag $U$ und Nullphase $\varphi_u$ der Gesamtspannung ab und prüfen Sie
beides rechnerisch.

::: hint
Am Widerstand sind Strom und Spannung in Phase; am Kondensator eilt die Spannung dem Strom
um eine Viertelperiode nach.
:::

::: hint
Legen Sie $\underline{I}$ auf die reelle Achse und setzen Sie $\underline{U}_C$ an die
Spitze von $\underline{U}_R$.
:::

::: solution
**a)** $U_R = I R = 10\,\mathrm{mA} \cdot 220\,\Omega = 2{,}2\,\mathrm{V}$ und
$U_C = I X_C = 10\,\mathrm{mA} \cdot 330\,\Omega = 3{,}3\,\mathrm{V}$.

**b)** $\underline{I}$ liegt als Bezugszeiger auf der positiven reellen Achse; seine Länge
folgt einem eigenen Maßstab, weil er eine andere Einheit hat. $\underline{U}_R$ ist mit dem
Strom in Phase und zeigt ebenfalls nach rechts, $\underline{U}_C$ von seiner Spitze aus
senkrecht nach unten; $\underline{U}$ verbindet den Ursprung mit der Spitze von
$\underline{U}_C$.

![Zeigerdiagramm mit dem Strom als Bezugszeiger: Die Teilspannungen 2,2 V und 3,3 V ergeben die Gesamtspannung 3,97 V bei −56,3°](fig:ws-zeiger-rc)

**c)** $\underline{U} = (2{,}2 - \mathrm{j}\,3{,}3)\,\mathrm{V}$, also

$$
U = \sqrt{2{,}2^2 + 3{,}3^2}\,\mathrm{V} \approx 3{,}97\,\mathrm{V}, \qquad \varphi_u = -\arctan\frac{3{,}3}{2{,}2} \approx -56{,}3^\circ
$$
:::
