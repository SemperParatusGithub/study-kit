---
topic: wechselstrom
title: Komplexe Wechselstromrechnung
objectives:
  - 'Amplitude, Effektivwert, Frequenz und Nullphase einer Sinusgröße angeben'
  - 'Sinusgrößen gleicher Frequenz als komplexe Zeiger darstellen'
  - 'Die Impedanzen von Widerstand, Spule und Kondensator angeben'
  - 'Impedanzen in Reihe und parallel zusammenfassen'
  - 'Das Zeigerdiagramm einer RL- oder RC-Reihenschaltung zeichnen'
---

## Sinusgrößen

Eine sinusförmige Spannung ist durch ihre Amplitude $\hat{u}$, ihre Kreisfrequenz
$\omega$ und ihren Nullphasenwinkel $\varphi_u$ festgelegt:

$$
u(t) = \hat{u} \cos(\omega t + \varphi_u), \qquad \omega = 2\pi f = \frac{2\pi}{T}
$$

![Sinusspannung mit der Amplitude 10 V, dem Effektivwert 7,07 V und der Periodendauer 1 ms](fig:ws-sinus)

::: definition
**Effektivwert**

Der Effektivwert $U$ ist die Gleichspannung, die an einem Widerstand dieselbe mittlere
Leistung umsetzt wie $u(t)$. Für Sinusgrößen gilt

$$
U = \frac{\hat{u}}{\sqrt{2}} \approx 0{,}707\,\hat{u}
$$
:::

::: warning
**Häufiger Fehler**

Messgeräte und Typenschilder nennen Effektivwerte. Die Netzspannung $U = 230\,\mathrm{V}$
hat die Amplitude $\hat{u} = \sqrt{2} \cdot 230\,\mathrm{V} \approx 325\,\mathrm{V}$. Der
Faktor $\sqrt{2}$ gilt nur für sinusförmige Größen.
:::

Übung: [Kenngrößen einer Sinusspannung](ex:ex-ws-effektivwert)

## Komplexe Zeiger

Rechnungen mit Sinusgrößen gleicher Frequenz werden einfach, wenn man jede Größe durch
einen komplexen Zeiger ersetzt. Hier trägt der Zeiger den Effektivwert und die Nullphase:

$$
u(t) = \hat{u}\cos(\omega t + \varphi_u) \quad \longleftrightarrow \quad \underline{U} = U\,\mathrm{e}^{\mathrm{j}\varphi_u} = U\cos\varphi_u + \mathrm{j}\,U\sin\varphi_u
$$

Der gemeinsame Faktor $\mathrm{e}^{\mathrm{j}\omega t}$ wird weggelassen. Zurück in den
Zeitbereich führt $u(t) = \sqrt{2}\,\mathrm{Re}\{\underline{U}\,\mathrm{e}^{\mathrm{j}\omega t}\}$.

::: note
Zeiger gleicher Frequenz addiert man wie Vektoren in der komplexen Ebene. Der Effektivwert
einer Summe ist nur dann gleich der Summe der Effektivwerte, wenn beide Zeiger in dieselbe
Richtung zeigen.
:::

## Impedanz von R, L und C

Das Verhältnis von Spannungs- und Stromzeiger heißt Impedanz,
$\underline{Z} = \underline{U}/\underline{I}$. Ihr Winkel $\varphi = \varphi_u - \varphi_i$
gibt an, um wie viel die Spannung dem Strom vorauseilt.

| Bauteil | Impedanz $\underline{Z}$ | Betrag $\lvert\underline{Z}\rvert$ | Winkel $\varphi$ |
|---|---|---|---|
| Widerstand | $R$ | $R$ | $0^\circ$ |
| Spule | $\mathrm{j}\omega L$ | $\omega L$ | $+90^\circ$ |
| Kondensator | $\frac{1}{\mathrm{j}\omega C} = -\frac{\mathrm{j}}{\omega C}$ | $\frac{1}{\omega C}$ | $-90^\circ$ |

