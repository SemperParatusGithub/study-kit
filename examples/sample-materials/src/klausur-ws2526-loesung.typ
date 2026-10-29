// Solutions to the past exam WS 2025/26 (fake material for the ingest pipeline; see ../README.md).
#import "common.typ": *

#show: blatt.with("Musterlösung Klausur WS 2025/26")

#align(center)[
  #text(size: 17pt, weight: "bold")[Musterlösung zur Klausur Elektronik 1] \
  Wintersemester 2025/26 · 18.02.2026
]

#aufgabe(1, [Multiple Choice], punkte: 12)[
  #table(
    columns: (auto, auto, 1fr),
    inset: 0.45em,
    [*Frage*], [*Richtig*], [*Begründung*],
    [1.1], [B], [virtueller Kurzschluss: $U_p = U_n$],
    [1.2], [A, B], [virtuelle Masse am invertierenden Eingang; Ausgang gegenphasig],
    [1.3], [B], [$V = 1 + R_2 \/ R_1$ mit $R_2 = 0$],
    [1.4], [B], [$U_a = -(U_1 + U_2) = -3 "V"$ bei gleichen Widerständen],
    [1.5], [A], [Integral einer Konstanten ist eine Rampe],
    [1.6], [C], [$V = 1 + 4 "k"Omega \/ 1 "k"Omega = 5$],
  )
  Je 2 Punkte, nur vollständig richtig.
]

#aufgabe(2, [Invertierender Verstärker], punkte: 16)[
  + $U_n = U_p = 0$ und $I_n = 0$, Knotenregel:
    $U_e \/ R_1 + U_a \/ R_2 = 0$, also $V = -R_2 \/ R_1$. (4 P: Regeln 2, Gleichung 1,
    Ergebnis 1)
  + $V = -(15 "k"Omega) / (2.2 "k"Omega) approx -6.82$ (2 P)
  + $U_a = -6.82 dot 0.5 "V" approx -3.41 "V"$ (2 P)
  + Rechnerisch $-6.82 dot 2 "V" approx -13.6 "V"$; das liegt außerhalb von
    $plus.minus 11 "V"$, der Ausgang geht in die Sättigung: $U_a = -11 "V"$. (4 P)
  + $R_i$ liegt in Reihe zu $R_1$:
    $ U_a / U_0 = -R_2 / (R_1 + R_i) = -(15 "k"Omega) / (3.2 "k"Omega) approx -4.69 $ (4 P)
]

#aufgabe(3, [Nichtinvertierender Verstärker und Impedanzwandler], punkte: 14)[
  + $R_2 = (V - 1) dot R_1 = 5 dot 3.3 "k"Omega = 16.5 "k"Omega$ (4 P)
  + $U_a = 6 dot 0.8 "V" = 4.8 "V"$ (2 P)
  + Ohne Folger: $U_L = 1.5 "V" dot (4.7 "k"Omega) / (51.7 "k"Omega) approx 0.136 "V"$;
    mit Folger: $U_L = 1.5 "V"$, weil in den Eingang kein Strom fließt. (4 P)
  + $U_e$ liegt direkt am nichtinvertierenden Eingang, in den beim idealen OPV kein Strom
    fließt; die Quelle wird also nicht belastet. (4 P)
]

#aufgabe(4, [Integrierer], punkte: 18)[
  + $U_a (t) = -1 / (R C) integral_0^t U_e dif tau = -(U_e) / (R C) dot t$ mit
    $R C = 47 "k"Omega dot 220 "nF" = 10.34 "ms"$:
    $U_a (t) approx -96.7 "V"/"s" dot t$ (4 P)
  + $t_"sat" = (11 "V") / (96.7 "V"/"s") approx 113.7 "ms"$ (4 P)
  + $U_e$: Sprung auf $1 "V"$ bei $t = 0$. $U_a$: fallende Gerade von $0$ auf $-11 "V"$ bei
    $113.7 "ms"$, danach konstant $-11 "V"$. (4 P)
  + $f_1 = 1 / (2 pi R C) approx 15.4 "Hz"$; bei $100 "Hz"$:
    $|underline(H)| = 1 / (2 pi dot 100 "Hz" dot 10.34 "ms") approx 0.154$ (6 P)
]
