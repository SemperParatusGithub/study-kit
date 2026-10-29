// Lecture 3 slides (fake material for the ingest pipeline; see ../README.md).
#import "common.typ": *

#show: folien.with("Vorlesung 3: Operationsverstärker-Grundschaltungen")

#align(center + horizon)[
  #text(size: 28pt, weight: "bold", fill: rgb("#1b4f8a"))[Operationsverstärker-Grundschaltungen]
  #v(0.6em)
  #text(size: 18pt)[Elektronik 1 · Vorlesung 3]
  #v(1.2em)
  #lehrstuhl \
  Wintersemester 2026/27
]

#folie[Gliederung][
  + Der ideale Operationsverstärker (OPV)
  + Gegenkopplung und virtueller Kurzschluss
  + Invertierender Verstärker
  + Nichtinvertierender Verstärker und Spannungsfolger
  + Summierer (Addierer)
  + Integrierer
  + Zusammenfassung und Klausurhinweise
]

#folie[Der ideale Operationsverstärker][
  Ausgangsspannung proportional zur Differenzspannung:
  $ U_a = V_0 dot (U_p - U_n) = V_0 dot U_d $
  Idealisierungen:
  - Leerlaufverstärkung $V_0 -> infinity$
  - Eingangswiderstand $R_e -> infinity$, also Eingangsströme $I_p = I_n = 0$
  - Ausgangswiderstand $R_a -> 0$
  - unbegrenzte Bandbreite, keine Offsetspannung
  Real: $V_0 approx 10^5$, Ausgang begrenzt auf $plus.minus U_"sat"$ (etwas unter $plus.minus U_B$).
]

#folie[Gegenkopplung: die zwei goldenen Regeln][
  Mit Gegenkopplung (Rückführung vom Ausgang auf den invertierenden Eingang) gilt im
  linearen Betrieb:
  #merke[
    + Es fließt kein Strom in die Eingänge: $I_p = I_n = 0$.
    + Die Differenzspannung ist null: $U_d = U_p - U_n = 0$ (virtueller Kurzschluss).
  ]
  Liegt $U_p$ auf Masse, so ist der invertierende Eingang eine *virtuelle Masse*: $U_n = 0$,
  obwohl keine Verbindung zur Masse besteht.

  Gilt nur, solange der Ausgang nicht in der Sättigung ist: $|U_a| < U_"sat"$.
]

#folie[Invertierender Verstärker][
  #grid(
    columns: (1.1fr, 1fr),
    gutter: 1em,
    fig("opv-invertierend"),
    [
      - $U_e$ über $R_1$ an den invertierenden Eingang
      - $R_2$ koppelt den Ausgang zurück
      - nichtinvertierender Eingang auf Masse
      #v(0.5em)
      $ V = U_a / U_e = -R_2 / R_1 $
    ],
  )
]

#folie[Invertierender Verstärker: Herleitung][
  Knotenregel am invertierenden Eingang (virtuelle Masse, $U_n = 0$, $I_n = 0$):
  $ (U_e - 0) / R_1 + (U_a - 0) / R_2 = 0 quad => quad U_a = -R_2 / R_1 dot U_e $
  - Eingangswiderstand der Schaltung: $R_"ein" = U_e / I_e = R_1$
  - Vorzeichen: Ausgang gegenphasig zum Eingang (Phasendrehung um $180 degree$)
  - Verstärkung hängt nur von den Widerständen ab, nicht von $V_0$
]

#folie[Beispiel: invertierender Verstärker][
  Gegeben: $R_1 = 10 "k"Omega$, $R_2 = 47 "k"Omega$, $U_e = 0.2 "V"$, Versorgung
  $plus.minus 12 "V"$ (Sättigung näherungsweise bei $plus.minus 12 "V"$).
  $ V = -(47 "k"Omega) / (10 "k"Omega) = -4.7 quad quad U_a = -4.7 dot 0.2 "V" = -0.94 "V" $
  Größte Eingangsamplitude ohne Sättigung:
  $ |U_e|_max = (12 "V") / 4.7 approx 2.55 "V" $
  Eingangsstrom: $I_e = U_e / R_1 = 20 mu"A"$.
]

