---
id: ex-rc-tp-bode
title: Bode-Diagramm eines Tiefpasses
topic: rc-filter
difficulty: 2
kind: sketch
minutes: 15
answers:
  - {key: fg, label: 'Grenzfrequenz $f_\mathrm{g}$', value: 10.261, unit: kHz, rtol: 5.0e-3}
  - {key: Hdb10, label: '$|\underline{H}|$ bei $10\,f_\mathrm{g}$ in dB', value: -20.043, unit: dB, atol: 0.05}
  - {key: phi10, label: 'Phase bei $10\,f_\mathrm{g}$', value: -84.29, unit: °, atol: 0.5}
  - {key: phi01, label: 'Phase bei $f_\mathrm{g}/10$', value: -5.71, unit: °, atol: 0.5}
---

Ein unbelasteter RC-Tiefpass besteht aus $R = 3{,}3\,\mathrm{k\Omega}$ und
$C = 4{,}7\,\mathrm{nF}$.

**a)** Berechnen Sie die Grenzfrequenz $f_\mathrm{g}$.

**b)** Berechnen Sie den Betrag in dB und die Phase bei $f = 10\,f_\mathrm{g}$.

**c)** Berechnen Sie die Phase bei $f = f_\mathrm{g}/10$.

**d)** Skizzieren Sie Betrags- und Phasengang von $100\,\mathrm{Hz}$ bis $1\,\mathrm{MHz}$
mit den Asymptoten und tragen Sie die berechneten Punkte ein.

::: hint
Rechnen Sie mit der normierten Frequenz $x = f/f_\mathrm{g}$. Dann gilt
$|\underline{H}| = 1/\sqrt{1 + x^2}$ und $\varphi = -\arctan x$.
:::

::: hint
Die Betragsasymptote ist bis $f_\mathrm{g}$ waagerecht und fällt danach pro Dekade um den
Faktor zehn in der Amplitude. Die Phasenasymptote verläuft von $0^\circ$ bei
$f_\mathrm{g}/10$ geradlinig bis $-90^\circ$ bei $10\,f_\mathrm{g}$.
:::

::: solution
**a)** $f_\mathrm{g} = \frac{1}{2\pi RC} = \frac{1}{2\pi \cdot 3{,}3\,\mathrm{k\Omega} \cdot 4{,}7\,\mathrm{nF}} \approx 10{,}26\,\mathrm{kHz}$

**b)** Mit $x = 10$:

$$
20\lg\frac{1}{\sqrt{101}} \approx -20{,}04\,\mathrm{dB}, \qquad \varphi = -\arctan 10 \approx -84{,}3^\circ
$$

Die Asymptote liefert dort genau $-20\,\mathrm{dB}$; der wahre Wert liegt nur
$0{,}04\,\mathrm{dB}$ darunter.

**c)** Mit $x = 0{,}1$: $\varphi = -\arctan 0{,}1 \approx -5{,}7^\circ$. Die Asymptote gibt
hier $0^\circ$.

**d)** Betrag: $0\,\mathrm{dB}$ bis $10{,}3\,\mathrm{kHz}$, danach $-20\,\mathrm{dB}$ pro
Dekade bis $-40\,\mathrm{dB}$ bei $1{,}03\,\mathrm{MHz}$. Phase: $-45^\circ$ bei
$f_\mathrm{g}$.

![Bode-Diagramm des Tiefpasses mit R = 3,3 kΩ und C = 4,7 nF, Grenzfrequenz 10,3 kHz](fig:rc-tp-bode-3k3)
:::
