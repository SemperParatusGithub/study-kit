---
id: ex-rc-tp-grenzfrequenz
title: Grenzfrequenz eines RC-Tiefpasses
topic: rc-tiefpass
difficulty: 2
kind: compute
minutes: 10
source: {doc: ue-02, page: 2, relation: adapted}
answers:
  - {key: fg, label: '$f_\mathrm{g}$', value: 1591.55, unit: Hz, rtol: 1.0e-3}
  - {key: Hdb, label: '$|\underline{H}(f_\mathrm{g})|$ in dB', value: -3.0103, unit: dB, atol: 0.01}
  - {key: H, label: 'Übertragungsfunktion $\underline{H}(s)$', expr: '1/(1+s*R*C)', symbols: [s, R, C]}
---

Gegeben ist der RC-Tiefpass mit $R = 1\,\mathrm{k\Omega}$ und $C = 100\,\mathrm{nF}$.

![Betragsgang des
RC-Tiefpasses](fig:rc-bode)

**a)** Bestimmen Sie die Grenzfrequenz $f_\mathrm{g}$.

**b)** Wie groß ist $|\underline{H}(f_\mathrm{g})|$ in dB?

**c)** Geben Sie $\underline{H}(s)$ an.

::: hint
Bei der Grenzfrequenz sind Wirk- und Blindwiderstand betragsmäßig gleich.
:::

::: hint
Setzen Sie $R = \frac{1}{2\pi f_\mathrm{g} C}$ und lösen Sie nach $f_\mathrm{g}$ auf.
:::

::: solution
**a)** $f_\mathrm{g} = \frac{1}{2\pi RC} \approx 1{,}59\,\mathrm{kHz}$

**b)** $20\log_{10}\frac{1}{\sqrt{2}} \approx -3{,}01\,\mathrm{dB}$

**c)** Spannungsteiler aus $R$ und $\frac{1}{sC}$:

$$
\underline{H}(s) = \frac{1}{1 + sRC}
$$
:::
