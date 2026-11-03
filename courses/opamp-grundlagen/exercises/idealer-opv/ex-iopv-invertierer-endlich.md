---
id: ex-iopv-invertierer-endlich
title: Invertierender Verstärker mit endlicher Leerlaufverstärkung
topic: idealer-opv
difficulty: 3
kind: derive
minutes: 16
source: {doc: skript-kapitel4-operationsverstaerker, page: 1, relation: inspired}
answers:
  - {key: Vexpr, label: 'Verstärkung $V = U_a/U_e$ als Formel in $R_1$, $R_2$ und $V_0$', expr: '-R2*V0/(R1*V0 + R1 + R2)', symbols: [R1, R2, V0]}
  - {key: V, label: 'Verstärkung $V$ mit $V_0 = 1000$', value: -20.813, rtol: 5.0e-3}
  - {key: dev, label: 'Abweichung von $|V|$ gegenüber $R_2/R_1$', value: 2.1791, unit: '%', rtol: 5.0e-3}
  - {key: Un, label: 'Spannung $U_n$ am invertierenden Eingang', value: 4.1626, unit: mV, rtol: 5.0e-3}
---

Ein invertierender Verstärker besteht aus $R_1$ (vom Eingang zum invertierenden Eingang)
und $R_2$ (vom Ausgang zum invertierenden Eingang); der nichtinvertierende Eingang liegt
auf Masse. Der OPV hat keine Eingangsströme, aber nur die endliche Leerlaufverstärkung
$V_0$, also $U_a = V_0 (U_p - U_n)$. Die Sättigung spielt keine Rolle.

![Invertierender Verstärker mit R1 im Eingang und R2 in der Rückführung, nichtinvertierender Eingang auf Masse](fig:idealer-opv-invertierer-symbolisch)

**a)** Leiten Sie die Verstärkung $V = U_a/U_e$ als Funktion von $R_1$, $R_2$ und $V_0$
her.

**b)** Zeigen Sie, dass für $V_0 \to \infty$ die Verstärkung des idealen invertierenden
Verstärkers herauskommt.

**c)** Berechnen Sie $V$ für $R_1 = 4.7\,\mathrm{k\Omega}$, $R_2 = 100\,\mathrm{k\Omega}$
und $V_0 = 1000$.

**d)** Um wie viel Prozent ist $|V|$ kleiner als $R_2/R_1$?

**e)** Am Eingang liegt $U_e = 0.2\,\mathrm{V}$. Welche Spannung $U_n$ stellt sich am
invertierenden Eingang ein?

::: hint
Weil kein Strom in den Eingang fließt, ist $U_n$ ein Spannungsteiler zwischen $U_e$ und
$U_a$: Stellen Sie die Knotenregel am invertierenden Eingang auf, ohne $U_n = 0$
vorauszusetzen.
:::

::: hint
Lösen Sie die Knotengleichung nach $U_n$ auf und setzen Sie das Ergebnis in
$U_a = -V_0 U_n$ ein.
:::

::: hint
Nach dem Einsetzen steht $U_a$ auf beiden Seiten: Sammeln Sie alle Terme mit $U_a$
links und teilen Sie durch $U_e$.
:::

::: solution
**a)** Knotenregel am invertierenden Eingang mit $I_n = 0$:

$$
\frac{U_e - U_n}{R_1} + \frac{U_a - U_n}{R_2} = 0 \quad\Rightarrow\quad U_n = \frac{R_2 U_e + R_1 U_a}{R_1 + R_2}
$$

Mit $U_p = 0$ ist $U_a = -V_0 U_n$. Einsetzen und nach $U_a$ auflösen:

$$
U_a \left(1 + \frac{V_0 R_1}{R_1 + R_2}\right) = -\frac{V_0 R_2}{R_1 + R_2} U_e \quad\Rightarrow\quad V = -\frac{V_0 R_2}{R_1 V_0 + R_1 + R_2}
$$

**b)** Zähler und Nenner durch $V_0$ teilen:
$V = -R_2/(R_1 + (R_1 + R_2)/V_0)$. Für $V_0 \to \infty$ verschwindet der zweite
Summand, und es bleibt $V = -R_2/R_1$.

**c)** Mit $k = 4.7/104.7 \approx 0.04489$ ist $k V_0 \approx 44.89$ und

$$
V = -\frac{100\,\mathrm{k\Omega}}{4.7\,\mathrm{k\Omega}} \cdot \frac{44.89}{45.89} \approx -21.28 \cdot 0.9782 \approx -20.81
$$

**d)** Die Abweichung ist $\frac{1}{1 + k V_0} = \frac{1}{45.89} \approx 0.0218 = 2.18\,\%$.

**e)** $U_a = V \cdot U_e \approx -20.81 \cdot 0.2\,\mathrm{V} \approx -4.163\,\mathrm{V}$, also

$$
U_n = -\frac{U_a}{V_0} = \frac{4.163\,\mathrm{V}}{1000} \approx 4.16\,\mathrm{mV}
$$

Der invertierende Eingang ist nur näherungsweise eine virtuelle Masse; je größer $V_0$,
desto näher liegt $U_n$ bei null.
:::
