---
id: ex-vg-summierer-drei-eingaenge
title: Summierer mit drei Eingängen
topic: verstaerker-grundschaltungen
difficulty: 2
kind: compute
minutes: 12
source: {doc: uebung03-opv-grundschaltungen, page: 1, relation: adapted}
answers:
  - {key: I1, label: 'Strom $I_1$ durch $R_1$', value: 31.25, unit: µA, rtol: 5.0e-3}
  - {key: I2, label: 'Strom $I_2$ durch $R_2$', value: -50, unit: µA, rtol: 5.0e-3}
  - {key: I3, label: 'Strom $I_3$ durch $R_3$', value: 31.25, unit: µA, rtol: 5.0e-3}
  - {key: Ua, label: 'Ausgangsspannung $U_a$', value: -0.3, unit: V, rtol: 5.0e-3}
---

Ein Summierer mit idealem OPV hat $R_F = 24\,\mathrm{k\Omega}$, $R_1 = 8\,\mathrm{k\Omega}$,
$R_2 = 12\,\mathrm{k\Omega}$ und $R_3 = 48\,\mathrm{k\Omega}$. An den Eingängen liegen
$U_1 = 0.25\,\mathrm{V}$, $U_2 = -0.6\,\mathrm{V}$ und $U_3 = 1.5\,\mathrm{V}$ (gegen Masse).
Die Ausgangsgrenze ist $\pm 12\,\mathrm{V}$. Die Ströme zählen von den Eingängen zum Knoten
am invertierenden Eingang.

![Summierer mit drei Eingängen: U1, U2 und U3 über R1, R2 und R3 an der virtuellen Masse, Rückkopplung über RF](fig:verstaerker-grundschaltungen-summierer)

**a)** Berechnen Sie die Ströme $I_1$, $I_2$ und $I_3$ in den Knoten.

**b)** Stellen Sie die Knotengleichung auf und berechnen Sie $U_a$.

::: hint
Der Knoten am invertierenden Eingang ist eine virtuelle Masse; jeder Strom hängt nur von
seiner eigenen Eingangsspannung ab.
:::

::: hint
Die Summe der drei Eingangsströme fließt durch $R_F$ zum Ausgang:
$U_a = -R_F \cdot (I_1 + I_2 + I_3)$.
:::

::: solution
**a)** Mit $U_n = 0$:
$I_1 = 0.25\,\mathrm{V}/8\,\mathrm{k\Omega} = 31.25\,\mathrm{\mu A}$,
$I_2 = -0.6\,\mathrm{V}/12\,\mathrm{k\Omega} = -50\,\mathrm{\mu A}$,
$I_3 = 1.5\,\mathrm{V}/48\,\mathrm{k\Omega} = 31.25\,\mathrm{\mu A}$.

**b)** Knotenregel:

$$
\frac{U_1}{R_1} + \frac{U_2}{R_2} + \frac{U_3}{R_3} + \frac{U_a}{R_F} = 0 \quad\Rightarrow\quad U_a = -R_F \cdot (I_1 + I_2 + I_3)
$$

$$
U_a = -24\,\mathrm{k\Omega} \cdot 12.5\,\mathrm{\mu A} = -0.3\,\mathrm{V}
$$

Das liegt weit innerhalb von $\pm 12\,\mathrm{V}$, die Rechnung gilt also.
:::
