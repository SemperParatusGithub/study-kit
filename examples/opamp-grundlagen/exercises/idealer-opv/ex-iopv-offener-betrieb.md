---
id: ex-iopv-offener-betrieb
title: OPV ohne Rückkopplung
topic: idealer-opv
difficulty: 1
kind: compute
minutes: 8
source: {doc: vl03-operationsverstaerker-grundschaltungen, page: 3, relation: inspired}
answers:
  - {key: Ud, label: 'Differenzspannung $U_d$', value: 30, unit: µV, rtol: 5.0e-3}
  - {key: Ua, label: 'Ausgangsspannung $U_a$', value: 6, unit: V, rtol: 5.0e-3}
  - {key: Udmax, label: 'Größte Differenzspannung $|U_d|_\mathrm{max}$ im linearen Bereich', value: 67.5, unit: µV, rtol: 5.0e-3}
  - {key: Ua2, label: 'Ausgangsspannung $U_a$ bei $U_n = 24.900\,\mathrm{mV}$', value: 13.5, unit: V, rtol: 5.0e-3}
---

Ein Operationsverstärker wird ohne Rückkopplung betrieben. Seine Leerlaufverstärkung ist
$V_0 = 2 \cdot 10^5$, sein Ausgang ist auf $\pm 13.5\,\mathrm{V}$ begrenzt
($U_\mathrm{sat} = 13.5\,\mathrm{V}$). Am nichtinvertierenden Eingang liegt
$U_p = 25.030\,\mathrm{mV}$, am invertierenden Eingang $U_n = 25.000\,\mathrm{mV}$, beide
gegen Masse gemessen.

**a)** Wie groß ist die Differenzspannung $U_d$?

**b)** Welche Ausgangsspannung $U_a$ stellt sich ein?

**c)** Bis zu welchem Betrag der Differenzspannung arbeitet der OPV linear?

**d)** $U_n$ sinkt auf $24.900\,\mathrm{mV}$, $U_p$ bleibt gleich. Welche
Ausgangsspannung stellt sich jetzt ein?

::: hint
Der OPV verstärkt nur die Differenz $U_d = U_p - U_n$, nicht die einzelnen Spannungen.
:::

::: hint
Der lineare Bereich endet dort, wo $V_0 \cdot |U_d|$ die Sättigungsspannung erreicht.
:::

::: hint
Prüfen Sie in d), ob $V_0 \cdot U_d$ noch kleiner als $U_\mathrm{sat}$ ist.
:::

::: solution
**a)** $U_d = U_p - U_n = 25.030\,\mathrm{mV} - 25.000\,\mathrm{mV} = 0.030\,\mathrm{mV} = 30\,\mathrm{\mu V}$

**b)** $U_a = V_0 \cdot U_d = 2 \cdot 10^5 \cdot 30\,\mathrm{\mu V} = 6\,\mathrm{V}$. Wegen
$6\,\mathrm{V} < 13.5\,\mathrm{V}$ ist der OPV im linearen Bereich.

**c)** Der lineare Bereich endet bei $V_0 \cdot |U_d| = U_\mathrm{sat}$:

$$
|U_d|_\mathrm{max} = \frac{U_\mathrm{sat}}{V_0} = \frac{13.5\,\mathrm{V}}{2 \cdot 10^5} = 67.5\,\mathrm{\mu V}
$$

**d)** Jetzt ist $U_d = 25.030\,\mathrm{mV} - 24.900\,\mathrm{mV} = 130\,\mathrm{\mu V}$.
Rechnerisch ergäbe das $U_a = 2 \cdot 10^5 \cdot 130\,\mathrm{\mu V} = 26\,\mathrm{V}$, mehr
als der Ausgang liefern kann. Wegen $U_d > |U_d|_\mathrm{max}$ ist der OPV in der
positiven Sättigung: $U_a = 13.5\,\mathrm{V}$. Schon eine Änderung von
$0.1\,\mathrm{mV}$ reicht dafür; ohne Gegenkopplung ist der OPV als Verstärker
unbrauchbar.
:::
