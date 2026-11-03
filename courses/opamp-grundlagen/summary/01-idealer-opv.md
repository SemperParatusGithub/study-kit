---
topic: idealer-opv
title: Idealer Operationsverstärker und Gegenkopplung
objectives:
  - 'Die Idealisierungen des OPV nennen und mit realen Werten vergleichen'
  - 'Aus $U_a = V_0 \cdot U_d$ den linearen Bereich und die Sättigung eines OPV ohne Rückkopplung bestimmen'
  - 'Die Verstärkung $V = V_0/(1 + k V_0)$ einer Gegenkopplung herleiten und den Fehler gegenüber $1/k$ berechnen'
  - 'Die zwei Regeln des idealen OPV mit Gegenkopplung begründen und anwenden'
  - 'Virtuelle Masse erklären und erkennen, wann sie wegen Sättigung nicht mehr gilt'
sources:
  - {doc: vl03-operationsverstaerker-grundschaltungen, pages: '3-4'}
  - {doc: skript-kapitel4-operationsverstaerker, pages: '1'}
  - {doc: altes-uebungsblatt02-scan, pages: '1'}
---

## Der OPV als Differenzverstärker

Ein Operationsverstärker hat zwei Eingänge, den nichtinvertierenden ($+$, Spannung $U_p$)
und den invertierenden ($-$, Spannung $U_n$), und einen Ausgang. Er verstärkt die
Differenzspannung zwischen den Eingängen mit der Leerlaufverstärkung $V_0$, wie
Folie 3 zeigt:

$$
U_a = V_0 \cdot (U_p - U_n) = V_0 \cdot U_d
$$

::: definition
**Leerlaufverstärkung und Sättigung**

Die Leerlaufverstärkung $V_0$ ist die Verstärkung des OPV ohne äußere Beschaltung. Real
ist $V_0 \approx 10^5$ bis $10^6$. Der Ausgang kann die Versorgungsspannung nicht
überschreiten: Er ist auf $-U_\mathrm{sat} \le U_a \le U_\mathrm{sat}$ begrenzt, wobei
$U_\mathrm{sat}$ etwas unter der Versorgungsspannung $U_B$ liegt.
:::

Weil $V_0$ so groß ist, ist der lineare Bereich winzig. Der Ausgang erreicht die Sättigung
schon bei

$$
|U_d|_\mathrm{max} = \frac{U_\mathrm{sat}}{V_0}
$$

![Übertragungskennlinie eines OPV ohne Rückkopplung: linear nur zwischen -120 µV und 120 µV, außerhalb Sättigung bei ±12 V](fig:idealer-opv-kennlinie)

::: example
**Beispiel: linearer Bereich ohne Rückkopplung**

Mit $V_0 = 10^5$ und $U_\mathrm{sat} = 12\,\mathrm{V}$ ist

$$
|U_d|_\mathrm{max} = \frac{12\,\mathrm{V}}{10^5} = 120\,\mathrm{\mu V}
$$

Schon eine Differenzspannung von $0.2\,\mathrm{mV}$ treibt den Ausgang also in die
Sättigung. Ohne Rückkopplung taugt der OPV deshalb nur als Komparator, nicht als
Verstärker.
:::

Übung: [OPV ohne Rückkopplung](ex:ex-iopv-offener-betrieb)

## Der ideale OPV

Für die Berechnung von Schaltungen ersetzt man den realen OPV durch ein Modell mit
idealisierten Eigenschaften; sie stehen auf Folie 3 und im
Skript S. 1.

::: definition
**Idealer Operationsverstärker**

- Leerlaufverstärkung $V_0 \to \infty$
- Eingangswiderstand $R_e \to \infty$, also fließen keine Eingangsströme: $I_p = I_n = 0$
- Ausgangswiderstand $R_a \to 0$: Die Ausgangsspannung hängt nicht von der Last ab
- unbegrenzte Bandbreite und keine Offsetspannung
:::

| Eigenschaft | ideal | real (typisch) |
|---|---|---|
| Leerlaufverstärkung $V_0$ | $\infty$ | $10^5$ bis $10^6$ |
| Eingangsströme $I_p$, $I_n$ | $0$ | sehr klein |
| Ausgangswiderstand $R_a$ | $0$ | klein |
| Ausgangsspannung $U_a$ | unbegrenzt im Modell | $\pm U_\mathrm{sat}$, etwas unter $\pm U_B$ |

::: note
**Grenzen des Modells**

Die Sättigung bleibt auch beim idealen OPV bestehen: Jede Rechnung mit dem Modell muss
am Ende prüfen, ob $|U_a| < U_\mathrm{sat}$ gilt. Die große Leerlaufverstärkung gilt real
außerdem nur bei tiefen Frequenzen; bei hohen Frequenzen sinkt $V_0$ deutlich.
:::

## Gegenkopplung

