---
topic: verstaerker-grundschaltungen
title: 'Invertierender und nichtinvertierender Verstärker, Spannungsfolger und Summierer'
objectives:
  - 'Die Verstärkung des invertierenden Verstärkers mit der Knotenregel an der virtuellen Masse herleiten und berechnen'
  - 'Die Aussteuergrenze bestimmen und die Ausgangsspannung in der Sättigung angeben'
  - 'Den Einfluss eines Quellen-Innenwiderstands $R_i$ auf die Verstärkung berechnen'
  - 'Einen nichtinvertierenden Verstärker für eine Zielverstärkung dimensionieren'
  - 'Den Spannungsfolger als Impedanzwandler zwischen hochohmiger Quelle und Last begründen'
  - 'Die Ausgangsspannung eines Summierers aus den Eingangsströmen berechnen'
sources:
  - {doc: vl03-operationsverstaerker-grundschaltungen, pages: '5-10'}
  - {doc: skript-kapitel4-operationsverstaerker, pages: '1-2'}
  - {doc: uebung03-opv-grundschaltungen, pages: 1}
  - {doc: klausur-ws2025-26, pages: '1-2'}
---

Alle Schaltungen folgen aus den zwei Regeln des [idealen OPV](topic:idealer-opv) im
linearen Bereich: $I_p = I_n = 0$ und $U_p = U_n$. Vorgehen: Knotenregel am invertierenden
Eingang aufstellen, nach $U_a$ auflösen, erst dann Zahlen einsetzen.

## Invertierender Verstärker

![Invertierender Verstärker: Eingang über R1, Rückkopplung über R2, nichtinvertierender Eingang auf Masse](fig:verstaerker-grundschaltungen-invertierer)

Die Eingangsspannung liegt über $R_1$ am invertierenden Eingang, $R_2$ koppelt den Ausgang
dorthin zurück, und der nichtinvertierende Eingang liegt auf Masse,
siehe Folie 5. Wegen $U_p = 0$ und
$U_d = 0$ ist auch $U_n = 0$: Der invertierende Eingang ist eine **virtuelle Masse**. Der
Strom $I_e = U_e/R_1$ kann nicht in den OPV fließen ($I_n = 0$), also fließt er vollständig
durch $R_2$ weiter. Die Knotenregel am invertierenden Eingang lautet
nach Folie 6:

$$
\frac{U_e - 0}{R_1} + \frac{U_a - 0}{R_2} = 0 \quad\Rightarrow\quad V = \frac{U_a}{U_e} = -\frac{R_2}{R_1}
$$

::: definition
**Eingangswiderstand des invertierenden Verstärkers**

Die Quelle sieht $R_1$ gegen die virtuelle Masse, also

$$
R_\mathrm{ein} = \frac{U_e}{I_e} = R_1
$$

Der Eingangswiderstand ist endlich und belastet die Quelle.
:::

Das Minuszeichen heißt: Ausgang und Eingang sind gegenphasig ($180^\circ$). $V$ hängt nur
von den Widerständen ab, nicht von $V_0$; mit $R_2 < R_1$ wird abgeschwächt.

::: example
**Beispiel: Verstärkung, Ausgangsspannung und Eingangsstrom**

Mit $R_1 = 12\,\mathrm{k\Omega}$, $R_2 = 68\,\mathrm{k\Omega}$ und $U_e = 0.25\,\mathrm{V}$:

$$
V = -\frac{68\,\mathrm{k\Omega}}{12\,\mathrm{k\Omega}} \approx -5.667, \qquad U_a = V \cdot U_e \approx -1.417\,\mathrm{V}
$$

Der Eingangsstrom ist $I_e = 0.25\,\mathrm{V}/12\,\mathrm{k\Omega} \approx 20.83\,\mathrm{\mu A}$.
Derselbe Strom fließt durch $R_2$: $U_a = -R_2 \cdot I_e \approx -1.417\,\mathrm{V}$.
:::

::: warning
**Häufige Fehler**

Das Minuszeichen fehlt im Ergebnis, oder $R_1$ und $R_2$ werden vertauscht
($V = -R_1/R_2$). Merke: Der Rückkopplungswiderstand $R_2$ steht im Zähler. Ebenso falsch
ist ein unendlicher Eingangswiderstand: Der gilt für den nichtinvertierenden Verstärker,
hier ist $R_\mathrm{ein} = R_1$.
:::

Übung: [Kennwerte eines invertierenden Verstärkers](ex:ex-vg-invertierer-kennwerte)

