// Exercise sheet 3 (fake material for the ingest pipeline; see ../README.md).
#import "common.typ": *

#show: blatt.with("Übungsblatt 3")

= Übungsblatt 3: Operationsverstärker-Grundschaltungen

Alle Operationsverstärker sind ideal. Die Ausgangsspannung ist auf $plus.minus 13 "V"$
begrenzt. Bearbeitungshinweis: Stellen Sie zuerst die Knotengleichung am invertierenden
Eingang auf und setzen Sie erst danach Zahlen ein.

#aufgabe(1, [Invertierender Verstärker])[
  #fig("opv-symbolisch", width: 55%)

  Gegeben sind $R_1 = 4.7 "k"Omega$, $R_2 = 33 "k"Omega$ und $U_e = 0.3 "V"$.
  + Leiten Sie die Spannungsverstärkung $V = U_a \/ U_e$ her und berechnen Sie ihren Wert.
  + Berechnen Sie die Ausgangsspannung $U_a$.
  + Wie groß sind der Eingangswiderstand der Schaltung und der Eingangsstrom $I_e$?
  + Bis zu welchem Betrag der Eingangsspannung arbeitet die Schaltung linear?
]

#aufgabe(2, [Nichtinvertierender Verstärker])[
  Ein nichtinvertierender Verstärker soll die Verstärkung $V = 11$ haben. Der Widerstand
  vom invertierenden Eingang nach Masse ist $R_1 = 1 "k"Omega$.
  + Bestimmen Sie den Rückkopplungswiderstand $R_2$.
  + Berechnen Sie $U_a$ für $U_e = 0.25 "V"$.
  + Welcher Strom fließt durch $R_1$?
]

#aufgabe(3, [Summierer])[
  Ein Summierer hat den Rückkopplungswiderstand $R_F = 15 "k"Omega$ und drei Eingänge mit
  $R_1 = 5 "k"Omega$, $R_2 = 15 "k"Omega$ und $R_3 = 30 "k"Omega$. Es liegen
  $U_1 = 0.2 "V"$, $U_2 = -0.6 "V"$ und $U_3 = 1.2 "V"$ an.
  + Stellen Sie die Gleichung für $U_a$ auf.
  + Berechnen Sie $U_a$.
]

#aufgabe(4, [Integrierer])[
  Ein Integrierer besteht aus $R = 20 "k"Omega$ und $C = 47 "nF"$. Ab $t = 0$ liegt die
  konstante Spannung $U_e = -0.4 "V"$ an, der Kondensator ist bei $t = 0$ entladen.
  + Geben Sie $U_a (t)$ an und berechnen Sie die Steigung der Ausgangsspannung.
  + Nach welcher Zeit erreicht $U_a$ den Wert $10 "V"$?
  + Bei welcher Frequenz ist der Betrag des Frequenzgangs gleich eins?
]
