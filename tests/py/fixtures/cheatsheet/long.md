---
title: Formelblatt
max_pages: 1
priority: [rc-tiefpass, spannungsteiler]
---

## Spannungsteiler

$$
U_2 = U_0 \cdot \frac{R_2}{R_1 + R_2}, \qquad U_1 = U_0 \cdot \frac{R_1}{R_1 + R_2}, \qquad \frac{U_1}{U_2} = \frac{R_1}{R_2}
$$

Belasteter Teiler: $R_2$ durch $R_2 \parallel R_\mathrm{L}$ ersetzen, in Zähler und Nenner.
Die Ausgangsspannung sinkt mit kleiner werdendem $R_\mathrm{L}$; für
$R_\mathrm{L} \gg R_2$ gilt wieder die Formel des unbelasteten Teilers.

$$
U_2 = U_0 \cdot \frac{R_2 \parallel R_\mathrm{L}}{R_1 + R_2 \parallel R_\mathrm{L}}, \qquad R_2 \parallel R_\mathrm{L} = \frac{R_2 R_\mathrm{L}}{R_2 + R_\mathrm{L}}
$$

::: definition
**Querstromverhältnis**

$q = I_\mathrm{q}/I_\mathrm{L}$: Verhältnis des Stroms durch $R_2$ zum Laststrom. Ein
großes $q$ macht die Ausgangsspannung lastunabhängig, kostet aber Verlustleistung.
:::

| Größe | unbelastet | belastet |
|---|---|---|
| $U_2$ | $U_0 R_2/(R_1 + R_2)$ | $U_0 R_{2\mathrm{L}}/(R_1 + R_{2\mathrm{L}})$ |
| $I_1$ | $U_0/(R_1 + R_2)$ | $U_0/(R_1 + R_{2\mathrm{L}})$ |
| $P_\mathrm{ges}$ | $U_0^2/(R_1 + R_2)$ | $U_0^2/(R_1 + R_{2\mathrm{L}})$ |

## Stromteiler

$$
I_1 = I_0 \cdot \frac{R_2}{R_1 + R_2}, \qquad I_2 = I_0 \cdot \frac{R_1}{R_1 + R_2}, \qquad \frac{I_1}{I_2} = \frac{R_2}{R_1} = \frac{G_1}{G_2}
$$

Mit Leitwerten: $I_k = I_0 \cdot G_k / \sum G$. Der größere Strom fließt durch den
kleineren Widerstand. Parallelschaltung: $G = G_1 + G_2$, $R = R_1 R_2/(R_1 + R_2)$.

::: note
Bei drei oder mehr Zweigen nur noch mit Leitwerten rechnen:
$I_k = I_0 \cdot G_k/(G_1 + G_2 + G_3)$.
:::

## Ersatzquellen

::: definition
**Ersatzspannungsquelle**

$U_\mathrm{q}$ = Leerlaufspannung an A–B. $R_\mathrm{i}$ = Widerstand an A–B mit
kurzgeschlossenen Spannungsquellen und offenen Stromquellen; $R_\mathrm{i} = U_\mathrm{q}/I_\mathrm{k}$.
:::

$$
U_\mathrm{L} = U_\mathrm{q} \cdot \frac{R_\mathrm{L}}{R_\mathrm{i} + R_\mathrm{L}}, \qquad I_\mathrm{L} = \frac{U_\mathrm{q}}{R_\mathrm{i} + R_\mathrm{L}}, \qquad P_\mathrm{L} = I_\mathrm{L}^2 R_\mathrm{L}
$$

$$
P_\mathrm{max} = \frac{U_\mathrm{q}^2}{4R_\mathrm{i}} \quad \text{bei } R_\mathrm{L} = R_\mathrm{i}, \qquad \eta = \frac{R_\mathrm{L}}{R_\mathrm{i} + R_\mathrm{L}}
$$

Ersatzstromquelle: $I_\mathrm{q} = I_\mathrm{k} = U_\mathrm{q}/R_\mathrm{i}$ parallel zu
$R_\mathrm{i}$. Beide Ersatzquellen verhalten sich an den Klemmen gleich, nicht aber im
Inneren: die Verlustleistung in $R_\mathrm{i}$ ist verschieden.

::: warning
Bei der Leistungsanpassung ist der Wirkungsgrad nur $50\,\%$.
:::

## Knoten und Maschen

$$
\sum_k I_k = 0 \quad \text{(Knoten)}, \qquad \sum_k U_k = 0 \quad \text{(Masche)}, \qquad U = R I
$$

Vorgehen: Zählpfeile festlegen, $k - 1$ Knotengleichungen und $z - (k - 1)$ unabhängige
Maschengleichungen aufstellen, dann das lineare Gleichungssystem lösen.

| Verfahren | Unbekannte | Gleichungen |
|---|---|---|
| Zweigstrom | $z$ Ströme | $z$ |
| Maschenstrom | $z - k + 1$ Ströme | $z - k + 1$ |
| Knotenpotential | $k - 1$ Potentiale | $k - 1$ |

## Wechselgrößen

$$
\omega = 2\pi f = \frac{2\pi}{T}, \qquad U = \frac{\hat{u}}{\sqrt{2}}, \qquad \underline{U} = U\,\mathrm{e}^{\mathrm{j}\varphi_u}, \qquad \underline{Z} = \frac{\underline{U}}{\underline{I}}
$$

