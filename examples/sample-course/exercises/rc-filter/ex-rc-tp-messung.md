---
id: ex-rc-tp-messung
title: Tiefpass aus einer Messung bestimmen
topic: rc-filter
difficulty: 3
kind: compute
minutes: 15
answers:
  - {key: fg, label: 'Grenzfrequenz $f_\mathrm{g}$', value: 750, unit: Hz, rtol: 5.0e-3}
  - {key: R, label: 'Widerstand $R$', value: 2.1221, unit: kΩ, rtol: 5.0e-3}
  - {key: phi, label: 'Phase $\varphi$ bei $1\,\mathrm{kHz}$', value: -53.13, unit: °, atol: 0.5}
  - {key: Hdb, label: '$|\underline{H}|$ bei $1\,\mathrm{kHz}$ in dB', value: -4.437, unit: dB, atol: 0.05}
---

Von einem unbelasteten RC-Tiefpass ist nur $C = 100\,\mathrm{nF}$ bekannt. Bei
$f = 1\,\mathrm{kHz}$ misst das Oszilloskop am Ausgang $60\,\%$ der Eingangsamplitude.

**a)** Bestimmen Sie die Grenzfrequenz $f_\mathrm{g}$.

**b)** Wie groß ist der Widerstand $R$?

**c)** Welche Phasenverschiebung zwischen Ausgang und Eingang zeigt das Oszilloskop bei
$1\,\mathrm{kHz}$, und wie groß ist der Betrag in dB?

::: hint
Setzen Sie $|\underline{H}| = 1/\sqrt{1 + (f/f_\mathrm{g})^2}$ gleich dem Messwert und lösen
Sie nach $f/f_\mathrm{g}$ auf.
:::

::: hint
Aus $f_\mathrm{g}$ und $C$ folgt $R$ über $f_\mathrm{g} = 1/(2\pi RC)$.
:::

::: solution
**a)** Aus $1/\sqrt{1 + x^2} = 0{,}6$ folgt $1 + x^2 = 1/0{,}36$, also
$x = f/f_\mathrm{g} = 4/3$ und

$$
f_\mathrm{g} = \frac{3}{4} \cdot 1\,\mathrm{kHz} = 750\,\mathrm{Hz}
$$

**b)** $R = \frac{1}{2\pi f_\mathrm{g} C} = \frac{1}{2\pi \cdot 750\,\mathrm{Hz} \cdot 100\,\mathrm{nF}} \approx 2{,}12\,\mathrm{k\Omega}$

**c)** $\varphi = -\arctan\frac{4}{3} \approx -53{,}1^\circ$: Der Ausgang eilt dem Eingang
nach. Der Betrag ist $20\lg 0{,}6 \approx -4{,}44\,\mathrm{dB}$.
:::