::: theorem
**Ohmsches Gesetz in komplexer Form**

$$
\underline{U} = \underline{Z} \cdot \underline{I}
$$

In Reihe addieren sich die Impedanzen, parallel die Admittanzen
$\underline{Y} = 1/\underline{Z}$. Es gelten dieselben Regeln wie für Widerstände im
Gleichstromkreis, nur mit komplexen Zahlen.
:::

![Blindwiderstände einer Spule mit 10 mH und eines Kondensators mit 1 µF über der Frequenz; bei 1,59 kHz betragen beide 100 Ω. Gestrichelt zum Vergleich ein Widerstand R = 100 Ω](fig:ws-impedanz-frequenz)

Der Blindwiderstand der Spule wächst mit der Frequenz, der des Kondensators fällt; ein
ohmscher Widerstand hängt nicht von der Frequenz ab. Bei Gleichspannung wirkt die Spule
wie ein Kurzschluss und der Kondensator wie ein Leerlauf; bei sehr hohen Frequenzen ist es
umgekehrt.

::: warning
**Vorzeichen beim Kondensator**

Wegen $1/\mathrm{j} = -\mathrm{j}$ hat die Impedanz des Kondensators einen negativen
Imaginärteil: Am Kondensator eilt die Spannung dem Strom um $90^\circ$ nach, an der Spule
eilt sie um $90^\circ$ vor.
:::

Übungen: [Impedanz einer RC-Reihenschaltung](ex:ex-ws-impedanz-rc),
[Parallelschaltung aus R und C](ex:ex-ws-parallel-rc)

## Zeigerdiagramm einer Reihenschaltung

In einer Reihenschaltung fließt durch alle Bauteile derselbe Strom; deshalb legt man
$\underline{I}$ als Bezugszeiger auf die reelle Achse. Für $R$ und $L$ in Reihe gilt

$$
\underline{Z} = R + \mathrm{j}\omega L, \qquad |\underline{Z}| = \sqrt{R^2 + (\omega L)^2}, \qquad \varphi = \arctan\frac{\omega L}{R}
$$

::: example
**Beispiel**

$R = 30\,\Omega$ und $\omega L = 40\,\Omega$ liegen in Reihe, der Strom beträgt
$I = 2\,\mathrm{A}$. Es ist $|\underline{Z}| = 50\,\Omega$ und $\varphi \approx 53{,}1^\circ$.
Die Teilspannungen $U_R = 60\,\mathrm{V}$ und $U_L = 80\,\mathrm{V}$ ergeben zusammen
$U = 100\,\mathrm{V}$, nicht $140\,\mathrm{V}$.
:::

![Zeigerdiagramm des Beispiels mit dem Strom als Bezugszeiger: Die Teilspannungen 60 V und 80 V ergeben die Gesamtspannung 100 V, die dem Strom um 53,1° vorauseilt](fig:ws-zeiger-rl)

Bei einer RC-Reihenschaltung zeigt $\underline{U}_C$ von der Spitze von $\underline{U}_R$
aus nach unten, und die Gesamtspannung eilt dem Strom nach.

Übungen: [RL-Reihenschaltung am Netz](ex:ex-ws-rl-reihe),
[Zeigerdiagramm einer RC-Reihenschaltung](ex:ex-ws-zeigerdiagramm)

::: takeaways
- Effektivwert einer Sinusgröße: $U = \hat{u}/\sqrt{2}$.
- Ein Zeiger trägt Effektivwert und Nullphase; die Frequenz steckt im gemeinsamen Faktor
  $\mathrm{e}^{\mathrm{j}\omega t}$.
- $\underline{Z}_R = R$, $\underline{Z}_L = \mathrm{j}\omega L$,
  $\underline{Z}_C = 1/(\mathrm{j}\omega C)$.
- Teilspannungen addieren sich als Zeiger, nicht als Beträge.
:::
