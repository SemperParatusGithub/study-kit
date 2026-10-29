---
topic: rc-tiefpass
title: RC-Tiefpass
objectives:
  - 'Die Grenzfrequenz $f_\mathrm{g}$ berechnen'
  - 'Den Betrag im Bode-Diagramm ablesen'
sources: [{doc: vl-02, pages: '1-12'}]
---

## Übertragungsfunktion

Der Tiefpass ist ein [Spannungsteiler](topic:spannungsteiler) aus $R$ und $C$:

$$
\underline{H}(\mathrm{j}\omega) = \frac{1}{1 + \mathrm{j}\omega RC}
$$

![Bode-Diagramm des RC-Tiefpasses](fig:rc-bode)

::: theorem
**Grenzfrequenz**

$$
f_\mathrm{g} = \frac{1}{2\pi RC} \approx 1{,}59\,\mathrm{kHz}
\quad \text{für } R = 1\,\mathrm{k\Omega},\ C = 100\,\mathrm{nF}
$$
:::

::: warning
**Häufiger Fehler**

$\omega_\mathrm{g}$ und $f_\mathrm{g}$ unterscheiden sich um den Faktor $2\pi$
([VL 2, S. 7](src:vl-02#p=7)).
:::

::: note
Die Phase ist $\varphi = \begin{cases} 0 & f \to 0 \\ -45^\circ & f = f_\mathrm{g} \end{cases}$
und bei $f = f_\mathrm{g}$ gilt $|\underline{H}| = 1/\sqrt{2}$.
:::

Übung: [Grenzfrequenz](ex:ex-rc-tp-grenzfrequenz), Quiz: [Frage 1](mc:mc-rc-tiefpass-001)
