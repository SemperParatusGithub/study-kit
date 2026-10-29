---
topic: rc-filter
title: RC-Filter und Bode-Diagramm
objectives:
  - 'Die Übertragungsfunktion von RC-Tiefpass und RC-Hochpass mit der Spannungsteilerregel herleiten'
  - 'Die Grenzfrequenz $f_\mathrm{g}$ berechnen und ihre Bedeutung erklären'
  - 'Betrags- und Phasengang im Bode-Diagramm mit Asymptoten skizzieren'
  - 'Die Sprungantwort eines RC-Glieds mit der Zeitkonstante $\tau = RC$ beschreiben'
---

## RC-Tiefpass

![RC-Tiefpass als Vierpol: R im Längszweig, C im Querzweig](fig:rc-tp-schaltung)

Der Tiefpass ist ein [Spannungsteiler](topic:spannungsteiler) aus $R$ und der Impedanz
$1/(\mathrm{j}\omega C)$ des Kondensators, gerechnet mit
[komplexen Zeigern](topic:wechselstrom). Bei unbelastetem Ausgang gilt

$$
\underline{H}(\mathrm{j}\omega) = \frac{\underline{U}_\mathrm{a}}{\underline{U}_\mathrm{e}} = \frac{\frac{1}{\mathrm{j}\omega C}}{R + \frac{1}{\mathrm{j}\omega C}} = \frac{1}{1 + \mathrm{j}\omega RC}
$$

Daraus folgen Betrag und Phase:

$$
|\underline{H}| = \frac{1}{\sqrt{1 + (\omega RC)^2}}, \qquad \varphi = -\arctan(\omega RC)
$$

Bei tiefen Frequenzen wirkt der Kondensator wie ein Leerlauf und $|\underline{H}| \to 1$;
bei hohen Frequenzen schließt er den Ausgang kurz und $|\underline{H}| \to 0$.

## Grenzfrequenz

::: definition
**Grenzfrequenz**

Bei der Grenzfrequenz ist der Blindwiderstand des Kondensators so groß wie $R$. Dort gilt
$|\underline{H}| = 1/\sqrt{2}$, also $-3\,\mathrm{dB}$, und $\varphi = -45^\circ$:

$$
\omega_\mathrm{g} = \frac{1}{RC} = \frac{1}{\tau}, \qquad f_\mathrm{g} = \frac{1}{2\pi RC}
$$
:::

::: warning
**Häufiger Fehler**

$\omega_\mathrm{g}$ und $f_\mathrm{g}$ unterscheiden sich um den Faktor $2\pi$. Für
$R = 1\,\mathrm{k\Omega}$ und $C = 100\,\mathrm{nF}$ ist
$\omega_\mathrm{g} = 10^4\,\mathrm{s^{-1}}$, aber $f_\mathrm{g} \approx 1{,}59\,\mathrm{kHz}$.
:::

Übungen: [Grenzfrequenz eines RC-Tiefpasses](ex:ex-rc-tp-grenzfrequenz),
[Tiefpass aus einer Messung bestimmen](ex:ex-rc-tp-messung)

## Bode-Diagramm

Das Bode-Diagramm zeigt den Betrag in Dezibel, $20\lg|\underline{H}|$, und die Phase über
einer logarithmischen Frequenzachse. Den Betragsgang des Tiefpasses nähern zwei Geraden
an:

- unterhalb von $f_\mathrm{g}$ waagerecht bei $0\,\mathrm{dB}$,
- oberhalb von $f_\mathrm{g}$ fallend mit $20\,\mathrm{dB}$ pro Dekade.

Am weitesten weicht der wahre Verlauf bei $f_\mathrm{g}$ von den Asymptoten ab, nämlich um
$3\,\mathrm{dB}$. Die Phase läuft von $0^\circ$ über $-45^\circ$ bei $f_\mathrm{g}$ nach
$-90^\circ$; ihre Asymptote verbindet $0^\circ$ bei $f_\mathrm{g}/10$ geradlinig mit
$-90^\circ$ bei $10\,f_\mathrm{g}$.

![Bode-Diagramm des RC-Tiefpasses mit R = 1 kΩ und C = 100 nF, Grenzfrequenz 1,59 kHz; gestrichelt die Asymptoten](fig:rc-tp-bode)

Übung: [Bode-Diagramm eines Tiefpasses](ex:ex-rc-tp-bode)

## RC-Hochpass

![RC-Hochpass als Vierpol: C im Längszweig, R im Querzweig](fig:rc-hp-schaltung)

Vertauscht man $R$ und $C$, entsteht ein Hochpass:

