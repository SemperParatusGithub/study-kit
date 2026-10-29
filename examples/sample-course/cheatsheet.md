---
title: Formelblatt RC-Netzwerke
max_pages: 2
priority: [rc-filter, wechselstrom, spannungsteiler]
---

## Spannungsteiler und Ersatzquellen

$$
U_2 = U_0 \cdot \frac{R_2}{R_1 + R_2}, \qquad I_1 = I_0 \cdot \frac{R_2}{R_1 + R_2}, \qquad R_1 \parallel R_2 = \frac{R_1 R_2}{R_1 + R_2}
$$

Belasteter Teiler: $R_2$ durch $R_2 \parallel R_\mathrm{L}$ ersetzen, in Zähler und Nenner.

::: definition
**Ersatzspannungsquelle**

$U_\mathrm{q}$ = Leerlaufspannung an A–B. $R_\mathrm{i}$ = Widerstand an A–B mit
kurzgeschlossenen Spannungsquellen und offenen Stromquellen; $R_\mathrm{i} = U_\mathrm{q}/I_\mathrm{k}$.
:::

$$
U_\mathrm{L} = U_\mathrm{q} \cdot \frac{R_\mathrm{L}}{R_\mathrm{i} + R_\mathrm{L}}, \qquad P_\mathrm{max} = \frac{U_\mathrm{q}^2}{4R_\mathrm{i}} \quad \text{bei } R_\mathrm{L} = R_\mathrm{i}
$$

## Komplexe Wechselstromrechnung

$$
\omega = 2\pi f = \frac{2\pi}{T}, \qquad U = \frac{\hat{u}}{\sqrt{2}}, \qquad \underline{U} = U\,\mathrm{e}^{\mathrm{j}\varphi_u}, \qquad \underline{Z} = \frac{\underline{U}}{\underline{I}}, \qquad \varphi = \varphi_u - \varphi_i
$$

| Bauteil | $\underline{Z}$ | $\varphi$ | $f \to 0$ | $f \to \infty$ |
|---|---|---|---|---|
| $R$ | $R$ | $0^\circ$ | $R$ | $R$ |
| $L$ | $\mathrm{j}\omega L$ | $+90^\circ$ | Kurzschluss | Leerlauf |
| $C$ | $1/(\mathrm{j}\omega C) = -\mathrm{j}/(\omega C)$ | $-90^\circ$ | Leerlauf | Kurzschluss |

Reihe: $\underline{Z} = \underline{Z}_1 + \underline{Z}_2$. Parallel:
$\underline{Y} = \underline{Y}_1 + \underline{Y}_2$ mit $\underline{Y} = 1/\underline{Z}$.
Betrag und Winkel: $|a + \mathrm{j}b| = \sqrt{a^2 + b^2}$, $\arg = \arctan(b/a)$ für $a > 0$.

::: warning
Effektivwerte von Teilspannungen addieren sich nicht; nur die Zeiger addieren sich.
:::

## RC-Filter

$$
\underline{H}_\mathrm{TP} = \frac{1}{1 + \mathrm{j}\omega RC}, \qquad \underline{H}_\mathrm{HP} = \frac{\mathrm{j}\omega RC}{1 + \mathrm{j}\omega RC}, \qquad f_\mathrm{g} = \frac{1}{2\pi RC}, \qquad \omega_\mathrm{g} = \frac{1}{\tau}
$$

Mit $x = f/f_\mathrm{g}$: Tiefpass $|\underline{H}| = 1/\sqrt{1 + x^2}$,
$\varphi = -\arctan x$; Hochpass $|\underline{H}| = x/\sqrt{1 + x^2}$,
$\varphi = 90^\circ - \arctan x$.

![Betragsgang von Tief- und Hochpass über f/fg mit Asymptoten; −3 dB bei fg](fig:cs-bode-asymptoten)

::: note
Bei $f_\mathrm{g}$: $-3\,\mathrm{dB}$, $\mp 45^\circ$. Asymptote: $20\,\mathrm{dB}$ pro Dekade.
Phase: Gerade von $f_\mathrm{g}/10$ bis $10\,f_\mathrm{g}$.
Dezibel: $20\lg 2 \approx 6\,\mathrm{dB}$, $20\lg 10 = 20\,\mathrm{dB}$.
:::

Sprungantwort ($\tau = RC$, $C$ anfangs ungeladen):

$$
u_C(t) = U_0\left(1 - \mathrm{e}^{-t/\tau}\right), \qquad i(t) = \frac{U_0}{R}\,\mathrm{e}^{-t/\tau}, \qquad t = -\tau \ln\left(1 - \frac{u_C}{U_0}\right)
$$

| $t$ | $\tau$ | $2\tau$ | $3\tau$ | $5\tau$ |
|---|---|---|---|---|
| $u_C/U_0$ | $63{,}2\,\%$ | $86{,}5\,\%$ | $95{,}0\,\%$ | $99{,}3\,\%$ |

::: warning
Last am Ausgang: $\underline{H}(0) = R_\mathrm{L}/(R + R_\mathrm{L})$ und
$\tau' = (R \parallel R_\mathrm{L})\,C$. Nicht $\omega_\mathrm{g}$ mit $f_\mathrm{g}$
verwechseln: Faktor $2\pi$.
:::
