---
id: ex-int-betrag-phase
title: Betrag und Phase des Integrierers
topic: integrierer
difficulty: 2
kind: compute
minutes: 10
source: {doc: vl03-operationsverstaerker-grundschaltungen, page: 12, relation: inspired}
answers:
  - {key: f1, label: 'Frequenz $f_1$ mit $|\underline{H}| = 1$', value: 3386.3, unit: Hz, rtol: 5.0e-3}
  - {key: Hdb, label: '$|\underline{H}|$ bei $f = 1\,\mathrm{kHz}$ in dB', value: 10.594, unit: dB, atol: 0.05}
  - {key: phi, label: 'Phasenwinkel $\varphi$ von $\underline{H}$ bei $f = 1\,\mathrm{kHz}$', value: 90.0, unit: °, atol: 0.5}
  - {key: f20, label: 'Frequenz mit $|\underline{H}| = 0.1$', value: 33.863, unit: kHz, rtol: 5.0e-3}
---

Ein invertierender Integrierer mit idealem OPV ist mit $R = 4.7\,\mathrm{k\Omega}$ und
$C = 10\,\mathrm{nF}$ aufgebaut. Sein Frequenzgang ist
$\underline{H}(j\omega) = \underline{U}_a/\underline{U}_e$.

**a)** Berechnen Sie die Frequenz $f_1$, bei der $|\underline{H}| = 1$ ist.

**b)** Wie groß ist $|\underline{H}|$ bei $f = 1\,\mathrm{kHz}$ in dB?

**c)** Welchen Phasenwinkel $\varphi$ hat $\underline{H}$ bei $f = 1\,\mathrm{kHz}$? Eilt die
Ausgangsspannung vor oder nach?

**d)** Bei welcher Frequenz ist $|\underline{H}| = 0.1$?

::: hint
Schreiben Sie den Integrierer als invertierenden Verstärker mit der Impedanz
$1/(j\omega C)$ im Rückkopplungszweig.
:::

::: hint
Formen Sie $-1/(j\omega RC)$ so um, dass kein $j$ im Nenner steht; der Betrag fällt mit
$20\,\mathrm{dB}$ pro Dekade.
:::

::: solution
**a)** $f_1 = \frac{1}{2\pi RC} = \frac{1}{2\pi \cdot 4.7\,\mathrm{k\Omega} \cdot 10\,\mathrm{nF}} = \frac{1}{2\pi \cdot 47\,\mathrm{\mu s}} \approx 3386\,\mathrm{Hz}$

**b)** $|\underline{H}| = 1/(2\pi f RC) = f_1/f = 3386\,\mathrm{Hz}/1\,\mathrm{kHz} \approx 3.386$, also

$$
20 \lg 3.386 \approx 10.59\,\mathrm{dB}
$$

Unterhalb von $f_1$ verstärkt der Integrierer.

**c)** Mit $1/j = -j$ gilt

$$
\underline{H}(j\omega) = -\frac{1}{j\omega RC} = \frac{j}{\omega RC}
$$

Das ist eine positive imaginäre Zahl, also $\varphi = +90^\circ$ bei jeder Frequenz: Die
Ausgangsspannung eilt der Eingangsspannung um $90^\circ$ vor.

**d)** $|\underline{H}| = f_1/f = 0.1$ ergibt $f = 10 \cdot f_1 \approx 33.86\,\mathrm{kHz}$,
eine Dekade über $f_1$ ($-20\,\mathrm{dB}$).
:::
