---
topic: rc-filter
title: RC-Filter und Bode-Diagramm
objectives:
  - 'Die Übertragungsfunktion des RC-Tiefpasses mit der Spannungsteilerregel herleiten'
  - 'Die Grenzfrequenz $f_\mathrm{g}$ berechnen und ihre Bedeutung erklären'
---

## RC-Tiefpass

![RC-Tiefpass als Vierpol: R im Längszweig, C im Querzweig](fig:rc-tp-schaltung)

Der Tiefpass ist ein [Spannungsteiler](topic:spannungsteiler) aus $R$ und der Impedanz
$1/(\mathrm{j}\omega C)$, gerechnet mit [komplexen Zeigern](topic:wechselstrom):

$$
\underline{H}(\mathrm{j}\omega) = \frac{1}{1 + \mathrm{j}\omega RC}, \qquad |\underline{H}| = \frac{1}{\sqrt{1 + (\omega RC)^2}}, \qquad \varphi = -\arctan(\omega RC)
$$

## Grenzfrequenz

::: definition
**Grenzfrequenz**

Bei der Grenzfrequenz ist der Blindwiderstand des Kondensators so groß wie $R$. Dort gilt
$|\underline{H}| = 1/\sqrt{2}$, also $-3\,\mathrm{dB}$, und $\varphi = -45^\circ$:

$$
\omega_\mathrm{g} = \frac{1}{RC}, \qquad f_\mathrm{g} = \frac{1}{2\pi RC}
$$
:::

::: warning
**Häufiger Fehler**

$\omega_\mathrm{g}$ und $f_\mathrm{g}$ unterscheiden sich um den Faktor $2\pi$.
:::

::: example
**Beispiel**

Mit $R = 1\,\mathrm{k\Omega}$ und $C = 100\,\mathrm{nF}$ ist
$f_\mathrm{g} \approx 1{,}59\,\mathrm{kHz}$.
:::

Übung: [Grenzfrequenz eines RC-Tiefpasses](ex:ex-rc-tp-grenzfrequenz)

::: takeaways
- $f_\mathrm{g} = 1/(2\pi RC)$, dort $-3\,\mathrm{dB}$ und $-45^\circ$.
- Oberhalb von $f_\mathrm{g}$ fällt der Betrag mit $20\,\mathrm{dB}$ pro Dekade.
:::
