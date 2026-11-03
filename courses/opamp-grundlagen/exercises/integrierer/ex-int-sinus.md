---
id: ex-int-sinus
title: Sinusspannung am Integrierer
topic: integrierer
difficulty: 3
kind: compute
minutes: 12
answers:
  - {key: Uahat, label: 'Amplitude $\hat{U}_a$ bei $f = 200\,\mathrm{Hz}$', value: 0.84657, unit: V, rtol: 5.0e-3}
  - {key: fmin, label: 'Kleinste Frequenz $f_\mathrm{min}$ ohne Sättigung', value: 16.931, unit: Hz, rtol: 5.0e-3}
  - {key: Ua12, label: 'Rechnerische Amplitude $\hat{U}_a$ bei $f = 12\,\mathrm{Hz}$', value: 14.109, unit: V, rtol: 5.0e-3}
---

An einem Integrierer mit idealem OPV, $R = 10\,\mathrm{k\Omega}$ und $C = 47\,\mathrm{nF}$
liegt die Eingangsspannung $U_e(t) = \hat{U}_e \sin(2\pi f t)$ mit
$\hat{U}_e = 0.5\,\mathrm{V}$. Der Ausgang ist auf $\pm 10\,\mathrm{V}$ begrenzt; der
Gleichanteil am Ausgang sei null.

**a)** Wie groß ist die Amplitude $\hat{U}_a$ der Ausgangsspannung bei $f = 200\,\mathrm{Hz}$?

**b)** Unterhalb welcher Frequenz $f_\mathrm{min}$ ginge der Ausgang in die Sättigung?

**c)** Welche Amplitude ergäbe die Formel bei $f = 12\,\mathrm{Hz}$? Was zeigt dann ein
Oszilloskop am Ausgang?

::: hint
Die Amplitude am Ausgang ist $|\underline{H}| \cdot \hat{U}_e$.
:::

::: hint
Der Betrag $|\underline{H}| = 1/(2\pi f RC)$ wächst, je tiefer die Frequenz ist; die
Grenze ist $\hat{U}_a = U_\mathrm{sat}$.
:::

::: solution
Es ist $RC = 10\,\mathrm{k\Omega} \cdot 47\,\mathrm{nF} = 0.47\,\mathrm{ms}$.

**a)** $\hat{U}_a = \frac{\hat{U}_e}{2\pi f RC} = \frac{0.5\,\mathrm{V}}{2\pi \cdot 200\,\mathrm{Hz} \cdot 0.47\,\mathrm{ms}} \approx 0.847\,\mathrm{V}$

Das Integral des Sinus ist ein Kosinus; wegen der Inversion eilt $U_a$ der
Eingangsspannung um $90^\circ$ vor.

**b)** Aus $\hat{U}_a = U_\mathrm{sat}$:

$$
f_\mathrm{min} = \frac{\hat{U}_e}{2\pi RC \cdot U_\mathrm{sat}} = \frac{0.5\,\mathrm{V}}{2\pi \cdot 0.47\,\mathrm{ms} \cdot 10\,\mathrm{V}} \approx 16.93\,\mathrm{Hz}
$$

**c)** $\hat{U}_a = \frac{0.5\,\mathrm{V}}{2\pi \cdot 12\,\mathrm{Hz} \cdot 0.47\,\mathrm{ms}} \approx 14.11\,\mathrm{V}$.
Das ist mehr als $10\,\mathrm{V}$: Der Ausgang wird oben und unten bei $\pm 10\,\mathrm{V}$
abgeschnitten, die Kosinusform ist verzerrt, und die Integriererformel gilt in diesen
Abschnitten nicht.
:::
