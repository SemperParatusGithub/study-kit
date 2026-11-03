---
topic: integrierer
title: Integrierer
objectives:
  - 'Die Ausgangsspannung $U_a(t)$ des Integrierers aus der Knotenregel an der virtuellen Masse herleiten'
  - 'Steigung und Vorzeichen der Rampe bei konstanter Eingangsspannung berechnen'
  - 'Die Zeit bis zur Sättigung mit und ohne Anfangswert $U_a(0)$ bestimmen'
  - 'Den Verlauf von $U_a(t)$ bei stückweise konstanter Eingangsspannung skizzieren'
  - 'Den Frequenzgang $\underline{H}(j\omega) = -1/(j\omega RC)$ deuten und $f_1$ sowie $|\underline{H}|$ bei einer Frequenz berechnen'
sources:
  - {doc: vl03-operationsverstaerker-grundschaltungen, pages: '11-12'}
  - {doc: skript-kapitel4-operationsverstaerker, pages: 2}
  - {doc: uebung03-opv-grundschaltungen, pages: 1}
  - {doc: klausur-ws2025-26, pages: 2}
---

## Vom invertierenden Verstärker zum Integrierer

Der Integrierer ist ein [invertierender Verstärker](topic:verstaerker-grundschaltungen),
in dem der Rückkopplungswiderstand $R_2$ durch einen Kondensator $C$ ersetzt ist. Der
nichtinvertierende Eingang liegt auf Masse, der invertierende Eingang ist deshalb eine
virtuelle Masse ($U_n = 0$), und in den OPV fließt kein Strom (die zwei Regeln aus
[Idealer Operationsverstärker und Gegenkopplung](topic:idealer-opv)).

![Invertierender Integrierer: R vom Eingang an den invertierenden Eingang, C vom Ausgang zurück](fig:integrierer-schaltung)

Durch $R$ fließt der Strom $I = U_e/R$. Weil er nicht in den OPV hineinfließen kann,
fließt er vollständig in den Kondensator. Dessen Spannung ist $U_n - U_a = -U_a$, also
gilt mit $I_C = C \cdot \mathrm{d}U_C/\mathrm{d}t$:

$$
C \cdot \frac{\mathrm{d}U_a}{\mathrm{d}t} = -\frac{U_e}{R} \quad\Rightarrow\quad U_a(t) = -\frac{1}{RC} \int_0^t U_e(\tau)\,\mathrm{d}\tau + U_a(0)
$$

Die Herleitung steht auf Folie 11
der Vorlesung und auf Seite 2 des
Skripts.

::: definition
**Integrierer und Zeitkonstante**

Ein Integrierer liefert eine Ausgangsspannung, die proportional zum zeitlichen Integral
der Eingangsspannung ist, mit dem Faktor $-1/(RC)$. Das Produkt $RC$ heißt
Integrationszeitkonstante; es hat die Einheit Sekunde
($1\,\mathrm{k\Omega} \cdot 1\,\mathrm{\mu F} = 1\,\mathrm{ms}$). $U_a(0)$ ist die
Ausgangsspannung zu Beginn, also die Anfangsladung des Kondensators.
:::

::: warning
**Häufiger Fehler: Vorzeichen vergessen**

Der Integrierer ist eine invertierende Schaltung. Das Minuszeichen vor dem Integral kommt
aus der virtuellen Masse und gehört immer dazu: Eine positive Eingangsspannung lässt
$U_a$ fallen, eine negative lässt $U_a$ steigen.
:::

Übung: [Ausgangsspannung des Integrierers herleiten](ex:ex-int-herleitung)

## Konstante Eingangsspannung: die Rampe

Ist $U_e$ ab $t = 0$ konstant, wird das Integral zu $U_e \cdot t$. Der Ausgang ist eine
Gerade, eine Rampe, mit der Steigung $-U_e/(RC)$:

$$
U_a(t) = -\frac{U_e}{RC} \cdot t + U_a(0), \qquad \frac{\mathrm{d}U_a}{\mathrm{d}t} = -\frac{U_e}{RC}
$$