## Aussteuergrenze und Sättigung

Der Ausgang kann nicht über die Sättigungsspannung $\pm U_\mathrm{sat}$ hinaus, die etwas
unter der Versorgung $\pm U_B$ liegt. Die Formel $U_a = V \cdot U_e$ gilt deshalb nur bis zur
**Aussteuergrenze**,
siehe Folie 7:

$$
|U_e|_\mathrm{max} = \frac{U_\mathrm{sat}}{|V|}
$$

![Übertragungskennlinie des invertierenden Verstärkers: Gerade mit Steigung V zwischen den Aussteuergrenzen, außerhalb konstant bei plus oder minus Usat](fig:verstaerker-grundschaltungen-kennlinie)

::: theorem
**Ausgangsspannung in der Sättigung**

Ist $|V \cdot U_e| > U_\mathrm{sat}$, bleibt der Ausgang an der Grenze stehen, mit dem
Vorzeichen des rechnerischen Werts:

$$
U_a = \begin{cases} V \cdot U_e, & |V \cdot U_e| \le U_\mathrm{sat} \\ U_\mathrm{sat} \cdot \mathrm{sgn}(V \cdot U_e), & |V \cdot U_e| > U_\mathrm{sat} \end{cases}
$$

In der Sättigung gilt $U_d = 0$ nicht mehr; die virtuelle Masse geht verloren.
:::

::: example
**Beispiel: Sättigung**

Dieselbe Schaltung ($V \approx -5.667$) an $\pm U_\mathrm{sat} = \pm 12\,\mathrm{V}$: Die
Aussteuergrenze ist $|U_e|_\mathrm{max} = 12\,\mathrm{V}/5.667 \approx 2.118\,\mathrm{V}$.
Für $U_e = 3\,\mathrm{V}$ ergäbe die Formel $-17\,\mathrm{V}$; tatsächlich stellt sich
$U_a = -12\,\mathrm{V}$ ein.
:::

::: warning
**Häufiger Fehler**

Einen rechnerischen Wert wie $-17\,\mathrm{V}$ als Ergebnis hinschreiben. Vergleiche jedes
$U_a$ mit $U_\mathrm{sat}$, bevor du es angibst; genau danach fragt
Aufgabe 2 der Altklausur.
:::

Übungen: [Invertierender Verstärker mit Sättigung und Innenwiderstand](ex:ex-vg-invertierer-saettigung),
[Übertragungskennlinie mit Sättigung skizzieren](ex:ex-vg-kennlinie-saettigung)

## Quelle mit Innenwiderstand

Eine reale Quelle mit Leerlaufspannung $U_0$ und Innenwiderstand $R_i$ liegt mit $R_i$ in
Reihe zu $R_1$, denn der Strom fließt durch beide bis zur virtuellen Masse,
siehe Skript S. 1. In der Knotenregel ersetzt
$R_1 + R_i$ den Widerstand $R_1$:

$$
\frac{U_a}{U_0} = -\frac{R_2}{R_1 + R_i}
$$

Der Fehler ist klein, wenn $R_1 \gg R_i$ ist: der Preis von $R_\mathrm{ein} = R_1$.

::: example
**Beispiel: Innenwiderstand**

Die Schaltung oben ($R_1 = 12\,\mathrm{k\Omega}$, $R_2 = 68\,\mathrm{k\Omega}$) an einer
Quelle mit $R_i = 2\,\mathrm{k\Omega}$:

$$
\frac{U_a}{U_0} = -\frac{68\,\mathrm{k\Omega}}{14\,\mathrm{k\Omega}} \approx -4.857
$$

Das sind nur noch etwa $85.7\,\%$ der Verstärkung von $-5.667$.
:::

::: warning
**Häufiger Fehler**

$R_i$ weglassen oder zu $R_2$ addieren: Es liegt im Eingangszweig, also neben $R_1$.
:::

Übung: [Invertierender Verstärker an einer Quelle mit Innenwiderstand](ex:ex-vg-innenwiderstand-herleitung)

## Nichtinvertierender Verstärker

![Nichtinvertierender Verstärker: Eingang am nichtinvertierenden Eingang, Spannungsteiler aus R2 und R1 im Rückkopplungszweig](fig:verstaerker-grundschaltungen-nichtinvertierer)

Hier liegt die Eingangsspannung direkt am nichtinvertierenden Eingang, und der
Spannungsteiler aus $R_2$ und $R_1$ führt einen Teil von $U_a$ auf den invertierenden
Eingang zurück, siehe Folie 8. Wegen
$U_d = 0$ ist $U_n = U_p = U_e$, und wegen $I_n = 0$ ist der Teiler unbelastet:

$$
U_e = \frac{R_1}{R_1 + R_2} \cdot U_a \quad\Rightarrow\quad V = \frac{U_a}{U_e} = 1 + \frac{R_2}{R_1}
$$

Die Verstärkung ist positiv (gleichphasig) und mindestens 1. Zum Dimensionieren löst man
nach $R_2$ auf, siehe Lösung Übungsblatt 3:

$$
R_2 = (V - 1) \cdot R_1
$$

::: definition
**Eingangswiderstand des nichtinvertierenden Verstärkers**

Die Quelle ist nur mit dem nichtinvertierenden Eingang verbunden, in den kein Strom
fließt ($I_p = 0$). Deshalb ist $R_\mathrm{ein} \to \infty$: Die Quelle wird nicht belastet.
:::

::: example
**Beispiel: nichtinvertierender Verstärker**

Mit $R_1 = 2.2\,\mathrm{k\Omega}$ und $R_2 = 10\,\mathrm{k\Omega}$ ist
$V = 1 + 10/2.2 \approx 5.545$. Für $U_e = 0.5\,\mathrm{V}$ folgt
$U_a \approx 2.773\,\mathrm{V}$. Durch $R_1$ fließt
$U_n/R_1 = 0.5\,\mathrm{V}/2.2\,\mathrm{k\Omega} \approx 227.3\,\mathrm{\mu A}$; derselbe Strom
kommt über $R_2$ vom Ausgang.
:::

::: warning
**Häufige Fehler**

Die Eins vergessen ($V = R_2/R_1$) oder das Minuszeichen des invertierenden Verstärkers
übernehmen. Beim Dimensionieren nicht $R_2 = V \cdot R_1$ rechnen: Für $V = 5$ ist
$R_2 = 4 \cdot R_1$.
:::

Übung: [Nichtinvertierenden Verstärker dimensionieren](ex:ex-vg-nichtinvertierer-dimensionieren)

## Spannungsfolger als Impedanzwandler

Setzt man im nichtinvertierenden Verstärker $R_2 = 0$ und lässt $R_1$ weg
($R_1 \to \infty$), wird der Ausgang direkt auf den invertierenden Eingang geführt,
siehe Folie 9:

$$
V = 1, \qquad R_\mathrm{ein} \to \infty, \qquad R_\mathrm{aus} \to 0
$$

Er verstärkt nicht, aber er entkoppelt: Den Laststrom liefert der OPV, nicht die Quelle.

![Spannungsfolger zwischen einer Quelle mit Innenwiderstand Ri und dem Lastwiderstand RL](fig:verstaerker-grundschaltungen-folger-last)

Ohne Folger bilden $R_i$ und $R_L$ einen Spannungsteiler, mit Folger fällt an $R_i$ keine
Spannung ab:

$$
U_L = U_0 \cdot \frac{R_L}{R_i + R_L} \quad \text{(direkt)}, \qquad U_L = U_0 \quad \text{(mit Folger)}
$$

::: example
**Beispiel: hochohmige Quelle an niederohmiger Last**

Eine Quelle mit $U_0 = 1.2\,\mathrm{V}$ und $R_i = 22\,\mathrm{k\Omega}$ speist
$R_L = 2.2\,\mathrm{k\Omega}$. Direkt angeschlossen bleiben
$U_L = 1.2\,\mathrm{V} \cdot 2.2/24.2 \approx 0.1091\,\mathrm{V}$, also nur etwa
$9.1\,\%$ von $U_0$. Mit Spannungsfolger liegt die volle Spannung
$U_L = 1.2\,\mathrm{V}$ an der Last.
:::

::: warning
**Häufiger Fehler**

„Der Spannungsfolger ist nutzlos, weil $V = 1$ ist.“ Sein Nutzen ist der unendliche
Eingangswiderstand und der verschwindende Ausgangswiderstand, nicht die Verstärkung.
:::

Übungen: [Hochohmiger Sensor mit und ohne Spannungsfolger](ex:ex-vg-impedanzwandler-sensor),
[Nichtinvertierender Verstärker und Impedanzwandler für einen Sensor](ex:ex-vg-nichtinvertierer-impedanzwandler)

## Summierer

![Summierer mit drei Eingängen: U1, U2 und U3 über R1, R2 und R3 an der virtuellen Masse, Rückkopplung über RF](fig:verstaerker-grundschaltungen-summierer)