#folie[Nichtinvertierender Verstärker][
  #grid(
    columns: (1.1fr, 1fr),
    gutter: 1em,
    fig("opv-nichtinvertierend"),
    [
      Spannungsteiler $R_1$, $R_2$ im Rückkopplungszweig, $U_n = U_e$:
      $ U_e = R_1 / (R_1 + R_2) dot U_a $
      $ V = 1 + R_2 / R_1 $
      Beispiel: $R_1 = 10 "k"Omega$, $R_2 = 22 "k"Omega$ ergibt $V = 3.2$.
    ],
  )
]

#folie[Spannungsfolger (Impedanzwandler)][
  Sonderfall $R_2 = 0$, $R_1 -> infinity$: Ausgang direkt auf den invertierenden Eingang.
  $ V = 1, quad R_"ein" -> infinity, quad R_"aus" -> 0 $
  Beispiel: Quelle $U_0$ mit Innenwiderstand $R_i = 10 "k"Omega$ an Last
  $R_L = 1 "k"Omega$:
  - direkt angeschlossen: $U_L = U_0 dot R_L / (R_i + R_L) approx 0.091 dot U_0$
  - mit Spannungsfolger: $U_L = U_0$, denn in den Eingang fließt kein Strom
]

#folie[Summierer (Addierer)][
  Mehrere Eingänge über $R_1, R_2, dots$ an die virtuelle Masse, Rückkopplung $R_F$:
  $ U_a = -R_F dot (U_1 / R_1 + U_2 / R_2 + dots + U_k / R_k) $
  Die Eingangsströme addieren sich am Knoten; die Eingänge beeinflussen sich nicht.

  Beispiel: $R_F = 10 "k"Omega$, $R_1 = 10 "k"Omega$, $R_2 = 20 "k"Omega$,
  $U_1 = 0.5 "V"$, $U_2 = 0.8 "V"$:
  $ U_a = -10 "k"Omega dot ((0.5 "V") / (10 "k"Omega) + (0.8 "V") / (20 "k"Omega)) = -0.9 "V" $
]

#folie[Integrierer][
  #grid(
    columns: (1.1fr, 1fr),
    gutter: 1em,
    fig("opv-integrierer"),
    [
      Kondensator im Rückkopplungszweig, $I_C = U_e / R$:
      $ U_a (t) = -1 / (R C) integral_0^t U_e (tau) dif tau + U_a (0) $
      Mit $R = 10 "k"Omega$, $C = 100 "nF"$: $R C = 1 "ms"$.
    ],
  )
]

#folie[Integrierer: Sprung am Eingang][
  Konstante Eingangsspannung $U_e = 0.5 "V"$ ab $t = 0$, $U_a (0) = 0$:
  $ U_a (t) = -(0.5 "V") / (1 "ms") dot t = -500 "V"/"s" dot t $
  - der Ausgang ist eine fallende Rampe
  - bei $U_"sat" = 12 "V"$ ist die Sättigung nach $t = 24 "ms"$ erreicht
  Im Frequenzbereich: $underline(H)(j omega) = -1 / (j omega R C)$, also $|underline(H)| = 1$
  bei $f_1 = 1 / (2 pi R C) approx 159 "Hz"$.
]

#folie[Zusammenfassung][
  #table(
    columns: (auto, auto, auto),
    inset: 0.45em,
    stroke: 0.6pt + luma(140),
    table.header([*Schaltung*], [*Übertragung*], [*Eingangswiderstand*]),
    [Invertierender Verstärker], [$U_a = -R_2 / R_1 dot U_e$], [$R_1$],
    [Nichtinvertierender Verstärker], [$U_a = (1 + R_2 / R_1) dot U_e$], [$-> infinity$],
    [Spannungsfolger], [$U_a = U_e$], [$-> infinity$],
    [Summierer], [$U_a = -R_F sum_k U_k / R_k$], [$R_k$ je Eingang],
    [Integrierer], [$U_a = -1 / (R C) integral U_e dif t$], [$R$],
  )
]

#folie[Organisatorisches und Klausurhinweise][
  - Übungsblatt 3 (Grundschaltungen) bis zur nächsten Übung bearbeiten
  - Klausurtermin: *17.02.2027*, 90 Minuten, schriftlich mit Multiple-Choice-Teil
  - Hilfsmittel: nicht programmierbarer Taschenrechner, ein handgeschriebenes DIN-A4-Blatt
    (beidseitig)
  - Altklausur WS 2025/26 mit Lösungen liegt im Kursordner
]