| Bauteil | $\underline{Z}$ | $\varphi$ | $f \to 0$ | $f \to \infty$ |
|---|---|---|---|---|
| $R$ | $R$ | $0^\circ$ | $R$ | $R$ |
| $L$ | $\mathrm{j}\omega L$ | $+90^\circ$ | Kurzschluss | Leerlauf |
| $C$ | $1/(\mathrm{j}\omega C)$ | $-90^\circ$ | Leerlauf | Kurzschluss |

Reihe: $\underline{Z} = \underline{Z}_1 + \underline{Z}_2$. Parallel:
$\underline{Y} = \underline{Y}_1 + \underline{Y}_2$ mit $\underline{Y} = 1/\underline{Z}$.
Betrag und Winkel: $|a + \mathrm{j}b| = \sqrt{a^2 + b^2}$, $\arg = \arctan(b/a)$ für $a > 0$.

::: warning
Effektivwerte von Teilspannungen addieren sich nicht; nur die Zeiger addieren sich.
:::

## Leistung

$$
P = U I \cos\varphi, \qquad Q = U I \sin\varphi, \qquad S = U I = \sqrt{P^2 + Q^2}, \qquad \underline{S} = \underline{U}\,\underline{I}^*
$$

Leistungsfaktor $\lambda = P/S = \cos\varphi$. Blindleistung induktiv positiv, kapazitiv
negativ. Kompensation: $Q_C = P(\tan\varphi_1 - \tan\varphi_2)$ und
$C = Q_C/(\omega U^2)$.

::: definition
**Wirkleistung am Widerstand**

$P = U^2/R = I^2 R$; nur der Wirkanteil von $\underline{Z}$ setzt Leistung um.
:::

## RC-Tiefpass

$$
\underline{H} = \frac{1}{1 + \mathrm{j}\omega RC}, \qquad |\underline{H}| = \frac{1}{\sqrt{1 + (\omega RC)^2}}, \qquad \varphi = -\arctan(\omega RC)
$$

$$
f_\mathrm{g} = \frac{1}{2\pi RC}, \qquad \omega_\mathrm{g} = \frac{1}{\tau}, \qquad \tau = RC
$$

Mit $x = f/f_\mathrm{g}$: $|\underline{H}| = 1/\sqrt{1 + x^2}$, $\varphi = -\arctan x$.
Oberhalb von $f_\mathrm{g}$ fällt der Betrag mit $20\,\mathrm{dB}$ pro Dekade.

::: note
Bei $f_\mathrm{g}$: $-3\,\mathrm{dB}$ und $-45^\circ$. Asymptoten: waagrecht bis
$f_\mathrm{g}$, dann $-20\,\mathrm{dB}$ pro Dekade.
:::

| $f/f_\mathrm{g}$ | $0{,}1$ | $1$ | $10$ | $100$ |
|---|---|---|---|---|
| $\lvert\underline{H}\rvert$ in dB | $-0{,}04$ | $-3{,}01$ | $-20{,}04$ | $-40{,}00$ |
| $\varphi$ | $-5{,}7^\circ$ | $-45^\circ$ | $-84{,}3^\circ$ | $-89{,}4^\circ$ |

## RC-Hochpass

$$
\underline{H} = \frac{\mathrm{j}\omega RC}{1 + \mathrm{j}\omega RC}, \qquad |\underline{H}| = \frac{\omega RC}{\sqrt{1 + (\omega RC)^2}}, \qquad \varphi = 90^\circ - \arctan(\omega RC)
$$

Mit $x = f/f_\mathrm{g}$: $|\underline{H}| = x/\sqrt{1 + x^2}$. Unterhalb von
$f_\mathrm{g}$ steigt der Betrag mit $20\,\mathrm{dB}$ pro Dekade.

::: warning
Hochpass und Tiefpass haben dieselbe Grenzfrequenz, aber entgegengesetzte Phasenlage.
:::

## Sprungantwort

$$
u_C(t) = U_0\left(1 - \mathrm{e}^{-t/\tau}\right), \qquad i(t) = \frac{U_0}{R}\,\mathrm{e}^{-t/\tau}, \qquad t = -\tau \ln\left(1 - \frac{u_C}{U_0}\right)
$$

| $t$ | $\tau$ | $2\tau$ | $3\tau$ | $5\tau$ |
|---|---|---|---|---|
| $u_C/U_0$ | $63{,}2\,\%$ | $86{,}5\,\%$ | $95{,}0\,\%$ | $99{,}3\,\%$ |

Entladen: $u_C(t) = U_0\,\mathrm{e}^{-t/\tau}$. Nach $5\tau$ gilt der Vorgang als
abgeschlossen. Die Tangente im Nullpunkt schneidet den Endwert bei $t = \tau$.

## Belasteter Ausgang

$$
\underline{H}(0) = \frac{R_\mathrm{L}}{R + R_\mathrm{L}}, \qquad \tau' = (R \parallel R_\mathrm{L})\,C, \qquad f_\mathrm{g}' = \frac{1}{2\pi \tau'}
$$

::: warning
Last am Ausgang senkt die Gleichspannungsverstärkung und verschiebt die Grenzfrequenz nach
oben. Nicht $\omega_\mathrm{g}$ mit $f_\mathrm{g}$ verwechseln: Faktor $2\pi$.
:::
