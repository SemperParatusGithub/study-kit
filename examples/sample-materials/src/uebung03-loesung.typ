// Solutions to exercise sheet 3 (fake material for the ingest pipeline; see ../README.md).
#import "common.typ": *

#show: blatt.with("Lösungen zu Übungsblatt 3")

= Lösungen zu Übungsblatt 3

#aufgabe(1, [Invertierender Verstärker])[
  + Virtuelle Masse am invertierenden Eingang, kein Eingangsstrom:
    $ U_e / R_1 + U_a / R_2 = 0 quad => quad V = -R_2 / R_1 = -(33 "k"Omega) / (4.7 "k"Omega) approx -7.02 $
  + $U_a = V dot U_e = -7.02 dot 0.3 "V" approx -2.11 "V"$
  + $R_"ein" = R_1 = 4.7 "k"Omega$, $I_e = U_e / R_1 = (0.3 "V") / (4.7 "k"Omega) approx 63.8 mu"A"$
  + $|U_e| <= (13 "V") / 7.02 approx 1.85 "V"$
]

#aufgabe(2, [Nichtinvertierender Verstärker])[
  + $V = 1 + R_2 / R_1 = 11 => R_2 = 10 dot R_1 = 10 "k"Omega$
  + $U_a = 11 dot 0.25 "V" = 2.75 "V"$
  + $U_n = U_e = 0.25 "V"$ liegt über $R_1$: $I = (0.25 "V") / (1 "k"Omega) = 0.25 "mA"$
]

#aufgabe(3, [Summierer])[
  + $U_a = -R_F dot (U_1 / R_1 + U_2 / R_2 + U_3 / R_3)$
  + Die drei Ströme sind $40 mu"A"$, $-40 mu"A"$ und $40 mu"A"$, zusammen $40 mu"A"$:
    $ U_a = -15 "k"Omega dot 40 mu"A" = -0.6 "V" $
]

#aufgabe(4, [Integrierer])[
  + $R C = 20 "k"Omega dot 47 "nF" = 0.94 "ms"$ und
    $ U_a (t) = -1 / (R C) dot U_e dot t = (0.4 "V") / (0.94 "ms") dot t approx 425.5 "V"/"s" dot t $
    Die Ausgangsspannung steigt, weil $U_e$ negativ ist.
  + $t = (10 "V") / (425.5 "V"/"s") approx 23.5 "ms"$
  + $|underline(H)| = 1 / (omega R C) = 1$ bei $f_1 = 1 / (2 pi R C) approx 169.3 "Hz"$
]
