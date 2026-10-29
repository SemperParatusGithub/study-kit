---
id: ex-st-ersatzquelle
title: Ersatzspannungsquelle eines Teilers
topic: spannungsteiler
difficulty: 3
kind: compute
minutes: 15
answers:
  - {key: Uq, label: 'Leerlaufspannung $U_\mathrm{q}$', value: 4, unit: V, rtol: 5.0e-3}
  - {key: Ri, label: 'Innenwiderstand $R_\mathrm{i}$', value: 2.4, unit: kΩ, rtol: 5.0e-3}
  - {key: UL, label: 'Lastspannung $U_\mathrm{L}$ an $R_\mathrm{L}$', value: 1.6, unit: V, rtol: 5.0e-3}
  - {key: IL, label: 'Laststrom $I_\mathrm{L}$', value: 1.0, unit: mA, rtol: 5.0e-3}
  - {key: Pmax, label: 'Größte Lastleistung $P_\mathrm{max}$', value: 1.6667, unit: mW, rtol: 5.0e-3}
---

Die Schaltung soll an den Klemmen A und B durch eine Ersatzspannungsquelle beschrieben
werden.

![Spannungsquelle U0 = 10 V mit R1 = 6 kΩ und R2 = 4 kΩ; die Klemmen A und B liegen an R2](fig:st-ersatz-netz)

**a)** Bestimmen Sie die Leerlaufspannung $U_\mathrm{q}$ an den Klemmen.

**b)** Bestimmen Sie den Innenwiderstand $R_\mathrm{i}$.

**c)** An die Klemmen wird $R_\mathrm{L} = 1{,}6\,\mathrm{k\Omega}$ angeschlossen.
Berechnen Sie $U_\mathrm{L}$ und $I_\mathrm{L}$ mit der Ersatzschaltung.

**d)** Bei welchem Lastwiderstand gibt die Schaltung die größte Leistung ab, und wie groß
ist diese Leistung?

::: hint
Bei offenen Klemmen ist der Teiler unbelastet; die Leerlaufspannung folgt aus der
Teilerregel.
:::

::: hint
Für den Innenwiderstand ersetzen Sie die Spannungsquelle durch einen Kurzschluss. Von den
Klemmen aus gesehen liegen $R_1$ und $R_2$ dann parallel.
:::

::: hint
Mit der Ersatzschaltung bilden $R_\mathrm{i}$ und $R_\mathrm{L}$ einen einfachen
Spannungsteiler.
:::

::: solution
**a)** $U_\mathrm{q} = U_0 \cdot \frac{R_2}{R_1 + R_2} = 10\,\mathrm{V} \cdot \frac{4}{10} = 4\,\mathrm{V}$

**b)** $R_\mathrm{i} = R_1 \parallel R_2 = \frac{6 \cdot 4}{6 + 4}\,\mathrm{k\Omega} = 2{,}4\,\mathrm{k\Omega}$.
Kontrolle über den Kurzschlussstrom: $I_\mathrm{k} = U_0/R_1 \approx 1{,}667\,\mathrm{mA}$ und
$U_\mathrm{q}/I_\mathrm{k} = 2{,}4\,\mathrm{k\Omega}$.

**c)** $U_\mathrm{L} = U_\mathrm{q} \cdot \frac{R_\mathrm{L}}{R_\mathrm{i} + R_\mathrm{L}} = 4\,\mathrm{V} \cdot \frac{1{,}6}{4{,}0} = 1{,}6\,\mathrm{V}$
und $I_\mathrm{L} = \frac{U_\mathrm{q}}{R_\mathrm{i} + R_\mathrm{L}} = \frac{4\,\mathrm{V}}{4\,\mathrm{k\Omega}} = 1\,\mathrm{mA}$.

**d)** Leistungsanpassung bei $R_\mathrm{L} = R_\mathrm{i} = 2{,}4\,\mathrm{k\Omega}$:

$$
P_\mathrm{max} = \frac{U_\mathrm{q}^2}{4 R_\mathrm{i}} = \frac{(4\,\mathrm{V})^2}{4 \cdot 2{,}4\,\mathrm{k\Omega}} \approx 1{,}67\,\mathrm{mW}
$$
:::
