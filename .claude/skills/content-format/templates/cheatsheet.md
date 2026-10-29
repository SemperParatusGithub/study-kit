---
title: Formelblatt RC-Netzwerke
max_pages: 2
priority: [rc-filter, wechselstrom, spannungsteiler]
---

## Spannungsteiler und Ersatzquellen

$$
U_2 = U_0 \cdot \frac{R_2}{R_1 + R_2}, \qquad R_1 \parallel R_2 = \frac{R_1 R_2}{R_1 + R_2}
$$

::: definition
**Ersatzspannungsquelle**

$U_\mathrm{q}$ = Leerlaufspannung, $R_\mathrm{i} = U_\mathrm{q}/I_\mathrm{k}$.
:::

## Komplexe Wechselstromrechnung

| Bauteil | $\underline{Z}$ | $\varphi$ |
|---|---|---|
| $R$ | $R$ | $0^\circ$ |
| $L$ | $\mathrm{j}\omega L$ | $+90^\circ$ |
| $C$ | $1/(\mathrm{j}\omega C)$ | $-90^\circ$ |

::: warning
Effektivwerte von Teilspannungen addieren sich nicht; nur die Zeiger addieren sich.
:::

## RC-Filter

$$
\underline{H}_\mathrm{TP} = \frac{1}{1 + \mathrm{j}\omega RC}, \qquad f_\mathrm{g} = \frac{1}{2\pi RC}
$$

![Betragsgang von Tief- und Hochpass über der normierten Frequenz, mit Asymptoten; −3 dB bei der Grenzfrequenz](fig:cs-bode-asymptoten)

::: note
Bei $f_\mathrm{g}$: $-3\,\mathrm{dB}$, $\mp 45^\circ$. Asymptote: $20\,\mathrm{dB}$ pro Dekade.
:::
