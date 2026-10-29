// Old exercise sheet 2 from WS 2023/24. build.py renders it to a low-resolution PNG, rotates
// it slightly and adds noise, and wraps the image in a PDF without a text layer: the
// "scan" the ingest pipeline must flag as a visual page (see ../README.md).
#import "common.typ": *

#show: blatt.with("Übungsblatt 2 (WS 2023/24)")

= Übungsblatt 2: Gegenkopplung

#aufgabe(1, [Endliche Leerlaufverstärkung])[
  Ein nichtinvertierender Verstärker mit $R_1 = 1 "k"Omega$ (nach Masse) und
  $R_2 = 9 "k"Omega$ (Rückkopplung) ist mit einem OPV der Leerlaufverstärkung $V_0 = 10^5$
  aufgebaut.
  + Berechnen Sie den Rückkopplungsfaktor $k = R_1 \/ (R_1 + R_2)$.
  + Berechnen Sie die Verstärkung $V = V_0 \/ (1 + k V_0)$ und vergleichen Sie mit dem
    idealen Wert $1 \/ k$.
  + Wie groß ist der relative Fehler gegenüber dem idealen Wert?
]

#aufgabe(2, [Virtuelle Masse])[
  Erklären Sie, warum der invertierende Eingang eines invertierenden Verstärkers auf
  Massepotential liegt, obwohl er nicht mit Masse verbunden ist. Unter welcher Bedingung
  gilt diese Aussage nicht mehr?
]

#aufgabe(3, [Spannungsfolger])[
  Eine Quelle mit $U_0 = 2 "V"$ und $R_i = 100 "k"Omega$ speist eine Last
  $R_L = 10 "k"Omega$. Berechnen Sie die Lastspannung ohne und mit Spannungsfolger.
]

#v(1em)
_Lösungshinweise:_ A1: $k = 0.1$, $V approx 9.999$, Fehler $approx 0.01 %$.
A3: ohne Folger $U_L approx 0.18 "V"$, mit Folger $U_L = 2 "V"$.
