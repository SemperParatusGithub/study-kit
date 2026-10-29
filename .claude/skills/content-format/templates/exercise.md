---
id: ex-rc-tp-vorlage
title: Grenzfrequenz und Dämpfung eines RC-Tiefpasses
topic: rc-filter
difficulty: 2
kind: compute
minutes: 10
answers:
  - {key: fg, label: 'Grenzfrequenz $f_\mathrm{g}$', value: 1591.55, unit: Hz, rtol: 5.0e-3}
  - {key: Hdb, label: '$|\underline{H}|$ bei $10\,\mathrm{kHz}$ in dB', value: -16.07, unit: dB, atol: 0.05}
---

Gegeben ist ein unbelasteter RC-Tiefpass mit $R = 1\,\mathrm{k\Omega}$ und
$C = 100\,\mathrm{nF}$.

![RC-Tiefpass als Vierpol: R im Längszweig, C im Querzweig](fig:rc-tp-schaltung)

**a)** Berechnen Sie die Grenzfrequenz $f_\mathrm{g}$.

**b)** Wie groß ist $|\underline{H}|$ bei $f = 10\,\mathrm{kHz}$ in dB?

::: hint
Bei der Grenzfrequenz ist der Blindwiderstand des Kondensators so groß wie $R$.
:::

::: hint
Setzen Sie $x = f/f_\mathrm{g}$ in $|\underline{H}| = 1/\sqrt{1 + x^2}$ ein.
:::

::: solution
**a)** $f_\mathrm{g} = \frac{1}{2\pi RC} = \frac{1}{2\pi \cdot 100\,\mathrm{\mu s}} \approx 1{,}59\,\mathrm{kHz}$

**b)** Mit $x = 10/1{,}592 \approx 6{,}28$:

$$
20\lg\frac{1}{\sqrt{1 + 6{,}28^2}} \approx -16{,}1\,\mathrm{dB}
$$
:::
