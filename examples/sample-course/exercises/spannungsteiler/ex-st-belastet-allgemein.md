---
id: ex-st-belastet-allgemein
title: Belasteter Teiler allgemein
topic: spannungsteiler
difficulty: 3
kind: derive
minutes: 15
answers:
  - {key: U2, label: 'Ausgangsspannung $U_2$ als Formel in $U_0$, $R_1$, $R_2$ und $R_\mathrm{L}$', expr: 'U0*R2*RL/(R1*R2 + R1*RL + R2*RL)', symbols: [U0, R1, R2, RL]}
  - {key: RLmin, label: 'Kleinster zulässiger Lastwiderstand $R_\mathrm{L,min}$', value: 9.5, unit: kΩ, rtol: 5.0e-3}
---

Ein Spannungsteiler aus $R_1$ und $R_2$ liegt an $U_0$. Parallel zu $R_2$ ist der
Lastwiderstand $R_\mathrm{L}$ angeschlossen.

![Belasteter Spannungsteiler mit der Last RL parallel zu R2](fig:st-teiler-last)

**a)** Leiten Sie $U_2$ als Funktion von $U_0$, $R_1$, $R_2$ und $R_\mathrm{L}$ her.
Geben Sie das Ergebnis als einen Bruch ohne Doppelbruch an.

**b)** Zeigen Sie, dass für $R_\mathrm{L} \to \infty$ die Teilerregel des unbelasteten
Teilers herauskommt.

**c)** Es sei $R_1 = R_2 = 1\,\mathrm{k\Omega}$. Wie groß muss $R_\mathrm{L}$ mindestens
sein, damit $U_2$ höchstens $5\,\%$ unter der Leerlaufspannung liegt?

::: hint
Ersetzen Sie $R_2$ durch $R_2 \parallel R_\mathrm{L}$ und erweitern Sie Zähler und Nenner
mit $R_2 + R_\mathrm{L}$.
:::

::: hint
Mit $R_1 = R_2 = R$ vereinfacht sich das Teilerverhältnis zu
$U_2/U_0 = R_\mathrm{L}/(R + 2R_\mathrm{L})$.
:::

::: hint
Die Leerlaufspannung ist $U_0/2$. Setzen Sie $U_2 \geq 0{,}95 \cdot U_0/2$ an und lösen Sie
nach $R_\mathrm{L}$ auf.
:::

::: solution
**a)** Mit $R_2 \parallel R_\mathrm{L} = R_2 R_\mathrm{L}/(R_2 + R_\mathrm{L})$:

$$
U_2 = U_0 \cdot \frac{\frac{R_2 R_\mathrm{L}}{R_2 + R_\mathrm{L}}}{R_1 + \frac{R_2 R_\mathrm{L}}{R_2 + R_\mathrm{L}}} = U_0 \cdot \frac{R_2 R_\mathrm{L}}{R_1 R_2 + R_1 R_\mathrm{L} + R_2 R_\mathrm{L}}
$$

**b)** Zähler und Nenner durch $R_\mathrm{L}$ teilen:

$$
U_2 = U_0 \cdot \frac{R_2}{R_1 R_2/R_\mathrm{L} + R_1 + R_2} \;\to\; U_0 \cdot \frac{R_2}{R_1 + R_2} \quad \text{für } R_\mathrm{L} \to \infty
$$

**c)** Mit $R_1 = R_2 = R$:

$$
\frac{R_\mathrm{L}}{R + 2R_\mathrm{L}} \geq 0{,}475 \quad \Rightarrow \quad 0{,}05\,R_\mathrm{L} \geq 0{,}475\,R \quad \Rightarrow \quad R_\mathrm{L} \geq 9{,}5\,R = 9{,}5\,\mathrm{k\Omega}
$$

Gegenprobe mit der Ersatzspannungsquelle: $R_\mathrm{i} = R/2 = 0{,}5\,\mathrm{k\Omega}$,
und die Last senkt die Spannung um
$R_\mathrm{i}/(R_\mathrm{i} + R_\mathrm{L}) = 0{,}5/(0{,}5 + 9{,}5) = 5\,\%$.
:::
