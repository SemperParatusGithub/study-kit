---
topic: rc-filter
title: RC-Filter und Bode-Diagramm
objectives:
  - 'Übertragungsfunktion eines RC-Tiefpasses herleiten'
sources: [{doc: vl-05, pages: '12-30'}]
---

## Übertragungsfunktion

Der Spannungsteiler aus $R$ und $C$ liefert

$$
\underline{H}(\mathrm{j}\omega) = \frac{1}{1 + \mathrm{j}\omega RC}
$$

![Bode-Diagramm des RC-Tiefpasses mit $f_\mathrm{g} = 1{,}59\,\mathrm{kHz}$](fig:rc-bode)

::: definition
**Grenzfrequenz**

Bei $f_\mathrm{g} = \frac{1}{2\pi RC}$ gilt $|\underline{H}| = 1/\sqrt{2}$.
:::

::: warning
**Häufiger Fehler**

$\omega_\mathrm{g}$ und $f_\mathrm{g}$ unterscheiden sich um den Faktor $2\pi$ ([VL 5, S. 14](src:vl-05#p=14)).
:::

### Sprungantwort

$$
u_C(t) = \begin{cases} 0 & t < 0 \\ U_0 \left(1 - \mathrm{e}^{-t/\tau}\right) & t \geq 0 \end{cases}
$$

| Größe | Wert |
|---|---|
| $\tau$ | $RC = 0{,}1\,\mathrm{ms}$ |
| $f_\mathrm{g}$ | $1{,}59\,\mathrm{kHz}$ |

- Zeitkonstante $\tau = RC$
- Nach $5\tau$ ist der Kondensator praktisch geladen.

```python
from math import pi

print(1 / (2 * pi * 1e3 * 100e-9))
```

::: note
Ohne Titel bekommt der Kasten den Standardnamen.
:::

Übung: [Grenzfrequenz RC-Tiefpass](ex:ex-rc-tp-grenzfrequenz), Grundlagen in [Gleichstromnetzwerke](topic:gleichstrom),
Testfrage [mc-rc-filter-003](mc:mc-rc-filter-003) und die [Probeklausur](exam:probeklausur-1).