Physikalisch lädt der konstante Strom $U_e/R$ den Kondensator gleichmäßig auf; ein
konstanter Strom ergibt an einem Kondensator immer eine linear wachsende Spannung.

![Sprungantwort des Integrierers mit R = 22 kΩ und C = 100 nF für Ue = 0.5 V: fallende Rampe bis zur Sättigung bei −12 V](fig:integrierer-rampe)

::: example
**Beispiel: Steigung der Rampe**

Mit $R = 22\,\mathrm{k\Omega}$, $C = 100\,\mathrm{nF}$ und $U_e = 0.5\,\mathrm{V}$ ab
$t = 0$, $U_a(0) = 0$:

$$
RC = 22\,\mathrm{k\Omega} \cdot 100\,\mathrm{nF} = 2.2\,\mathrm{ms}, \qquad \frac{\mathrm{d}U_a}{\mathrm{d}t} = -\frac{0.5\,\mathrm{V}}{2.2\,\mathrm{ms}} \approx -227.3\,\frac{\mathrm{V}}{\mathrm{s}}
$$

Nach $10\,\mathrm{ms}$ ist $U_a \approx -2.27\,\mathrm{V}$. Dasselbe mit
$RC = 1\,\mathrm{ms}$ rechnet
Folie 12 vor.
:::

::: warning
**Häufiger Fehler: Zehnerpotenzen in $RC$**

$\mathrm{k\Omega} \cdot \mathrm{nF}$ ergibt $\mathrm{\mu s}$,
$\mathrm{k\Omega} \cdot \mathrm{\mu F}$ ergibt $\mathrm{ms}$. Wer $100\,\mathrm{nF}$ als $10^{-6}\,\mathrm{F}$
einsetzt, bekommt eine zehnmal zu flache Rampe.
:::

Übung: [Rampe am Integrierer](ex:ex-int-rampe)

## Sättigung

Die Rampe kann nicht beliebig weiterlaufen. Sobald $|U_a|$ die Sättigungsspannung
$U_\mathrm{sat}$ erreicht, bleibt der Ausgang dort stehen. Ab diesem Moment ist der OPV
nicht mehr im linearen Betrieb, $U_d \ne 0$, und die Integriererformel gilt nicht mehr.

::: theorem
**Zeit bis zur Sättigung**

Bei konstanter Eingangsspannung $U_e \ne 0$ erreicht der Ausgang die Sättigung, wenn die
Rampe den Abstand vom Anfangswert $U_a(0)$ bis zur Grenze $\mp U_\mathrm{sat}$
zurückgelegt hat (für $U_e > 0$ ist es $-U_\mathrm{sat}$, für $U_e < 0$ ist es
$+U_\mathrm{sat}$):

$$
t_\mathrm{sat} = \frac{U_\mathrm{sat} \pm U_a(0)}{|U_e|} \cdot RC
$$

Das Pluszeichen gilt, wenn der Anfangswert dasselbe Vorzeichen wie $U_e$ hat (die Rampe
muss erst durch null), das Minuszeichen, wenn er schon in Richtung der Grenze liegt. Mit
$U_a(0) = 0$ bleibt $t_\mathrm{sat} = U_\mathrm{sat} \cdot RC/|U_e|$. Die Formel gilt
nur, solange $|U_a(0)| < U_\mathrm{sat}$ ist.
:::

::: example
**Beispiel: Sättigungszeit**

Mit den Werten von oben und $U_\mathrm{sat} = 12\,\mathrm{V}$, $U_a(0) = 0$:

$$
t_\mathrm{sat} = \frac{12\,\mathrm{V}}{0.5\,\mathrm{V}} \cdot 2.2\,\mathrm{ms} = 52.8\,\mathrm{ms}
$$

Ist der Kondensator zu Beginn auf $U_a(0) = 3\,\mathrm{V}$ geladen, muss die fallende
Rampe von $+3\,\mathrm{V}$ bis $-12\,\mathrm{V}$ laufen, also $15\,\mathrm{V}$:
$t_\mathrm{sat} = 15\,\mathrm{V}/(227.3\,\mathrm{V/s}) \approx 66\,\mathrm{ms}$.
:::