Bei der Gegenkopplung wird ein Teil der Ausgangsspannung auf den invertierenden Eingang
zurückgeführt, siehe Folie 4. Steigt
$U_a$, steigt auch $U_n$; damit sinkt $U_d$ und wirkt dem Anstieg entgegen. Der Ausgang
stellt sich so ein, dass das Gleichgewicht erreicht ist.

::: definition
**Gegenkopplung und Rückkopplungsfaktor**

Gegenkopplung ist die Rückführung vom Ausgang auf den invertierenden Eingang. Der
Rückkopplungsfaktor $k$ gibt an, welcher Anteil von $U_a$ zurückgeführt wird. Beim
Spannungsteiler aus $R_2$ (vom Ausgang) und $R_1$ (nach Masse) ist

$$
k = \frac{R_1}{R_1 + R_2}
$$
:::

![Wirkungsplan der Gegenkopplung: Vorwärtszweig V0, Rückführung k·Ua auf die Summierstelle](fig:idealer-opv-gegenkopplung)

Am nichtinvertierenden Verstärker ist $U_p = U_e$ und $U_n = k U_a$. Eingesetzt in die
Gleichung des OPV:

$$
U_a = V_0 (U_e - k U_a) \quad\Rightarrow\quad U_a (1 + k V_0) = V_0 U_e
$$

::: theorem
**Verstärkung mit endlicher Leerlaufverstärkung**

Für eine Gegenkopplung mit dem Rückkopplungsfaktor $k$ gilt nach dem
Skript S. 1

$$
V = \frac{U_a}{U_e} = \frac{V_0}{1 + k V_0} \quad\to\quad \frac{1}{k} \quad \text{für } k V_0 \gg 1
$$

Das Produkt $k V_0$ heißt Schleifenverstärkung. Der relative Fehler gegenüber dem idealen
Wert $1/k$ ist

$$
F = \frac{1/k - V}{1/k} = \frac{1}{1 + k V_0}
$$
:::

Die Verstärkung hängt also fast nur noch von $k$ ab, das heißt von zwei Widerständen, und
kaum noch vom Exemplar des OPV. Halbiert sich $V_0$ etwa durch Erwärmung, ändert sich $V$
nur um rund $1/(1 + k V_0)$ dieses Anteils.

::: example
**Beispiel: nichtinvertierender Verstärker mit realem OPV**

Mit $R_1 = 10\,\mathrm{k\Omega}$, $R_2 = 39\,\mathrm{k\Omega}$ und $V_0 = 10^5$ ist
$k = 10/49 \approx 0.2041$ und $1/k = 4.9$. Mit $k V_0 \approx 20408$ folgt

$$
V = \frac{10^5}{1 + 20408} \approx 4.8998, \qquad F = \frac{1}{1 + k V_0} \approx 4.9 \cdot 10^{-5} = 0.0049\,\%
$$

Bei $U_e = 0.1\,\mathrm{V}$ ist $U_a \approx 0.49\,\mathrm{V}$ und
$U_d = U_a/V_0 \approx 4.9\,\mathrm{\mu V}$: praktisch null.
:::

::: warning
**Häufiger Fehler: Mitkopplung statt Gegenkopplung**

Nur die Rückführung auf den **invertierenden** Eingang ist eine Gegenkopplung. Wird der
Ausgang auf den nichtinvertierenden Eingang zurückgeführt (Mitkopplung), verstärkt sich
jede Abweichung selbst, und der Ausgang läuft in die Sättigung.
:::

::: warning
**Häufiger Fehler: Rückkopplungsfaktor vertauscht**

$k$ ist der Anteil von $U_a$ am invertierenden Eingang, also $R_1/(R_1 + R_2)$ mit $R_1$
nach Masse, nicht $R_2/(R_1 + R_2)$. Die Probe: $1/k$ muss $1 + R_2/R_1$ ergeben.
:::

Übungen: [Endliche Leerlaufverstärkung](ex:ex-iopv-endliche-leerlaufverstaerkung),
[Mindest-Leerlaufverstärkung](ex:ex-iopv-mindest-leerlaufverstaerkung)

## Die zwei Regeln: virtueller Kurzschluss

Bei endlicher Ausgangsspannung und $V_0 \to \infty$ muss die Differenzspannung
verschwinden, so begründet es das Skript S. 1:

$$
U_d = \frac{U_a}{V_0} \to 0
$$

Daraus folgen die beiden Regeln, mit denen jede gegengekoppelte OPV-Schaltung berechnet
wird; Folie 4 nennt sie die goldenen Regeln.

::: theorem
**Die zwei Regeln des idealen OPV**

Bei Gegenkopplung im linearen Betrieb ($|U_a| < U_\mathrm{sat}$) gilt:

1. In die Eingänge fließt kein Strom: $I_p = I_n = 0$.
2. Die Differenzspannung ist null: $U_d = U_p - U_n = 0$, also $U_p = U_n$
   (virtueller Kurzschluss).

$$
I_p = I_n = 0, \qquad U_p = U_n
$$
:::

::: warning
**Häufiger Fehler: virtueller Kurzschluss als echte Verbindung**

