---
id: ex-iopv-mindest-leerlaufverstaerkung
title: Mindest-Leerlaufverstärkung für einen genauen Verstärker
topic: idealer-opv
difficulty: 4
kind: compute
minutes: 18
source: {doc: altes-uebungsblatt02-scan, page: 1, relation: inspired}
answers:
  - {key: V0min, label: 'Mindest-Leerlaufverstärkung $V_{0,\mathrm{min}}$', value: 12475, rtol: 5.0e-3}
  - {key: F, label: 'Relativer Fehler $F$ mit $V_0 = 10^5$', value: 0.024994, unit: '%', rtol: 5.0e-3}
  - {key: dV, label: 'Relative Änderung von $V$, wenn $V_0$ auf $5 \cdot 10^4$ sinkt', value: -0.024988, unit: '%', rtol: 5.0e-3}
  - {key: fac, label: 'Faktor zwischen der relativen Änderung von $V_0$ und der von $V$', value: 2001, rtol: 5.0e-3}
---

Ein Messverstärker soll Sensorsignale nichtinvertierend verstärken. Er ist mit
$R_1 = 2\,\mathrm{k\Omega}$ (vom invertierenden Eingang nach Masse) und
$R_2 = 48\,\mathrm{k\Omega}$ (vom Ausgang zum invertierenden Eingang) aufgebaut. Wegen der
endlichen Leerlaufverstärkung $V_0$ darf die Verstärkung höchstens um $0.2\,\%$ unter dem
idealen Wert liegen. Die Sättigung spielt keine Rolle.

![Nichtinvertierender Verstärker mit R1 = 2 kΩ nach Masse und R2 = 48 kΩ in der Rückführung](fig:idealer-opv-nichtinv-2k-48k)

**a)** Welche Leerlaufverstärkung $V_{0,\mathrm{min}}$ muss der OPV mindestens haben?

**b)** Der gewählte OPV hat $V_0 = 10^5$. Wie groß ist der relative Fehler $F$ der
Verstärkung gegenüber dem idealen Wert?

**c)** Bei Erwärmung sinkt die Leerlaufverstärkung auf $V_0 = 5 \cdot 10^4$. Um wie viel
Prozent ändert sich die Verstärkung $V$ gegenüber b)?

**d)** $V_0$ hat sich in c) um $-50\,\%$ geändert. Um welchen Faktor ist diese relative
Änderung größer als die relative Änderung von $V$? Deuten Sie das Ergebnis.

::: hint
Der relative Fehler gegenüber dem idealen Wert $1/k$ hängt nur von der
Schleifenverstärkung $k V_0$ ab.
:::

::: hint
Aus $F = 1/(1 + k V_0) \le 0.002$ folgt eine Bedingung für $k V_0$ und damit für $V_0$.
:::

::: hint
Für c) berechnen Sie $V = V_0/(1 + k V_0)$ für beide Werte von $V_0$ mit mindestens
sechs gültigen Stellen, bevor Sie die Differenz bilden.
:::

::: solution
**a)** Der Rückkopplungsfaktor ist $k = \frac{R_1}{R_1 + R_2} = \frac{2}{50} = 0.04$, der
ideale Wert $1/k = 25$. Mit $F = 1/(1 + k V_0)$:

$$
\frac{1}{1 + k V_0} \le 0.002 \quad\Rightarrow\quad k V_0 \ge 499 \quad\Rightarrow\quad V_{0,\mathrm{min}} = \frac{499}{0.04} = 12475
$$

**b)** $k V_0 = 0.04 \cdot 10^5 = 4000$, also

$$
F = \frac{1}{1 + 4000} \approx 2.4994 \cdot 10^{-4} \approx 0.0250\,\%
$$

Die Anforderung von $0.2\,\%$ ist gut erfüllt.

**c)** Mit $V = V_0/(1 + k V_0)$:

$$
V(10^5) = \frac{10^5}{4001} \approx 24.99375, \qquad V(5 \cdot 10^4) = \frac{5 \cdot 10^4}{2001} \approx 24.98751
$$

Die relative Änderung ist
$\frac{24.98751 - 24.99375}{24.99375} \approx -2.4988 \cdot 10^{-4} \approx -0.0250\,\%$.

**d)** $\frac{-50\,\%}{-0.024988\,\%} \approx 2001$. Das ist gerade $1 + k V_0$ mit dem
neuen Wert $V_0 = 5 \cdot 10^4$: Die Gegenkopplung macht die Verstärkung um den Faktor der
Schleifenverstärkung unempfindlicher gegen Schwankungen von $V_0$. Deshalb genügt es,
$V_0$ groß genug zu wählen; sein genauer Wert ist unwichtig.
:::
