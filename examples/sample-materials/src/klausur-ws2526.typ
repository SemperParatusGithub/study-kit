// Past exam WS 2025/26 (fake material for the ingest pipeline; see ../README.md).
#import "common.typ": *

#show: blatt.with("Klausur WS 2025/26")

#let kaestchen = box(width: 0.8em, height: 0.8em, stroke: 0.6pt, baseline: 0.1em)
#let mc(frage, mehrfach: false, optionen) = block(breakable: false, width: 100%)[
  #frage #if mehrfach [_(Mehrfachauswahl)_] else [_(genau eine Antwort)_]
  #set list(marker: kaestchen, indent: 1em)
  #optionen
]

#align(center)[
  #text(size: 17pt, weight: "bold")[Klausur Elektronik 1] \
  Wintersemester 2025/26 · 18.02.2026
]

#v(0.5em)
#table(
  columns: (1fr, 1fr),
  inset: 0.6em,
  [Name:], [Matrikelnummer:],
)

*Bearbeitungszeit:* 90 Minuten · *Gesamtpunktzahl:* 60 Punkte · *Bestanden ab* 30 Punkten

*Hilfsmittel:* nicht programmierbarer Taschenrechner, ein handgeschriebenes DIN-A4-Blatt
(beidseitig). Alle Operationsverstärker sind ideal; die Ausgangsspannung ist auf
$plus.minus 11 "V"$ begrenzt.

#table(
  columns: (auto, 1fr, 1fr, 1fr, 1fr, 1fr),
  inset: 0.5em,
  align: center,
  [Aufgabe], [1], [2], [3], [4], [Summe],
  [Punkte], [12], [16], [14], [18], [60],
  [erreicht], [], [], [], [], [],
)

#aufgabe(1, [Multiple Choice], punkte: 12)[
  Jede Frage zählt 2 Punkte und wird nur bei vollständig richtiger Antwort gewertet; es gibt
  keine Minuspunkte.

  #mc[1.1 Für einen idealen OPV mit Gegenkopplung im linearen Betrieb gilt:][
    - $U_a = 0$
    - $U_p - U_n = 0$
    - $I_n = U_a / R_2$
    - $U_n = U_B$
  ]
  #mc(mehrfach: true)[1.2 Welche Aussagen zum invertierenden Verstärker sind richtig?][
    - Der Eingangswiderstand der Schaltung ist $R_1$.
    - Die Verstärkung ist $-R_2 / R_1$.
    - Ausgangs- und Eingangsspannung sind gleichphasig.
    - Der Eingangswiderstand ist unendlich groß.
  ]
  #mc[1.3 Die Spannungsverstärkung eines Spannungsfolgers ist][
    - $0$
    - $1$
    - $-1$
    - $V_0$
  ]
  #mc[1.4 Summierer mit $R_F = R_1 = R_2 = 10 "k"Omega$, $U_1 = 1 "V"$, $U_2 = 2 "V"$:
    $U_a$ ist][
    - $3 "V"$
    - $-3 "V"$
    - $-1.5 "V"$
    - $1.5 "V"$
  ]
  #mc[1.5 An einem Integrierer liegt eine konstante Eingangsspannung. Der Ausgang zeigt][
    - eine Rampe, bis die Sättigung erreicht ist
    - einen Sprung
    - eine Sinusschwingung
    - eine konstante Spannung
  ]
  #mc[1.6 Nichtinvertierender Verstärker mit $R_1 = 1 "k"Omega$ (nach Masse) und
    $R_2 = 4 "k"Omega$ (Rückkopplung): $V$ ist][
    - $4$
    - $-4$
    - $5$
    - $0.8$
  ]
]

#aufgabe(2, [Invertierender Verstärker], punkte: 16)[
  #fig("opv-symbolisch", width: 50%)

  Gegeben: $R_1 = 2.2 "k"Omega$, $R_2 = 15 "k"Omega$.
  + Leiten Sie $V = U_a \/ U_e$ mit den Regeln des idealen OPV her. (4 P)
  + Berechnen Sie $V$. (2 P)
  + Berechnen Sie $U_a$ für $U_e = 0.5 "V"$. (2 P)
  + Welche Ausgangsspannung stellt sich für $U_e = 2 "V"$ ein? Begründen Sie. (4 P)
  + Die Eingangsspannung kommt aus einer Quelle mit Innenwiderstand $R_i = 1 "k"Omega$.
    Wie groß ist die Verstärkung $U_a \/ U_0$ bezogen auf die Leerlaufspannung $U_0$? (4 P)
]

#aufgabe(3, [Nichtinvertierender Verstärker und Impedanzwandler], punkte: 14)[
  + Dimensionieren Sie $R_2$ für $V = 6$ bei $R_1 = 3.3 "k"Omega$. (4 P)
  + Berechnen Sie $U_a$ für $U_e = 0.8 "V"$. (2 P)
  + Ein Sensor ($U_0 = 1.5 "V"$, $R_i = 47 "k"Omega$) soll eine Last $R_L = 4.7 "k"Omega$
    speisen. Berechnen Sie $U_L$ ohne und mit Spannungsfolger. (4 P)
  + Begründen Sie, warum der Eingangswiderstand des nichtinvertierenden Verstärkers ideal
    unendlich groß ist. (4 P)
]

#aufgabe(4, [Integrierer], punkte: 18)[
  Ein Integrierer besteht aus $R = 47 "k"Omega$ und $C = 220 "nF"$. Ab $t = 0$ liegt
  $U_e = 1 "V"$ an; $U_a (0) = 0$.
  + Geben Sie $U_a (t)$ allgemein und mit Zahlen an. (4 P)
  + Wann erreicht der Ausgang die Sättigung? (4 P)
  + Skizzieren Sie $U_e (t)$ und $U_a (t)$ für $0 <= t <= 150 "ms"$. (4 P)
  + Bei welcher Frequenz $f_1$ ist $|underline(H) (j omega)| = 1$? Wie groß ist
    $|underline(H)|$ bei $f = 100 "Hz"$? (6 P)
]
