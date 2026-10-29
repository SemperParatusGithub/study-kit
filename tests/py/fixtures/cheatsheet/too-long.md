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

## Spule und Kondensator

$$
u_L = L\,\frac{\mathrm{d}i}{\mathrm{d}t}, \qquad i_C = C\,\frac{\mathrm{d}u}{\mathrm{d}t}, \qquad W_L = \frac{1}{2} L I^2, \qquad W_C = \frac{1}{2} C U^2
$$

Reihe von Kondensatoren: $1/C = 1/C_1 + 1/C_2$. Parallel: $C = C_1 + C_2$. Spulen
verhalten sich wie Widerstände: Reihe addiert, parallel wie $R_1 \parallel R_2$.

| Bauteil | Gleichstrom, eingeschwungen | Sprung im ersten Moment |
|---|---|---|
| $C$ | Leerlauf | Kurzschluss |
| $L$ | Kurzschluss | Leerlauf |

::: warning
Die Spannung am Kondensator und der Strom durch die Spule springen nie.
:::

## RL-Glied

$$
\tau = \frac{L}{R}, \qquad i_L(t) = \frac{U_0}{R}\left(1 - \mathrm{e}^{-t/\tau}\right), \qquad u_L(t) = U_0\,\mathrm{e}^{-t/\tau}
$$

$$
\underline{H}_\mathrm{TP} = \frac{R}{R + \mathrm{j}\omega L}, \qquad f_\mathrm{g} = \frac{R}{2\pi L}, \qquad \underline{H}_\mathrm{HP} = \frac{\mathrm{j}\omega L}{R + \mathrm{j}\omega L}
$$

Beim RL-Glied liegt der Tiefpassausgang am Widerstand, der Hochpassausgang an der Spule;
beim RC-Glied ist es umgekehrt.

::: note
Abschalten einer Spule ohne Freilaufdiode erzeugt eine hohe Induktionsspannung.
:::

## Reihenschwingkreis

$$
\underline{Z} = R + \mathrm{j}\left(\omega L - \frac{1}{\omega C}\right), \qquad \omega_0 = \frac{1}{\sqrt{LC}}, \qquad Q = \frac{1}{R}\sqrt{\frac{L}{C}}
$$

$$
B = \frac{f_0}{Q}, \qquad f_{1,2} = f_0\left(\sqrt{1 + \frac{1}{4Q^2}} \mp \frac{1}{2Q}\right), \qquad U_L(\omega_0) = Q\,U
$$

Bei Resonanz ist $\underline{Z} = R$ rein reell und der Strom maximal. Unterhalb von
$\omega_0$ wirkt der Kreis kapazitiv, oberhalb induktiv.

::: definition
**Güte**

$Q$ ist das Verhältnis von Blindleistung zu Wirkleistung bei Resonanz; eine hohe Güte
bedeutet eine schmale Resonanzkurve.
:::

## Parallelschwingkreis

$$
\underline{Y} = G + \mathrm{j}\left(\omega C - \frac{1}{\omega L}\right), \qquad \omega_0 = \frac{1}{\sqrt{LC}}, \qquad Q = R\sqrt{\frac{C}{L}}
$$

Bei Resonanz ist der Leitwert minimal und die Spannung maximal; die Ströme in $L$ und $C$
sind $Q$-mal so groß wie der Gesamtstrom.

| Kreis | bei Resonanz | unterhalb | oberhalb |
|---|---|---|---|
| Reihe | $\lvert\underline{Z}\rvert$ minimal | kapazitiv | induktiv |
| Parallel | $\lvert\underline{Z}\rvert$ maximal | induktiv | kapazitiv |

## Drehstrom

$$
U_\mathrm{L} = \sqrt{3}\,U_\mathrm{Str}, \qquad P = \sqrt{3}\,U_\mathrm{L} I_\mathrm{L} \cos\varphi, \qquad S = \sqrt{3}\,U_\mathrm{L} I_\mathrm{L}
$$

Stern: $I_\mathrm{L} = I_\mathrm{Str}$. Dreieck: $I_\mathrm{L} = \sqrt{3}\,I_\mathrm{Str}$
und $U_\mathrm{L} = U_\mathrm{Str}$. Umschalten von Dreieck auf Stern drittelt die
Leistung.

::: warning
Im Vierleiternetz führt der Neutralleiter bei symmetrischer Last keinen Strom.
:::

## Messtechnik