„Virtuell" heißt: Die Eingänge liegen auf gleichem Potential, sind aber nicht verbunden.
Zwischen ihnen fließt kein Strom, und $U_d = 0$ stellt erst die Gegenkopplung über den
Ausgang her.
:::

::: warning
**Häufiger Fehler: Regeln ohne Gegenkopplung**

Ohne Gegenkopplung gilt $U_d = 0$ nicht. Ein offen betriebener OPV verstärkt jede
Differenzspannung mit $V_0$ und geht fast immer in die Sättigung.
:::

## Virtuelle Masse

Liegt der nichtinvertierende Eingang auf Masse ($U_p = 0$), folgt aus der zweiten Regel
$U_n = 0$, obwohl der invertierende Eingang nicht mit Masse verbunden ist. Dieser Punkt
heißt virtuelle Masse, siehe Folie 4.

![Invertierender Verstärker: Ue über R1 an den invertierenden Eingang, R2 vom Ausgang zurück, nichtinvertierender Eingang auf Masse](fig:idealer-opv-invertierer-symbolisch)

::: definition
**Virtuelle Masse**

Ein Eingang, der ohne Verbindung zur Masse auf $0\,\mathrm{V}$ liegt, weil der andere
Eingang auf Masse liegt und die Gegenkopplung $U_p = U_n$ erzwingt.
:::

Am invertierenden Verstärker liefern die beiden Regeln die Knotengleichung an der
virtuellen Masse: Der Strom $U_e/R_1$ kann nicht in den Eingang fließen und muss über
$R_2$ zum Ausgang weiter. Daraus folgt $V = -R_2/R_1$; die Grundschaltungen rechnet das
Thema [Grundschaltungen](topic:verstaerker-grundschaltungen) durch.

$$
\frac{U_e - 0}{R_1} + \frac{U_a - 0}{R_2} = 0
$$

::: warning
**Häufiger Fehler: virtuelle Masse trotz Sättigung**

Ist der Ausgang in der Sättigung, wirkt die Gegenkopplung nicht mehr, und $U_n \ne 0$.
Dann fließt derselbe Strom durch $R_1$ und $R_2$ (der Eingang nimmt keinen auf), und
$U_n$ folgt aus dem Spannungsteiler zwischen $U_e$ und $U_a = \pm U_\mathrm{sat}$.
:::

::: example
**Beispiel: invertierender Verstärker in der Sättigung**

Mit $R_1 = 10\,\mathrm{k\Omega}$, $R_2 = 47\,\mathrm{k\Omega}$ und
$U_\mathrm{sat} = 12\,\mathrm{V}$ ergäbe $U_e = 3\,\mathrm{V}$ rechnerisch
$U_a = -4.7 \cdot 3\,\mathrm{V} = -14.1\,\mathrm{V}$. Das geht nicht: $U_a = -12\,\mathrm{V}$.
Der Strom durch beide Widerstände und die Spannung am invertierenden Eingang sind dann

$$
I = \frac{U_e - U_a}{R_1 + R_2} = \frac{15\,\mathrm{V}}{57\,\mathrm{k\Omega}} \approx 0.263\,\mathrm{mA}, \qquad U_n = U_e - I R_1 \approx 0.368\,\mathrm{V}
$$

Die virtuelle Masse ist verloren.
:::

Übung: [Virtuelle Masse und Sättigung](ex:ex-iopv-virtuelle-masse-saettigung),
[Invertierender Verstärker mit endlichem $V_0$](ex:ex-iopv-invertierer-endlich)

## Vorgehen bei einer OPV-Schaltung

1. Prüfen, ob eine Gegenkopplung vorliegt (Rückführung auf den invertierenden Eingang).
2. Die zwei Regeln ansetzen: $I_p = I_n = 0$ und $U_p = U_n$.
3. Die Knotenregel am invertierenden Eingang aufstellen und nach $U_a$ auflösen.
4. Zahlen einsetzen und prüfen, ob $|U_a| < U_\mathrm{sat}$ gilt. Sonst ist
   $U_a = \pm U_\mathrm{sat}$, und die Regeln gelten nicht mehr.

::: takeaways
- $U_a = V_0 \cdot U_d$; ohne Rückkopplung ist der lineare Bereich nur
  $|U_d| < U_\mathrm{sat}/V_0$ breit (mit $V_0 = 10^5$ und $12\,\mathrm{V}$ nur $120\,\mathrm{\mu V}$).
- Idealer OPV: $V_0 \to \infty$, $I_p = I_n = 0$, $R_a \to 0$.
- Gegenkopplung: $V = V_0/(1 + k V_0) \approx 1/k$, relativer Fehler $1/(1 + k V_0)$.
- Mit Gegenkopplung im linearen Betrieb gilt $U_p = U_n$ (virtueller Kurzschluss); liegt
  $U_p$ auf Masse, ist der invertierende Eingang eine virtuelle Masse.
- Beide Regeln gelten nur für $|U_a| < U_\mathrm{sat}$; in der Sättigung ist $U_d \ne 0$.
:::
