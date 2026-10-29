---
id: ex-rc-tp-grenzfrequenz
title: Grenzfrequenz eines RC-Tiefpasses
topic: rc-filter
difficulty: 2
kind: compute
minutes: 10
source: {doc: vl-05, page: 14, relation: adapted}
answers:
  - {key: fg, label: '$f_\mathrm{g}$', value: 1591.55, unit: Hz, rtol: 1.0e-3}
---

Gegeben ist der RC-Tiefpass mit $R = 1\,\mathrm{k\Omega}$ und $C = 100\,\mathrm{nF}$.

![RC-Tiefpass](fig:rc-tp-schaltung)

**a)** Bestimmen Sie die Grenzfrequenz $f_\mathrm{g}$.

**b)** Wie groß ist $|\underline{H}(f_\mathrm{g})|$ in dB?

::: hint
Bei der Grenzfrequenz sind Wirk- und Blindwiderstand betragsmäßig gleich ([Thema](topic:rc-filter)).
:::

::: hint
Setzen Sie $R = \frac{1}{2\pi f_\mathrm{g} C}$ und lösen Sie nach $f_\mathrm{g}$ auf.
:::

::: solution
**a)** $f_\mathrm{g} = \frac{1}{2\pi RC} \approx 1{,}59\,\mathrm{kHz}$

**b)** $20\log_{10}\frac{1}{\sqrt{2}} \approx -3{,}01\,\mathrm{dB}$
:::
