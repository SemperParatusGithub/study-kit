---
id: ex-int-sprung-saettigung
title: Integrierer mit Sprungeingang bis zur Sättigung
topic: integrierer
difficulty: 4
kind: compute
minutes: 27
source: {doc: klausur-ws2025-26, page: 2, relation: adapted}
answers:
  - {key: slope, label: 'Steigung $\mathrm{d}U_a/\mathrm{d}t$ der Ausgangsrampe', value: 78.431, unit: V/s, rtol: 5.0e-3}
  - {key: tsat, label: 'Zeit $t_\mathrm{sat}$ bis zur Sättigung', value: 140.25, unit: ms, rtol: 5.0e-3}
  - {key: f1, label: 'Frequenz $f_1$ mit $|\underline{H}| = 1$', value: 15.603, unit: Hz, rtol: 5.0e-3}
  - {key: H50, label: 'Betrag $|\underline{H}|$ bei $f = 50\,\mathrm{Hz}$', value: 0.31207, rtol: 5.0e-3}
---

Ein Integrierer mit idealem OPV besteht aus $R = 68\,\mathrm{k\Omega}$ und
$C = 150\,\mathrm{nF}$. Der Ausgang ist auf $\pm 11\,\mathrm{V}$ begrenzt. Ab $t = 0$
liegt die konstante Eingangsspannung $U_e = -0.8\,\mathrm{V}$ an; vorher war
$U_e = 0$ und der Kondensator ist entladen, $U_a(0) = 0$.

![Invertierender Integrierer: R vom Eingang an den invertierenden Eingang, C vom Ausgang zurück](fig:integrierer-schaltung)

**a)** Geben Sie $U_a(t)$ allgemein und mit Zahlen an. Wie groß ist die Steigung
$\mathrm{d}U_a/\mathrm{d}t$?

**b)** Wann erreicht der Ausgang die Sättigung?

**c)** Skizzieren Sie $U_e(t)$ und $U_a(t)$ für $0 \le t \le 200\,\mathrm{ms}$.

**d)** Bei welcher Frequenz $f_1$ ist $|\underline{H}(j\omega)| = 1$? Wie groß ist
$|\underline{H}|$ bei $f = 50\,\mathrm{Hz}$?

::: hint
Gehen Sie von der virtuellen Masse aus: Der Strom $U_e/R$ fließt vollständig in den
Kondensator.
:::

::: hint
Bei konstantem $U_e$ wird das Integral zu $U_e \cdot t$; achten Sie auf das Vorzeichen,
denn $U_e$ ist negativ.
:::

::: hint
Die Rampe endet an der Grenze, auf die sie zuläuft; der Integrierer hat
$|\underline{H}| = 1/(2\pi f RC)$.
:::

::: solution
**a)** Allgemein gilt

$$
U_a(t) = -\frac{1}{RC} \int_0^t U_e\,\mathrm{d}\tau + U_a(0) = -\frac{U_e}{RC} \cdot t
$$

Mit $RC = 68\,\mathrm{k\Omega} \cdot 150\,\mathrm{nF} = 10.2\,\mathrm{ms}$:

$$
U_a(t) = -\frac{-0.8\,\mathrm{V}}{10.2\,\mathrm{ms}} \cdot t \approx 78.43\,\frac{\mathrm{V}}{\mathrm{s}} \cdot t
$$

Die Rampe steigt, weil $U_e$ negativ ist.

**b)** Sie läuft auf $+11\,\mathrm{V}$ zu:

$$
t_\mathrm{sat} = \frac{11\,\mathrm{V}}{78.43\,\mathrm{V/s}} \approx 140.25\,\mathrm{ms}
$$

**c)** $U_e$ springt bei $t = 0$ auf $-0.8\,\mathrm{V}$ und bleibt dort. $U_a$ steigt von
null linear an, erreicht bei $140.25\,\mathrm{ms}$ die $+11\,\mathrm{V}$ und bleibt bis
$200\,\mathrm{ms}$ waagerecht dort.

![Lösungsskizze: Ue springt bei t = 0 auf −0.8 V; Ua steigt linear bis +11 V bei 140.25 ms und bleibt dann konstant](fig:integrierer-sprung-skizze)

**d)** Aus $|\underline{H}| = 1/(2\pi f RC) = 1$:

$$
f_1 = \frac{1}{2\pi RC} = \frac{1}{2\pi \cdot 10.2\,\mathrm{ms}} \approx 15.60\,\mathrm{Hz}
$$

Bei $f = 50\,\mathrm{Hz}$ ist
$|\underline{H}| = f_1/f = 15.60\,\mathrm{Hz}/50\,\mathrm{Hz} \approx 0.312$.
:::
