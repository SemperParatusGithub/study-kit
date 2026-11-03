---
id: ex-vg-innenwiderstand-herleitung
title: Invertierender Verstärker an einer Quelle mit Innenwiderstand
topic: verstaerker-grundschaltungen
difficulty: 3
kind: derive
minutes: 15
source: {doc: skript-kapitel4-operationsverstaerker, page: 1, relation: adapted}
answers:
  - {key: VU0, label: 'Verstärkung $U_a/U_0$ als Formel in $R_1$, $R_2$ und $R_i$', expr: '-R2/(R1 + Ri)', symbols: [R1, R2, Ri]}
  - {key: R1min, label: 'Kleinster zulässiger Widerstand $R_1$', value: 73.5, unit: kΩ, rtol: 5.0e-3}
  - {key: R2, label: 'Rückkopplungswiderstand $R_2$', value: 367.5, unit: kΩ, rtol: 5.0e-3}
---

Ein invertierender Verstärker mit idealem OPV wird aus einer Quelle mit Leerlaufspannung
$U_0$ und Innenwiderstand $R_i$ gespeist.

![Invertierender Verstärker an einer Quelle mit Leerlaufspannung U0 und Innenwiderstand Ri](fig:verstaerker-grundschaltungen-invertierer-quelle)

**a)** Leiten Sie die Verstärkung $U_a/U_0$ bezogen auf die Leerlaufspannung als Formel in
$R_1$, $R_2$ und $R_i$ her.

**b)** Der Innenwiderstand ist $R_i = 1.5\,\mathrm{k\Omega}$. Der Betrag von $U_a/U_0$ soll
höchstens $2\,\%$ unter dem Betrag der idealen Verstärkung $-R_2/R_1$ liegen. Wie groß muss
$R_1$ mindestens sein?

**c)** Die ideale Verstärkung soll $-R_2/R_1 = -5$ sein. Welchen Wert hat $R_2$, wenn Sie
$R_1$ aus b) wählen?

::: hint
Der Strom aus der Quelle fließt durch $R_i$ und $R_1$ bis zur virtuellen Masse.
:::

::: hint
Das Verhältnis der beiden Verstärkungen ist $R_1/(R_1 + R_i)$; die Abweichung ist also
$R_i/(R_1 + R_i)$.
:::

::: solution
**a)** $R_i$ und $R_1$ liegen in Reihe vor der virtuellen Masse ($U_n = 0$, $I_n = 0$).
Knotenregel am invertierenden Eingang:

$$
\frac{U_0}{R_1 + R_i} + \frac{U_a}{R_2} = 0 \quad\Rightarrow\quad \frac{U_a}{U_0} = -\frac{R_2}{R_1 + R_i}
$$

Für $R_i \to 0$ folgt wieder $-R_2/R_1$.

**b)** Relative Abweichung vom idealen Betrag:

$$
1 - \frac{R_1}{R_1 + R_i} = \frac{R_i}{R_1 + R_i} \le 0.02 \quad\Rightarrow\quad R_1 \ge \frac{0.98}{0.02} \cdot R_i = 49 \cdot 1.5\,\mathrm{k\Omega} = 73.5\,\mathrm{k\Omega}
$$

**c)** $R_2 = 5 \cdot R_1 = 5 \cdot 73.5\,\mathrm{k\Omega} = 367.5\,\mathrm{k\Omega}$. Der große
Eingangswiderstand $R_1$ verlangt einen entsprechend großen $R_2$; bei sehr hochohmigen
Quellen ist deshalb ein nichtinvertierender Verstärker günstiger.
:::
