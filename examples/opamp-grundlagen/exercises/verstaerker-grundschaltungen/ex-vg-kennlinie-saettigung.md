---
id: ex-vg-kennlinie-saettigung
title: Übertragungskennlinie mit Sättigung skizzieren
topic: verstaerker-grundschaltungen
difficulty: 2
kind: sketch
minutes: 12
answers:
  - {key: V, label: 'Spannungsverstärkung $V$', value: 4.8462, rtol: 5.0e-3}
  - {key: Uemax, label: 'Aussteuergrenze $U_{e,\mathrm{max}}$', value: 2.4762, unit: V, rtol: 5.0e-3}
  - {key: Ua3, label: '$U_a$ für $U_e = 3\,\mathrm{V}$', value: 12, unit: V, rtol: 5.0e-3}
  - {key: Uapeak, label: 'Scheitelwert von $U_a$ bei einer Sinusamplitude von $2\,\mathrm{V}$', value: 9.6923, unit: V, rtol: 5.0e-3}
---

Ein nichtinvertierender Verstärker mit idealem OPV hat $R_1 = 3.9\,\mathrm{k\Omega}$ (nach
Masse) und $R_2 = 15\,\mathrm{k\Omega}$ (Rückkopplung). Der Ausgang ist auf
$\pm U_\mathrm{sat} = \pm 12\,\mathrm{V}$ begrenzt.

![Nichtinvertierender Verstärker mit dem Spannungsteiler aus R2 und R1 im Rückkopplungszweig](fig:verstaerker-grundschaltungen-nichtinvertierer)

**a)** Berechnen Sie die Verstärkung $V$.

**b)** Bis zu welchem Betrag der Eingangsspannung arbeitet die Schaltung linear?

**c)** Welche Ausgangsspannung stellt sich für $U_e = 3\,\mathrm{V}$ ein? Begründen Sie.

**d)** Skizzieren Sie die Übertragungskennlinie $U_a(U_e)$ für
$-4\,\mathrm{V} \le U_e \le 4\,\mathrm{V}$.

**e)** Am Eingang liegt eine Sinusspannung mit der Amplitude $2\,\mathrm{V}$. Wie groß ist der
Scheitelwert der Ausgangsspannung, und wird die Sinusform verzerrt?

::: hint
Die Formel $U_a = V \cdot U_e$ gilt nur, solange $|U_a| \le U_\mathrm{sat}$ bleibt.
:::

::: hint
Die Knickpunkte der Kennlinie liegen dort, wo $V \cdot U_e$ gerade $\pm U_\mathrm{sat}$
erreicht.
:::

::: solution
**a)** $V = 1 + R_2/R_1 = 1 + 15/3.9 \approx 4.846$

**b)** $|U_e|_\mathrm{max} = U_\mathrm{sat}/V = 12\,\mathrm{V}/4.846 \approx 2.476\,\mathrm{V}$

**c)** Rechnerisch wäre $U_a = 4.846 \cdot 3\,\mathrm{V} \approx 14.54\,\mathrm{V}$. Das liegt über
der Grenze; der Ausgang bleibt bei $U_a = +12\,\mathrm{V}$ stehen (gleiches Vorzeichen wie
$U_e$, weil der Verstärker nicht invertiert). In der Sättigung gilt $U_d = 0$ nicht mehr.

**d)** Eine Gerade mit der Steigung $4.846$ durch den Ursprung zwischen
$U_e \approx -2.48\,\mathrm{V}$ und $U_e \approx 2.48\,\mathrm{V}$, außerhalb waagerecht bei
$-12\,\mathrm{V}$ bzw. $+12\,\mathrm{V}$:

![Übertragungskennlinie des nichtinvertierenden Verstärkers mit V = 4.85 und Begrenzung bei plus und minus 12 V](fig:verstaerker-grundschaltungen-kennlinie-nichtinv)

**e)** $2\,\mathrm{V} < 2.476\,\mathrm{V}$: Die Schaltung bleibt linear, der Scheitelwert ist
$4.846 \cdot 2\,\mathrm{V} \approx 9.69\,\mathrm{V}$, und die Sinusform bleibt erhalten.
:::
