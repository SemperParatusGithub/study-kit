---
id: ex-int-rampe
title: Rampe am Integrierer
topic: integrierer
difficulty: 2
kind: compute
minutes: 10
source: {doc: uebung03-opv-grundschaltungen, page: 1, relation: adapted}
answers:
  - {key: I, label: 'Strom $I$ durch den Kondensator', value: 20.0, unit: µA, rtol: 5.0e-3}
  - {key: slope, label: 'Steigung $\mathrm{d}U_a/\mathrm{d}t$ der Rampe', value: -90.909, unit: V/s, rtol: 5.0e-3}
  - {key: Ua20, label: 'Ausgangsspannung $U_a$ bei $t = 20\,\mathrm{ms}$', value: -1.8182, unit: V, rtol: 5.0e-3}
  - {key: tsat, label: 'Zeit $t_\mathrm{sat}$ bis zur Sättigung', value: 132.0, unit: ms, rtol: 5.0e-3}
---

Ein Integrierer mit idealem OPV hat $R = 15\,\mathrm{k\Omega}$ und $C = 220\,\mathrm{nF}$.
Der Kondensator ist zu Beginn entladen ($U_a(0) = 0$). Ab $t = 0$ liegt die konstante
Eingangsspannung $U_e = 0.3\,\mathrm{V}$ an. Der Ausgang ist auf $\pm 12\,\mathrm{V}$
begrenzt.

![Invertierender Integrierer: R vom Eingang an den invertierenden Eingang, C vom Ausgang zurück](fig:integrierer-schaltung)

**a)** Welcher Strom $I$ fließt durch den Kondensator?

**b)** Mit welcher Steigung $\mathrm{d}U_a/\mathrm{d}t$ ändert sich die Ausgangsspannung?
Achten Sie auf das Vorzeichen.

**c)** Wie groß ist $U_a$ bei $t = 20\,\mathrm{ms}$?

**d)** Nach welcher Zeit $t_\mathrm{sat}$ erreicht der Ausgang die Sättigung?

::: hint
Wegen der virtuellen Masse liegt die ganze Eingangsspannung an $R$; der Strom durch $R$
kann nur in den Kondensator fließen.
:::

::: hint
Bei konstanter Eingangsspannung ist $U_a(t) = -U_e \cdot t/(RC) + U_a(0)$, eine Gerade.
:::

::: solution
**a)** $I = U_e/R = 0.3\,\mathrm{V}/15\,\mathrm{k\Omega} = 20\,\mathrm{\mu A}$

**b)** Mit $RC = 15\,\mathrm{k\Omega} \cdot 220\,\mathrm{nF} = 3.3\,\mathrm{ms}$:

$$
\frac{\mathrm{d}U_a}{\mathrm{d}t} = -\frac{U_e}{RC} = -\frac{0.3\,\mathrm{V}}{3.3\,\mathrm{ms}} \approx -90.91\,\frac{\mathrm{V}}{\mathrm{s}}
$$

Die Rampe fällt, weil $U_e$ positiv ist.

**c)** $U_a(20\,\mathrm{ms}) = -90.91\,\mathrm{V/s} \cdot 0.02\,\mathrm{s} \approx -1.818\,\mathrm{V}$;
das liegt noch im linearen Bereich.

**d)** Die Rampe erreicht $-12\,\mathrm{V}$ nach

$$
t_\mathrm{sat} = \frac{12\,\mathrm{V}}{90.91\,\mathrm{V/s}} = 0.132\,\mathrm{s} = 132\,\mathrm{ms}
$$

Danach bleibt $U_a = -12\,\mathrm{V}$, solange $U_e$ anliegt.
:::
