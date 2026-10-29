// Lecture notes excerpt, chapter 4 (fake material for the ingest pipeline; see ../README.md).
#import "common.typ": *

#show: blatt.with("Skript, Kapitel 4")
#set heading(numbering: "1.1")
#counter(heading).update(3)

= Operationsverstärker

Der Operationsverstärker (OPV) ist ein Differenzverstärker mit sehr hoher
Leerlaufverstärkung $V_0$. Er wird fast nie ohne Rückkopplung betrieben: Erst die
Gegenkopplung macht aus dem empfindlichen Bauteil einen Verstärker, dessen Eigenschaften
allein durch die äußere Beschaltung festgelegt sind. Dieses Kapitel behandelt die
Grundschaltungen unter der Annahme eines idealen OPV.

== Der ideale Operationsverstärker

Die Ausgangsspannung ist der Differenzspannung $U_d = U_p - U_n$ proportional,
$ U_a = V_0 dot U_d . $
Für den idealen OPV gelten $V_0 -> infinity$, unendlich großer Eingangswiderstand (die
Eingangsströme $I_p$ und $I_n$ verschwinden) und verschwindender Ausgangswiderstand.
Ein realer OPV erreicht $V_0 approx 10^5$ bis $10^6$; seine Ausgangsspannung ist auf den
Bereich $-U_"sat" <= U_a <= U_"sat"$ begrenzt, wobei $U_"sat"$ etwas unter der
Versorgungsspannung $U_B$ liegt.

== Gegenkopplung und virtueller Kurzschluss

Wird ein Teil der Ausgangsspannung auf den invertierenden Eingang zurückgeführt, so stellt
sich der Ausgang so ein, dass $U_d$ verschwindet: Bei endlichem $U_a$ und $V_0 -> infinity$
muss $U_d = U_a / V_0 -> 0$ gelten. Für die Analyse gegengekoppelter Schaltungen genügen
daher zwei Regeln:

+ In die Eingänge fließt kein Strom: $I_p = I_n = 0$.
+ Die beiden Eingänge liegen auf gleichem Potential: $U_p = U_n$ (virtueller Kurzschluss).

Die Regeln gelten nur im linearen Bereich. Erreicht $U_a$ die Sättigung, ist die
Gegenkopplung unwirksam und $U_d$ nicht mehr null.

Mit endlicher Leerlaufverstärkung ergibt sich für eine Gegenkopplung mit dem
Rückkopplungsfaktor $k$ die Verstärkung
$ V = V_0 / (1 + k V_0) , $
die für $k V_0 >> 1$ gegen $1 / k$ strebt.

== Invertierender Verstärker

Die Eingangsspannung $U_e$ liegt über $R_1$ am invertierenden Eingang, der Widerstand $R_2$
verbindet Ausgang und invertierenden Eingang, der nichtinvertierende Eingang liegt auf
Masse. Wegen $U_p = 0$ ist der invertierende Eingang eine virtuelle Masse. Die Knotenregel
liefert
$ U_e / R_1 + U_a / R_2 = 0 quad => quad V = U_a / U_e = -R_2 / R_1 . $
Der Eingangswiderstand der Schaltung ist $R_1$, denn die Quelle sieht $R_1$ gegen die
virtuelle Masse. Eine Quelle mit Innenwiderstand $R_i$ liegt in Reihe zu $R_1$; die
Verstärkung sinkt dann auf $-R_2 / (R_1 + R_i)$.

== Nichtinvertierender Verstärker und Spannungsfolger

Hier liegt $U_e$ am nichtinvertierenden Eingang, und der Spannungsteiler aus $R_2$ (vom
Ausgang) und $R_1$ (nach Masse) führt $U_n = R_1 / (R_1 + R_2) dot U_a$ zurück. Aus
$U_n = U_p = U_e$ folgt
$ V = 1 + R_2 / R_1 . $
Der Eingangswiderstand ist (ideal) unendlich groß. Mit $R_2 = 0$ entsteht der
Spannungsfolger mit $V = 1$, der als Impedanzwandler hochohmige Quellen von niederohmigen
Lasten entkoppelt.

== Summierer

Werden mehrere Spannungen $U_1, dots, U_k$ über eigene Widerstände $R_1, dots, R_k$ an die
virtuelle Masse eines invertierenden Verstärkers mit Rückkopplungswiderstand $R_F$ gelegt,
so addieren sich die Ströme:
$ U_a = -R_F dot sum_(i = 1)^k U_i / R_i . $
Mit gleichen Widerständen $R_i = R_F$ ist $U_a = -(U_1 + dots + U_k)$.

== Integrierer

Ersetzt man im invertierenden Verstärker $R_2$ durch einen Kondensator $C$, fließt der
Strom $I = U_e / R$ in den Kondensator, und es gilt $C dot dif U_a \/ dif t = -I$:
$ U_a (t) = -1 / (R C) integral_0^t U_e (tau) dif tau + U_a (0) . $

#figure(
  fig("opv-integrierer", width: 62%),
  caption: [Integrierer mit $R = 10 "k"Omega$ und $C = 100 "nF"$ ($R C = 1 "ms"$).],
)

Eine konstante Eingangsspannung erzeugt eine Rampe mit der Steigung $-U_e / (R C)$, bis
der Ausgang die Sättigung erreicht. Im Frequenzbereich ist
$ underline(H) (j omega) = -1 / (j omega R C) , quad |underline(H)| = 1 "bei" f_1 = 1 / (2 pi R C) . $
Für $R C = 1 "ms"$ ist $f_1 approx 159.2 "Hz"$. Weil schon eine kleine Offsetspannung den
Ausgang mit der Zeit in die Sättigung treibt, legt man in der Praxis einen großen
Widerstand parallel zu $C$; er begrenzt die Gleichspannungsverstärkung.
