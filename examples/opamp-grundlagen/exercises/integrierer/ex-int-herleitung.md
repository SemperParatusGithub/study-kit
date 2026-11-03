---
id: ex-int-herleitung
title: Ausgangsspannung des Integrierers herleiten
topic: integrierer
difficulty: 2
kind: derive
minutes: 12
source: {doc: vl03-operationsverstaerker-grundschaltungen, page: 11, relation: inspired}
answers:
  - {key: Ua, label: 'Ausgangsspannung $U_a(t)$ als Formel in $U_e$, $R$, $C$, $t$ und $U_{a0}$', expr: 'Ua0 - Ue*t/(R*C)', symbols: [Ue, R, C, t, Ua0]}
  - {key: tsat, label: 'Zeit $t_\mathrm{sat}$ bis $U_a = -U_\mathrm{sat}$ als Formel', expr: 'R*C*(Usat + Ua0)/Ue', symbols: [Ue, R, C, Ua0, Usat]}
---

An einem invertierenden Integrierer (idealer OPV, Widerstand $R$ am Eingang, Kondensator
$C$ im Rückkopplungszweig) liegt ab $t = 0$ eine konstante Eingangsspannung $U_e > 0$.
Zu Beginn ist der Kondensator so geladen, dass $U_a(0) = U_{a0}$ gilt, mit
$|U_{a0}| < U_\mathrm{sat}$.

![Invertierender Integrierer: R vom Eingang an den invertierenden Eingang, C vom Ausgang zurück](fig:integrierer-schaltung)

**a)** Stellen Sie die Knotengleichung am invertierenden Eingang auf und leiten Sie daraus
$U_a(t)$ her, solange der Ausgang nicht in der Sättigung ist.

**b)** Nach welcher Zeit $t_\mathrm{sat}$ erreicht der Ausgang die Sättigung
$-U_\mathrm{sat}$?

::: hint
Am invertierenden Eingang gilt die virtuelle Masse $U_n = 0$, und in den OPV fließt kein
Strom.
:::

::: hint
Der Strom durch $R$ fließt vollständig in den Kondensator; am Kondensator gilt
$I_C = C \cdot \mathrm{d}U_C/\mathrm{d}t$ mit $U_C = U_n - U_a$.
:::

::: hint
Die Knotengleichung führt auf $\mathrm{d}U_a/\mathrm{d}t = -U_e/(RC)$; integrieren Sie
von $0$ bis $t$.
:::

::: solution
**a)** Mit $U_n = 0$ und $I_n = 0$ ist der Strom durch $R$ gleich dem Strom in den
Kondensator:

$$
\frac{U_e - 0}{R} = C \cdot \frac{\mathrm{d}(0 - U_a)}{\mathrm{d}t} \quad\Rightarrow\quad \frac{\mathrm{d}U_a}{\mathrm{d}t} = -\frac{U_e}{RC}
$$

Integriert von $0$ bis $t$ mit dem Anfangswert $U_{a0}$:

$$
U_a(t) = -\frac{1}{RC} \int_0^t U_e\,\mathrm{d}\tau + U_{a0} = U_{a0} - \frac{U_e}{RC} \cdot t
$$

Für $U_e > 0$ ist das eine fallende Rampe.

**b)** Aus $U_a(t_\mathrm{sat}) = -U_\mathrm{sat}$:

$$
U_{a0} - \frac{U_e}{RC} \cdot t_\mathrm{sat} = -U_\mathrm{sat} \quad\Rightarrow\quad t_\mathrm{sat} = \frac{RC \cdot (U_\mathrm{sat} + U_{a0})}{U_e}
$$

Ein positiver Anfangswert verlängert die Zeit, weil die Rampe erst durch null laufen
muss; mit $U_{a0} = 0$ bleibt $t_\mathrm{sat} = RC \cdot U_\mathrm{sat}/U_e$.
:::