$$
R_\mathrm{V} = R_\mathrm{i}\left(\frac{U_\mathrm{max}}{U_\mathrm{M}} - 1\right), \qquad R_\mathrm{P} = \frac{R_\mathrm{i}}{I_\mathrm{max}/I_\mathrm{M} - 1}, \qquad F = \frac{x_\mathrm{gem} - x_\mathrm{w}}{x_\mathrm{w}}
$$

Spannungsrichtig messen bei kleinen, stromrichtig bei großen Widerständen. Der
Innenwiderstand eines Spannungsmessers soll groß, der eines Strommessers klein sein.

| Fehler | Ursache | Abhilfe |
|---|---|---|
| systematisch | Messgerät belastet | Schaltung wählen, korrigieren |
| zufällig | Ablesen, Rauschen | mehrfach messen, mitteln |

## Operationsverstärker

$$
V_\mathrm{inv} = -\frac{R_2}{R_1}, \qquad V_\mathrm{nicht} = 1 + \frac{R_2}{R_1}, \qquad u_\mathrm{a} = -\frac{1}{RC}\int u_\mathrm{e}\,\mathrm{d}t
$$

Idealer OPV: $U_\mathrm{D} = 0$ bei Gegenkopplung, keine Eingangsströme, Ausgang begrenzt
durch die Versorgungsspannung. Addierer: $u_\mathrm{a} = -R_2 \left(u_1/R_1 + u_2/R_3\right)$.

| Schaltung | Verstärkung | Eingangswiderstand |
|---|---|---|
| invertierend | $-R_2/R_1$ | $R_1$ |
| nichtinvertierend | $1 + R_2/R_1$ | sehr groß |
| Impedanzwandler | $1$ | sehr groß |

::: warning
Ohne Gegenkopplung arbeitet der OPV als Komparator und geht in die Sättigung.
:::

## Diode

$$
I_\mathrm{D} = I_\mathrm{S}\left(\mathrm{e}^{U_\mathrm{D}/(n U_\mathrm{T})} - 1\right), \qquad U_\mathrm{T} = \frac{k T}{e} \approx 25{,}9\,\mathrm{mV}, \qquad r_\mathrm{d} = \frac{n U_\mathrm{T}}{I_\mathrm{D}}
$$

Ersatzschaltung im Durchlass: Spannungsquelle $U_\mathrm{F} \approx 0{,}7\,\mathrm{V}$ in
Reihe mit $r_\mathrm{d}$. Sperrrichtung: nur der kleine Sperrstrom fließt, bis zur
Durchbruchspannung.

::: note
Gleichrichter: Einweg liefert $\bar{u} = \hat{u}/\pi$, Brücke $\bar{u} = 2\hat{u}/\pi$,
jeweils ohne Durchlassspannung gerechnet.
:::

## Transistor

$$
I_\mathrm{C} = B\,I_\mathrm{B}, \qquad I_\mathrm{E} = I_\mathrm{C} + I_\mathrm{B}, \qquad V_u \approx -\frac{R_\mathrm{C}}{R_\mathrm{E}}, \qquad g_\mathrm{m} = \frac{I_\mathrm{C}}{U_\mathrm{T}}
$$

Arbeitspunkt: Basisspannungsteiler mit Querstrom etwa $10\,I_\mathrm{B}$, Emitterwiderstand
für die Stabilität. Kleinsignal: $r_\mathrm{BE} = \beta/g_\mathrm{m}$.

| Grundschaltung | Spannungsverstärkung | Phasenlage |
|---|---|---|
| Emitter | groß | $180^\circ$ |
| Kollektor | etwa $1$ | $0^\circ$ |
| Basis | groß | $0^\circ$ |

## Fourierreihe

$$
f(t) = \frac{a_0}{2} + \sum_{k=1}^{\infty} \left(a_k \cos(k\omega t) + b_k \sin(k\omega t)\right), \qquad a_k = \frac{2}{T}\int_0^T f(t)\cos(k\omega t)\,\mathrm{d}t
$$

Gerade Funktionen haben nur Kosinusanteile, ungerade nur Sinusanteile. Rechteck mit
Amplitude $\hat{u}$: $b_k = 4\hat{u}/(k\pi)$ für ungerade $k$, sonst null.

::: definition
**Effektivwert einer Mischgröße**

$U = \sqrt{U_0^2 + U_1^2 + U_2^2 + \dots}$ aus Gleichanteil und den Effektivwerten der
Oberschwingungen.
:::