::: warning
**Häufiger Fehler: $U_B$ statt $U_\mathrm{sat}$**

Die Rampe endet an der Sättigungsspannung $U_\mathrm{sat}$, nicht an der
Versorgungsspannung $U_B$. Ist nur $U_B$ gegeben, sagt die Aufgabe, ob der Ausgang bis
$U_B$ reicht. Ein zweiter Fehler ist, den Hub von $-U_\mathrm{sat}$ bis
$+U_\mathrm{sat}$ anzusetzen, obwohl die Rampe bei $U_a(0) = 0$ beginnt.
:::

::: note
**Offset-Drift in der Praxis**

Schon eine kleine Offsetspannung am Eingang wird integriert und treibt den Ausgang mit
der Zeit in die Sättigung. Deshalb legt man einen großen Widerstand parallel zu $C$; er
begrenzt die Gleichspannungsverstärkung. So steht es auf
Seite 2 des Skripts.
:::

Übung: [Integrierer mit Sprungeingang bis zur Sättigung](ex:ex-int-sprung-saettigung)

## Stückweise konstante Eingangsspannung

Ändert sich $U_e$ sprunghaft, rechnet man Abschnitt für Abschnitt. In jedem Abschnitt
ist der Ausgang eine Gerade mit der Steigung $-U_e/(RC)$ des Abschnitts. Der Endwert eines
Abschnitts ist der Anfangswert des nächsten, denn die Kondensatorspannung kann nicht
springen:

$$
U_a(t) = U_a(t_k) - \frac{U_{e,k}}{RC} \cdot (t - t_k) \quad \text{für } t_k \le t < t_{k+1}
$$

Eine Rechteckspannung am Eingang ergibt so eine Dreieckspannung am Ausgang; ein
Abschnitt mit $U_e = 0$ hält den Ausgang konstant.

::: example
**Beispiel: zwei Abschnitte**

$RC = 2.2\,\mathrm{ms}$, $U_a(0) = 0$, $U_e = 0.5\,\mathrm{V}$ für
$0 \le t < 1\,\mathrm{ms}$, danach $U_e = -0.5\,\mathrm{V}$. Im ersten Abschnitt fällt
der Ausgang um $0.5\,\mathrm{V} \cdot 1\,\mathrm{ms}/2.2\,\mathrm{ms} \approx 0.227\,\mathrm{V}$
auf $U_a(1\,\mathrm{ms}) \approx -0.227\,\mathrm{V}$. Danach steigt er mit derselben
Steigung wieder und erreicht bei $t = 2\,\mathrm{ms}$ wieder null.
:::

::: warning
**Häufiger Fehler: Anfangswert vergessen**

Im zweiten Abschnitt startet die Rampe nicht bei null, sondern beim Endwert des ersten
Abschnitts. Wer $U_a(t_k)$ weglässt, verschiebt den ganzen weiteren Verlauf.
:::

Übung: [Integrierer mit zwei Eingangsabschnitten](ex:ex-int-zwei-abschnitte)

## Frequenzgang

Für sinusförmige Spannungen wird aus dem Kondensator die Impedanz $1/(j\omega C)$. Der
Integrierer ist dann ein invertierender Verstärker mit $R_1 = R$ und
$R_2 = 1/(j\omega C)$:

$$
\underline{H}(j\omega) = \frac{\underline{U}_a}{\underline{U}_e} = -\frac{1}{j\omega RC} = \frac{j}{\omega RC}, \qquad |\underline{H}| = \frac{1}{\omega RC} = \frac{1}{2\pi f RC}
$$

Der Betrag ist umgekehrt proportional zur Frequenz: Er fällt mit $20\,\mathrm{dB}$ pro
Dekade. Die Phase ist bei allen Frequenzen $+90^\circ$, denn $-1/j = +j$: Der Ausgang
eilt dem Eingang um $90^\circ$ vor (Inversion $180^\circ$ und Integration $-90^\circ$).

::: definition
**Frequenz $f_1$**

Bei $f_1$ ist der Betrag des Frequenzgangs genau 1 ($0\,\mathrm{dB}$):

