---
id: ex-rc-tp-belastet
title: Belasteter RC-Tiefpass
topic: rc-filter
difficulty: 4
kind: derive
minutes: 20
answers:
  - {key: H, label: 'Übertragungsfunktion $\underline{H}(s)$ mit $s = \mathrm{j}\omega$', expr: 'RL/(R + RL + s*R*RL*C)', symbols: [s, R, RL, C]}
  - {key: H0db, label: 'Übertragungsfaktor $|\underline{H}(0)|$ in dB', value: -6.0206, unit: dB, atol: 0.05}
  - {key: fg, label: 'Grenzfrequenz $f_\mathrm{g}$ mit Last', value: 3183.1, unit: Hz, rtol: 5.0e-3}
---

Ein RC-Tiefpass mit $R = 10\,\mathrm{k\Omega}$ und $C = 10\,\mathrm{nF}$ wird am Ausgang mit
$R_\mathrm{L} = 10\,\mathrm{k\Omega}$ belastet. Schreiben Sie $s = \mathrm{j}\omega$.

![RC-Tiefpass mit R = 10 kΩ und C = 10 nF, belastet mit einem Widerstand von 10 kΩ](fig:rc-tp-last)

**a)** Leiten Sie die Übertragungsfunktion
$\underline{H}(s) = \underline{U}_\mathrm{a}/\underline{U}_\mathrm{e}$ allgemein her.

**b)** Wie groß ist der Übertragungsfaktor bei Gleichspannung, in dB?

**c)** Berechnen Sie die Grenzfrequenz mit Last und vergleichen Sie sie mit der des
unbelasteten Tiefpasses.

::: hint
Fassen Sie $C$ und $R_\mathrm{L}$ zu einer Impedanz zusammen und wenden Sie die
Spannungsteilerregel an.
:::

::: hint
Alternativ ersetzen Sie Quelle, $R$ und $R_\mathrm{L}$, von den Klemmen des Kondensators
aus gesehen, durch eine Ersatzspannungsquelle; ihr Innenwiderstand ist
$R \parallel R_\mathrm{L}$.
:::

::: hint
Bringen Sie $\underline{H}(s)$ auf die Form $H_0/(1 + s\tau')$. Die Grenzfrequenz folgt aus
$\tau'$.
:::

::: solution
**a)** Die Parallelschaltung aus $C$ und $R_\mathrm{L}$ hat die Impedanz
$\underline{Z}_\mathrm{p} = R_\mathrm{L}/(1 + sR_\mathrm{L}C)$. Mit der Teilerregel:

$$
\underline{H}(s) = \frac{\underline{Z}_\mathrm{p}}{R + \underline{Z}_\mathrm{p}} = \frac{R_\mathrm{L}}{R\,(1 + sR_\mathrm{L}C) + R_\mathrm{L}} = \frac{R_\mathrm{L}}{R + R_\mathrm{L} + sRR_\mathrm{L}C}
$$

**b)** Für $s = 0$ ist $H_0 = \frac{R_\mathrm{L}}{R + R_\mathrm{L}} = 0{,}5$, also
$20\lg 0{,}5 \approx -6{,}02\,\mathrm{dB}$.

**c)** Ausklammern ergibt

$$
\underline{H}(s) = \frac{R_\mathrm{L}}{R + R_\mathrm{L}} \cdot \frac{1}{1 + s\,(R \parallel R_\mathrm{L})\,C}, \qquad \tau' = 5\,\mathrm{k\Omega} \cdot 10\,\mathrm{nF} = 50\,\mathrm{\mu s}
$$

und damit $f_\mathrm{g} = 1/(2\pi\tau') \approx 3{,}18\,\mathrm{kHz}$. Ohne Last wäre
$f_\mathrm{g} = 1/(2\pi RC) \approx 1{,}59\,\mathrm{kHz}$: Die Last halbiert den
Übertragungsfaktor im Durchlassbereich und verdoppelt die Grenzfrequenz.
:::