$$
\underline{H}(\mathrm{j}\omega) = \frac{R}{R + \frac{1}{\mathrm{j}\omega C}} = \frac{\mathrm{j}\omega RC}{1 + \mathrm{j}\omega RC}
$$

Die Grenzfrequenz ist dieselbe, $f_\mathrm{g} = 1/(2\pi RC)$. Unterhalb von $f_\mathrm{g}$
steigt der Betrag mit $20\,\mathrm{dB}$ pro Dekade, darüber bleibt er nahe
$0\,\mathrm{dB}$. Die Phase läuft von $+90^\circ$ über $+45^\circ$ bei $f_\mathrm{g}$ nach
$0^\circ$. Der Kondensator im Längszweig sperrt Gleichspannung.

![Bode-Diagramm des RC-Hochpasses mit R = 1 kΩ und C = 100 nF, Grenzfrequenz 1,59 kHz](fig:rc-hp-bode)

Übung: [Hochpass dimensionieren](ex:ex-rc-hp-dimensionieren)

## Zeitkonstante und Sprungantwort

Springt die Eingangsspannung eines RC-Tiefpasses zum Zeitpunkt $t = 0$ von $0$ auf $U_0$,
lädt sich der zunächst ungeladene Kondensator exponentiell auf:

$$
u_C(t) = U_0 \left(1 - \mathrm{e}^{-t/\tau}\right), \qquad i(t) = \frac{U_0}{R}\,\mathrm{e}^{-t/\tau}, \qquad \tau = RC
$$

![Normierte Ladekurve eines Kondensators: 63,2 % des Endwerts nach τ, 99,3 % nach 5τ](fig:rc-sprungantwort)

| Zeit $t$ | $\tau$ | $2\tau$ | $3\tau$ | $5\tau$ |
|---|---|---|---|---|
| $u_C/U_0$ | $63{,}2\,\%$ | $86{,}5\,\%$ | $95{,}0\,\%$ | $99{,}3\,\%$ |

::: note
**Tangentenregel**

Die Tangente an $u_C(t)$ im Ursprung erreicht den Endwert $U_0$ genau nach der Zeit
$\tau$. So liest man $\tau$ aus einem gemessenen Verlauf ab. Nach etwa $5\tau$ gilt der
Kondensator als vollständig geladen. Zeitkonstante und Grenzfrequenz hängen über
$\tau = 1/\omega_\mathrm{g}$ zusammen.
:::

Übung: [Sprungantwort eines RC-Glieds](ex:ex-rc-sprungantwort)

## Belasteter Ausgang

Eine Last $R_\mathrm{L}$ am Ausgang liegt parallel zum Kondensator. Mit der
[Ersatzspannungsquelle](topic:spannungsteiler) bezüglich der Kondensatorklemmen sieht der
Kondensator die Quellspannung $\underline{U}_\mathrm{e} \cdot R_\mathrm{L}/(R + R_\mathrm{L})$
und den Innenwiderstand $R \parallel R_\mathrm{L}$:

$$
\underline{H}(\mathrm{j}\omega) = \frac{R_\mathrm{L}}{R + R_\mathrm{L}} \cdot \frac{1}{1 + \mathrm{j}\omega\,(R \parallel R_\mathrm{L})\,C}
$$

Die Last senkt also die Verstärkung im Durchlassbereich und erhöht die Grenzfrequenz.

::: warning
**Häufiger Fehler**

$f_\mathrm{g} = 1/(2\pi RC)$ gilt nur für den unbelasteten Tiefpass. Sobald am Ausgang
etwas angeschlossen ist, gehört der Lastwiderstand in die Rechnung.
:::

Übung: [Belasteter RC-Tiefpass](ex:ex-rc-tp-belastet)

::: takeaways
- Tiefpass: $\underline{H} = 1/(1 + \mathrm{j}\omega RC)$; Hochpass:
  $\underline{H} = \mathrm{j}\omega RC/(1 + \mathrm{j}\omega RC)$.
- Bei $f_\mathrm{g} = 1/(2\pi RC)$ beträgt der Betrag $-3\,\mathrm{dB}$ und die Phase
  $-45^\circ$ beim Tiefpass, $+45^\circ$ beim Hochpass.
- Filter erster Ordnung: Die Asymptote hat die Steigung $20\,\mathrm{dB}$ pro Dekade.
- Sprungantwort: $63\,\%$ des Endwerts nach $\tau$, praktisch eingeschwungen nach $5\tau$.
- Eine Last am Ausgang verändert Verstärkung und Grenzfrequenz.
:::
