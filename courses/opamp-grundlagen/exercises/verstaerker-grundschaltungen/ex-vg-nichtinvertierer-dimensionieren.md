---
id: ex-vg-nichtinvertierer-dimensionieren
title: Nichtinvertierenden Verstärker dimensionieren
topic: verstaerker-grundschaltungen
difficulty: 1
kind: compute
minutes: 8
source: {doc: uebung03-opv-grundschaltungen, page: 1, relation: adapted}
answers:
  - {key: R2, label: 'Rückkopplungswiderstand $R_2$', value: 16.5, unit: kΩ, rtol: 5.0e-3}
  - {key: Ua, label: 'Ausgangsspannung $U_a$', value: 3.825, unit: V, rtol: 5.0e-3}
  - {key: I1, label: 'Strom durch $R_1$', value: 204.55, unit: µA, rtol: 5.0e-3}
---

Ein nichtinvertierender Verstärker mit idealem OPV soll die Verstärkung $V = 8.5$ haben.
Der Widerstand vom invertierenden Eingang nach Masse ist $R_1 = 2.2\,\mathrm{k\Omega}$.

![Nichtinvertierender Verstärker mit dem Spannungsteiler aus R2 und R1 im Rückkopplungszweig](fig:verstaerker-grundschaltungen-nichtinvertierer)

**a)** Wie groß muss der Rückkopplungswiderstand $R_2$ sein?

**b)** Welche Ausgangsspannung $U_a$ stellt sich für $U_e = 0.45\,\mathrm{V}$ ein?

**c)** Welcher Strom fließt dabei durch $R_1$?

::: hint
Wegen $U_d = 0$ liegt der invertierende Eingang auf $U_e$; $R_2$ und $R_1$ bilden einen
unbelasteten Spannungsteiler für $U_a$.
:::

::: hint
Lösen Sie $V = 1 + R_2/R_1$ nach $R_2$ auf.
:::

::: solution
**a)** $V = 1 + R_2/R_1 \Rightarrow R_2 = (V - 1) \cdot R_1 = 7.5 \cdot 2.2\,\mathrm{k\Omega} = 16.5\,\mathrm{k\Omega}$

**b)** $U_a = V \cdot U_e = 8.5 \cdot 0.45\,\mathrm{V} \approx 3.825\,\mathrm{V}$

**c)** An $R_1$ liegt $U_n = U_e = 0.45\,\mathrm{V}$:
$I_1 = 0.45\,\mathrm{V}/2.2\,\mathrm{k\Omega} \approx 204.5\,\mathrm{\mu A}$. Weil in den OPV kein
Strom fließt, kommt derselbe Strom vom Ausgang über $R_2$.
:::
