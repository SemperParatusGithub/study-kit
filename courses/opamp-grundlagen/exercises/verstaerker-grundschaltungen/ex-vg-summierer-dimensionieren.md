---
id: ex-vg-summierer-dimensionieren
title: Gewichteten Summierer dimensionieren
topic: verstaerker-grundschaltungen
difficulty: 3
kind: compute
minutes: 15
answers:
  - {key: R1, label: 'Eingangswiderstand $R_1$', value: 10, unit: kΩ, rtol: 5.0e-3}
  - {key: R2, label: 'Eingangswiderstand $R_2$', value: 40, unit: kΩ, rtol: 5.0e-3}
  - {key: Ua1, label: '$U_a$ für $U_1 = 1.2\,\mathrm{V}$ und $U_2 = -3\,\mathrm{V}$', value: -0.9, unit: V, rtol: 5.0e-3}
  - {key: Ua2, label: '$U_a$ für $U_1 = 3.5\,\mathrm{V}$ und $U_2 = 8\,\mathrm{V}$', value: -10, unit: V, rtol: 5.0e-3}
---

Ein Summierer mit idealem OPV und zwei Eingängen soll

$$
U_a = -\left( 2 \cdot U_1 + 0.5 \cdot U_2 \right)
$$

bilden. Der Rückkopplungswiderstand ist $R_F = 20\,\mathrm{k\Omega}$, der Ausgang ist auf
$\pm 10\,\mathrm{V}$ begrenzt.

**a)** Bestimmen Sie die Eingangswiderstände $R_1$ und $R_2$.

**b)** Berechnen Sie $U_a$ für $U_1 = 1.2\,\mathrm{V}$ und $U_2 = -3\,\mathrm{V}$.

**c)** Welche Ausgangsspannung stellt sich für $U_1 = 3.5\,\mathrm{V}$ und
$U_2 = 8\,\mathrm{V}$ ein?

::: hint
Jeder Eingang hat das Gewicht $-R_F/R_i$.
:::

::: hint
Prüfen Sie jedes Ergebnis gegen die Ausgangsgrenze, bevor Sie es angeben.
:::

::: solution
**a)** Aus $U_a = -R_F \cdot (U_1/R_1 + U_2/R_2)$ folgen die Gewichte $R_F/R_1 = 2$ und
$R_F/R_2 = 0.5$:

$$
R_1 = \frac{R_F}{2} = 10\,\mathrm{k\Omega}, \qquad R_2 = \frac{R_F}{0.5} = 40\,\mathrm{k\Omega}
$$

**b)** $U_a = -(2 \cdot 1.2\,\mathrm{V} + 0.5 \cdot (-3\,\mathrm{V})) = -(2.4\,\mathrm{V} - 1.5\,\mathrm{V}) = -0.9\,\mathrm{V}$

**c)** Rechnerisch $U_a = -(7\,\mathrm{V} + 4\,\mathrm{V}) = -11\,\mathrm{V}$. Das liegt jenseits
der Grenze; der Ausgang bleibt bei $U_a = -10\,\mathrm{V}$ (Sättigung), und die virtuelle
Masse gilt nicht mehr.
:::