Beim Summierer (Addierer) führen mehrere Eingangswiderstände auf dieselbe virtuelle Masse,
siehe Folie 10. Jeder Eingang treibt
den Strom $U_i/R_i$ in den Knoten, weil der Knoten auf $0\,\mathrm{V}$ liegt; die Eingänge
beeinflussen sich deshalb nicht. Die Summe der Ströme fließt durch $R_F$:

$$
U_a = -R_F \cdot \left( \frac{U_1}{R_1} + \frac{U_2}{R_2} + \ldots + \frac{U_k}{R_k} \right)
$$

Jeder Eingang hat sein eigenes Gewicht $-R_F/R_i$. Mit $R_1 = R_2 = \ldots = R_F$ gilt
$U_a = -(U_1 + U_2 + \ldots + U_k)$,
siehe Skript S. 2. Der Eingangswiderstand
jedes Eingangs ist sein $R_i$.

::: example
**Beispiel: drei Eingänge**

$R_F = 30\,\mathrm{k\Omega}$, $R_1 = 10\,\mathrm{k\Omega}$, $R_2 = 15\,\mathrm{k\Omega}$,
$R_3 = 60\,\mathrm{k\Omega}$; $U_1 = 0.4\,\mathrm{V}$, $U_2 = -0.3\,\mathrm{V}$,
$U_3 = 1\,\mathrm{V}$. Die Ströme sind $40\,\mathrm{\mu A}$, $-20\,\mathrm{\mu A}$ und
$16.67\,\mathrm{\mu A}$, zusammen $36.67\,\mathrm{\mu A}$:

$$
U_a = -30\,\mathrm{k\Omega} \cdot 36.67\,\mathrm{\mu A} \approx -1.1\,\mathrm{V}
$$

Die Gewichte sind $-3$, $-2$ und $-0.5$.
:::

::: warning
**Häufige Fehler**

Die Spannungen einfach addieren ($U_1 + U_2 + U_3$), obwohl die Widerstände verschieden
sind, das Minuszeichen vergessen, oder das Vorzeichen eines negativen Eingangs verlieren.
Rechne über die Ströme: Jeder Strom trägt das Vorzeichen seiner Spannung.
:::

Übungen: [Summierer mit drei Eingängen](ex:ex-vg-summierer-drei-eingaenge),
[Gewichteten Summierer dimensionieren](ex:ex-vg-summierer-dimensionieren)

## Die Grundschaltungen im Vergleich

Übertragung und Eingangswiderstand, siehe Folie 13:

| Schaltung | Übertragung | Eingangswiderstand |
|---|---|---|
| Invertierender Verstärker | $U_a = -\frac{R_2}{R_1} \cdot U_e$ | $R_1$ |
| Nichtinvertierender Verstärker | $U_a = \left(1 + \frac{R_2}{R_1}\right) \cdot U_e$ | $\to \infty$ |
| Spannungsfolger | $U_a = U_e$ | $\to \infty$ |
| Summierer | $U_a = -R_F \sum_i \frac{U_i}{R_i}$ | $R_i$ je Eingang |

::: note
**Welche Schaltung wofür?**

Für ein Signal aus einer hochohmigen Quelle nimmt man den nichtinvertierenden Verstärker
oder den Spannungsfolger. Der invertierende Verstärker ist die richtige Wahl, wenn das
Vorzeichen umgekehrt, abgeschwächt ($|V| < 1$) oder wie beim Summierer gemischt werden
soll. Den [Integrierer](topic:integrierer) erhältst du, wenn du $R_2$ durch einen
Kondensator ersetzt.
:::

::: takeaways
- Knotenregel am invertierenden Eingang aufstellen, dann auflösen, dann Zahlen einsetzen.
- Invertierender Verstärker: $V = -R_2/R_1$, $R_\mathrm{ein} = R_1$; mit Quelle $R_i$ wird daraus $-R_2/(R_1 + R_i)$.
- Nichtinvertierender Verstärker: $V = 1 + R_2/R_1$, $R_\mathrm{ein} \to \infty$; dimensionieren mit $R_2 = (V - 1) \cdot R_1$.
- Spannungsfolger: $V = 1$, entkoppelt hochohmige Quellen von niederohmigen Lasten.
- Summierer: $U_a = -R_F \sum U_i/R_i$, jeder Eingang mit eigenem Gewicht.
- Jedes Ergebnis mit $\pm U_\mathrm{sat}$ vergleichen: Jenseits von $U_\mathrm{sat}/|V|$ bleibt der Ausgang an der Grenze.
:::