$$
|\underline{H}(j 2\pi f_1)| = 1 \quad\Rightarrow\quad f_1 = \frac{1}{2\pi RC}
$$

Unterhalb von $f_1$ verstärkt der Integrierer, oberhalb schwächt er ab; siehe
Folie 12.
:::

![Bode-Diagramm des Integrierers mit RC = 2.2 ms: Betrag fällt mit 20 dB pro Dekade durch 0 dB bei f1, Phase konstant +90°](fig:integrierer-bode)

::: example
**Beispiel: $f_1$ und Betrag bei 1 kHz**

Mit $RC = 2.2\,\mathrm{ms}$:

$$
f_1 = \frac{1}{2\pi \cdot 2.2\,\mathrm{ms}} \approx 72.34\,\mathrm{Hz}, \qquad |\underline{H}(1\,\mathrm{kHz})| = \frac{f_1}{1\,\mathrm{kHz}} \approx 0.0723
$$

Das sind $20 \lg 0.0723 \approx -22.8\,\mathrm{dB}$.
:::

::: warning
**Häufiger Fehler: $f_1$ ist keine Grenzfrequenz**

Beim Integrierer gibt es keinen Knick und keine $-3\,\mathrm{dB}$-Stelle wie beim
RC-Tiefpass: $f_1$ ist die Frequenz mit dem Betrag 1. Außerdem gilt $f_1 = 1/(2\pi RC)$;
$1/(RC)$ ist die Kreisfrequenz $\omega_1$ in $\mathrm{s^{-1}}$, nicht $f_1$ in
$\mathrm{Hz}$.
:::

Übungen: [Zeitkonstante und Frequenz f1 eines Integrierers](ex:ex-int-grenzfrequenz),
[Betrag und Phase des Integrierers](ex:ex-int-betrag-phase)

## Sinusförmige Eingangsspannung

Bei $U_e(t) = \hat{U}_e \sin(\omega t)$ liefert das Integral einen Kosinus. Die Amplitude
am Ausgang ist der Betrag des Frequenzgangs mal die Eingangsamplitude:

$$
\hat{U}_a = |\underline{H}| \cdot \hat{U}_e = \frac{\hat{U}_e}{\omega RC}
$$

Bei tiefen Frequenzen wird $\hat{U}_a$ groß. Der Ausgang bleibt nur unverzerrt, solange
$\hat{U}_a < U_\mathrm{sat}$ ist, also oberhalb von
$f_\mathrm{min} = \hat{U}_e/(2\pi RC \cdot U_\mathrm{sat})$.

::: example
**Beispiel: Amplitude bei 50 Hz**

Mit $RC = 2.2\,\mathrm{ms}$ und $\hat{U}_e = 0.2\,\mathrm{V}$ bei $f = 50\,\mathrm{Hz}$:

$$
\hat{U}_a = \frac{0.2\,\mathrm{V}}{2\pi \cdot 50\,\mathrm{Hz} \cdot 2.2\,\mathrm{ms}} \approx 0.289\,\mathrm{V}
$$
:::

Übung: [Sinusspannung am Integrierer](ex:ex-int-sinus)

::: takeaways
- Integrierer = invertierender Verstärker mit $C$ statt $R_2$:
  $U_a(t) = -\frac{1}{RC}\int_0^t U_e\,\mathrm{d}\tau + U_a(0)$.
- Konstante Eingangsspannung ergibt eine Rampe mit der Steigung $-U_e/(RC)$; das
  Vorzeichen ist dem von $U_e$ entgegengesetzt.
- Die Rampe endet bei $\pm U_\mathrm{sat}$ nach
  $t_\mathrm{sat} = (U_\mathrm{sat} \pm U_a(0)) \cdot RC/|U_e|$; danach gilt die Formel
  nicht mehr.
- Bei stückweise konstantem Eingang ist der Endwert eines Abschnitts der Anfangswert des
  nächsten.
- $\underline{H}(j\omega) = -1/(j\omega RC)$: Betrag $1/(\omega RC)$ fällt mit
  $20\,\mathrm{dB}$ pro Dekade, Phase $+90^\circ$, Betrag 1 bei $f_1 = 1/(2\pi RC)$.
:::
