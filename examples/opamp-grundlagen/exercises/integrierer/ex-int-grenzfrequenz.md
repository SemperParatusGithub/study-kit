---
id: ex-int-grenzfrequenz
title: Zeitkonstante und Frequenz f1 eines Integrierers
topic: integrierer
difficulty: 1
kind: compute
minutes: 6
source: {doc: skript-kapitel4-operationsverstaerker, page: 2, relation: inspired}
answers:
  - {key: RC, label: 'Integrationszeitkonstante $RC$', value: 1.551, unit: ms, rtol: 5.0e-3}
  - {key: f1, label: 'Frequenz $f_1$ mit $|\underline{H}| = 1$', value: 102.61, unit: Hz, rtol: 5.0e-3}
  - {key: H500, label: 'Betrag $|\underline{H}|$ bei $f = 500\,\mathrm{Hz}$', value: 0.20523, rtol: 5.0e-3}
---

Ein invertierender Integrierer mit idealem OPV ist mit $R = 33\,\mathrm{k\Omega}$ und
$C = 47\,\mathrm{nF}$ aufgebaut.

![Invertierender Integrierer: R vom Eingang an den invertierenden Eingang, C vom Ausgang zurück](fig:integrierer-schaltung)

**a)** Berechnen Sie die Integrationszeitkonstante $RC$ in Millisekunden.

**b)** Bei welcher Frequenz $f_1$ ist $|\underline{H}(j\omega)| = 1$?

**c)** Wie groß ist $|\underline{H}|$ bei $f = 500\,\mathrm{Hz}$?

::: hint
Der Frequenzgang des Integrierers ist $\underline{H}(j\omega) = -1/(j\omega RC)$; sein
Betrag ist $1/(\omega RC)$.
:::

::: hint
Setzen Sie $|\underline{H}| = 1$ und lösen Sie nach $\omega$ auf; denken Sie an
$\omega = 2\pi f$.
:::

::: solution
**a)** $RC = 33\,\mathrm{k\Omega} \cdot 47\,\mathrm{nF} = 1.551 \cdot 10^{-3}\,\mathrm{s} = 1.551\,\mathrm{ms}$

**b)** Aus $1/(2\pi f_1 RC) = 1$:

$$
f_1 = \frac{1}{2\pi RC} = \frac{1}{2\pi \cdot 1.551\,\mathrm{ms}} \approx 102.6\,\mathrm{Hz}
$$

**c)** $|\underline{H}| = 1/(2\pi f RC) = f_1/f = 102.6\,\mathrm{Hz}/500\,\mathrm{Hz} \approx 0.205$.
Oberhalb von $f_1$ schwächt der Integrierer ab.
:::
