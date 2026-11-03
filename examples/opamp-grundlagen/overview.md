---
title: Überblick
---

## Worum geht es?

Ein Operationsverstärker (OPV) ist ein Differenzverstärker mit sehr großer
Leerlaufverstärkung $V_0 \approx 10^5$. Allein wäre er unbrauchbar, denn schon eine
Differenzspannung von rund $0.1\,\mathrm{mV}$ treibt den Ausgang bei $\pm 12\,\mathrm{V}$
Versorgung in die Sättigung. Erst die Gegenkopplung macht aus ihm einen Baustein,
dessen Verhalten nur noch von den äußeren Widerständen und Kondensatoren abhängt. Dieser
Kurs zeigt, wie man solche Schaltungen mit zwei einfachen Regeln berechnet.

Am Anfang steht das Thema
[Idealer Operationsverstärker und Gegenkopplung](topic:idealer-opv): die Idealisierungen,
der virtuelle Kurzschluss und die virtuelle Masse. Mit diesen Regeln berechnest du im
Schwerpunkt, dem Thema [Invertierender und nichtinvertierender Verstärker, Spannungsfolger
und Summierer](topic:verstaerker-grundschaltungen), alle Grundschaltungen. Der
[Integrierer](topic:integrierer) ersetzt schließlich den Rückkopplungswiderstand durch
einen Kondensator und führt in den Zeitbereich und zum Frequenzgang.

## Themenkarte

![Die drei Themen des Kurses und ihre Abhängigkeiten; die Grundschaltungen tragen das meiste Gewicht](fig:topic-map)

## Wie die Themen zusammenhängen

Der rote Faden sind die zwei Regeln des idealen OPV bei Gegenkopplung: In die Eingänge
fließt kein Strom ($I_p = I_n = 0$), und die Differenzspannung ist null ($U_d = 0$, also
$U_p = U_n$). Beide gelten nur, solange der Ausgang nicht in der Sättigung ist
($|U_a| < U_\mathrm{sat}$).

Liegt der nichtinvertierende Eingang auf Masse, ist der invertierende Eingang eine
virtuelle Masse. Die Knotenregel an diesem Punkt liefert den invertierenden Verstärker:

$$
\frac{U_e}{R_1} + \frac{U_a}{R_2} = 0 \quad\Rightarrow\quad V = \frac{U_a}{U_e} = -\frac{R_2}{R_1}
$$

Dieselbe Gleichung trägt durch den ganzen Kurs. Mehrere Eingangswiderstände an derselben
virtuellen Masse ergeben den Summierer. Beim nichtinvertierenden Verstärker wird der
Rückkopplungszweig zum Spannungsteiler, und mit $U_n = U_e$ folgt $V = 1 + R_2/R_1$; der
Spannungsfolger ist der Sonderfall $V = 1$. Ersetzt man $R_2$ durch einen Kondensator,
lädt der Strom $U_e/R$ ihn auf, und aus dem Verstärker wird der Integrierer:

$$
U_a(t) = -\frac{1}{RC} \int_0^t U_e(\tau)\,\mathrm{d}\tau + U_a(0)
$$

Eine konstante Eingangsspannung erzeugt also eine Rampe, die irgendwann an
$\pm U_\mathrm{sat}$ endet. Die Übersichtstabelle auf
Folie 13 stellt Übertragung und
Eingangswiderstand aller Schaltungen nebeneinander.

## Die Klausur auf einen Blick

Die Klausur ist schriftlich mit einem Multiple-Choice-Teil, dauert 90 Minuten und bringt
60 Punkte; bestanden ist sie mit 30 Punkten. Dieser Kurs plant mit dem 20.02.2027, die
Vorlesung nennt auf Folie 14
dagegen den 17.02.2027. Prüfe den Termin also rechtzeitig. Erlaubt sind ein nicht
programmierbarer Taschenrechner und ein handgeschriebenes DIN-A4-Blatt (beidseitig), also
zwei Seiten Formelsammlung.

Das Format stammt aus der einzigen Altklausur (WS 2025/26); die Aufteilung ist deshalb
eine gut begründete Schätzung, keine Garantie.

| Teil | Inhalt | Punkte | Zeit |
|---|---|---|---|
| MC-Teil | 6 Fragen zu je 2 Punkten, genau eine Antwort oder Mehrfachauswahl, nur vollständig richtig gewertet, keine Minuspunkte | 12 | 18 min |
| Rechenaufgabe | Invertierender Verstärker: Herleitung von $V$, Sättigung, Quelle mit Innenwiderstand | 16 | 24 min |
| Rechenaufgabe | Nichtinvertierender Verstärker dimensionieren, Spannungsfolger als Impedanzwandler | 14 | 21 min |
| Rechenaufgabe | Integrierer mit Sprungeingang bis zur Sättigung, Skizze, Frequenzgang | 18 | 27 min |

Pro Punkt hast du $1.5\,\mathrm{min}$, für eine MC-Frage also etwa $3\,\mathrm{min}$.
Daraus folgt:

- Die Grundschaltungen und der Integrierer bringen zusammen 97 % der Punkte; der ideale
  OPV zählt kaum direkt, steckt aber in jeder Herleitung.
- Der Integrierer allein ist die größte Aufgabe (18 Punkte). Seine Rampe, die
  Sättigungszeit und $f_1 = 1/(2\pi RC)$ müssen sicher sitzen.
- Herleitungen bringen Punkte für die Regeln und die Knotengleichung, nicht nur für das
  Ergebnis. Schreibe beides immer hin.
- Die [Probeklausur 1](exam:probeklausur-1) dieses Kurses hat dasselbe Format.

## So lernst du dieses Fach

- Halte dich an die Reihenfolge der Themenkarte: zuerst die zwei Regeln des
  [idealen OPV](topic:idealer-opv), dann die
  [Grundschaltungen](topic:verstaerker-grundschaltungen), zuletzt den
  [Integrierer](topic:integrierer).
- Beginne in jedem Thema mit den leichten Übungen, etwa
  [OPV ohne Rückkopplung](ex:ex-iopv-offener-betrieb),
  [Kennwerte eines invertierenden Verstärkers](ex:ex-vg-invertierer-kennwerte) und
  [Zeitkonstante und Frequenz f1 eines Integrierers](ex:ex-int-grenzfrequenz), und stelle
  immer zuerst die Knotengleichung am invertierenden Eingang auf, bevor du Zahlen
  einsetzt.
- Prüfe bei jedem Ergebnis, ob $|U_a| < U_\mathrm{sat}$ gilt; die Sättigung ist die
  häufigste Falle der Altklausur.
- Beantworte die MC-Fragen eines Themas direkt nach seiner Zusammenfassung und wiederhole
  sie später verteilt; jede Frage zählt nur, wenn sie ganz richtig ist.
- Schreibe dein zweiseitiges Formelblatt selbst, während du die Zusammenfassungen liest,
  und nutze es ab dann bei jeder Übung.
- Schreibe die [Probeklausur 1](exam:probeklausur-1) in den letzten zwei Wochen vor der
  Klausur am Stück in 90 Minuten und nur mit den erlaubten Hilfsmitteln.

## Voraussetzungen

- Ohmsches Gesetz, Knoten- und Maschenregel
- Spannungsteiler, auch belastet (Quelle mit Innenwiderstand an einer Last)
- Kondensator: $I_C = C \cdot \mathrm{d}U_C/\mathrm{d}t$, Integral einer konstanten Funktion
- Komplexe Zahlen: Betrag eines Bruchs wie $1/(j\omega RC)$
