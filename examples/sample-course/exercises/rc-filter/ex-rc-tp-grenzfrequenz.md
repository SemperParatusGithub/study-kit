---
id: ex-rc-tp-grenzfrequenz
title: Grenzfrequenz eines RC-Tiefpasses
topic: rc-filter
difficulty: 1
kind: compute
minutes: 8
answers:
  - {key: tau, label: 'Zeitkonstante $\tau$', value: 103.4, unit: µs, rtol: 5.0e-3}
  - {key: fg, label: 'Grenzfrequenz $f_\mathrm{g}$', value: 1539.2, unit: Hz, rtol: 5.0e-3}
  - {key: Hdb, label: '$|\underline{H}(f_\mathrm{g})|$ in dB', value: -3.0103, unit: dB, atol: 0.05}
  - {key: phi, label: 'Phase $\varphi$ bei $f_\mathrm{g}$', value: -45, unit: °, atol: 0.5}
---

Gegeben ist ein unbelasteter RC-Tiefpass mit $R = 2{,}2\,\mathrm{k\Omega}$ und
$C = 47\,\mathrm{nF}$.

![RC-Tiefpass mit R = 2,2 kΩ und C = 47 nF](fig:rc-tp-2k2)

**a)** Berechnen Sie die Zeitkonstante $\tau$.

**b)** Berechnen Sie die Grenzfrequenz $f_\mathrm{g}$.

**c)** Wie groß sind Betrag (in dB) und Phase von $\underline{H}$ bei $f_\mathrm{g}$?

::: hint
Bei der Grenzfrequenz ist der Blindwiderstand des Kondensators so groß wie $R$.
:::

::: hint
Es gilt $\tau = RC$, $\omega_\mathrm{g} = 1/\tau$ und $f_\mathrm{g} = \omega_\mathrm{g}/(2\pi)$.
:::

::: solution
**a)** $\tau = RC = 2{,}2\,\mathrm{k\Omega} \cdot 47\,\mathrm{nF} = 103{,}4\,\mathrm{\mu s}$

**b)** $f_\mathrm{g} = \frac{1}{2\pi\tau} = \frac{1}{2\pi \cdot 103{,}4\,\mathrm{\mu s}} \approx 1{,}54\,\mathrm{kHz}$

**c)** Bei $f_\mathrm{g}$ ist $\omega RC = 1$, also $\underline{H} = 1/(1 + \mathrm{j})$:

$$
|\underline{H}| = \frac{1}{\sqrt{2}} \;\Rightarrow\; 20\lg\frac{1}{\sqrt{2}} \approx -3{,}01\,\mathrm{dB}, \qquad \varphi = -\arctan 1 = -45^\circ
$$
:::
