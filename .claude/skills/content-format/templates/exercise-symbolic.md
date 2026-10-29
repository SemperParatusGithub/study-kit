---
id: ex-st-vorlage
title: Belasteter Teiler allgemein
topic: spannungsteiler
difficulty: 3
kind: derive
minutes: 12
answers:
  - {key: U2, label: 'Ausgangsspannung $U_2$ als Formel in $U_0$, $R_1$, $R_2$ und $R_\mathrm{L}$', expr: 'U0*R2*RL/(R1*R2 + R1*RL + R2*RL)', symbols: [U0, R1, R2, RL]}
---

Ein Spannungsteiler aus $R_1$ und $R_2$ liegt an $U_0$. Parallel zu $R_2$ ist der
Lastwiderstand $R_\mathrm{L}$ angeschlossen.

![Belasteter Spannungsteiler: Der Lastwiderstand liegt parallel zum unteren Teilerwiderstand](fig:st-teiler-last)

**a)** Leiten Sie $U_2$ als Funktion von $U_0$, $R_1$, $R_2$ und $R_\mathrm{L}$ her.

**b)** Zeigen Sie, dass für $R_\mathrm{L} \to \infty$ die Regel des unbelasteten Teilers
herauskommt.

::: hint
Ersetzen Sie $R_2$ durch $R_2 \parallel R_\mathrm{L}$.
:::

::: solution
**a)** Mit $R_2 \parallel R_\mathrm{L} = R_2 R_\mathrm{L}/(R_2 + R_\mathrm{L})$:

$$
U_2 = U_0 \cdot \frac{R_2 R_\mathrm{L}}{R_1 R_2 + R_1 R_\mathrm{L} + R_2 R_\mathrm{L}}
$$

**b)** Zähler und Nenner durch $R_\mathrm{L}$ teilen; für $R_\mathrm{L} \to \infty$ bleibt
$U_2 = U_0 \cdot R_2/(R_1 + R_2)$.
:::
