---
id: ex-int-zwei-abschnitte
title: Integrierer mit zwei Eingangsabschnitten
topic: integrierer
difficulty: 3
kind: compute
minutes: 15
answers:
  - {key: t0a, label: 'Zeitpunkt $t_\mathrm{A}$ des ersten Nulldurchgangs von $U_a$', value: 5.0, unit: ms, rtol: 5.0e-3}
  - {key: Ua8, label: 'Ausgangsspannung $U_a$ bei $t = 8\,\mathrm{ms}$', value: -0.9, unit: V, rtol: 5.0e-3}
  - {key: Ua20, label: 'Ausgangsspannung $U_a$ bei $t = 20\,\mathrm{ms}$', value: 0.6, unit: V, rtol: 5.0e-3}
  - {key: t0b, label: 'Zeitpunkt $t_\mathrm{B}$ des zweiten Nulldurchgangs von $U_a$', value: 15.2, unit: ms, rtol: 5.0e-3}
---

Ein Integrierer mit idealem OPV hat $R = 20\,\mathrm{k\Omega}$ und $C = 100\,\mathrm{nF}$;
der Ausgang ist auf $\pm 10\,\mathrm{V}$ begrenzt. Der Kondensator ist zu Beginn so
geladen, dass $U_a(0) = 1.5\,\mathrm{V}$ ist. Die Eingangsspannung beträgt
$U_e = 0.6\,\mathrm{V}$ für $0 \le t < 8\,\mathrm{ms}$ und danach
$U_e = -0.25\,\mathrm{V}$.

![Eingangsspannung: 0.6 V von 0 bis 8 ms, danach −0.25 V](fig:integrierer-zwei-phasen)

**a)** Zu welchem Zeitpunkt $t_\mathrm{A}$ geht $U_a$ zum ersten Mal durch null?

**b)** Wie groß ist $U_a$ bei $t = 8\,\mathrm{ms}$?

**c)** Wie groß ist $U_a$ bei $t = 20\,\mathrm{ms}$?

**d)** Zu welchem Zeitpunkt $t_\mathrm{B}$ geht $U_a$ zum zweiten Mal durch null?

::: hint
In jedem Abschnitt mit konstantem $U_e$ ist $U_a(t)$ eine Gerade mit der Steigung
$-U_e/(RC)$.
:::

::: hint
Die Kondensatorspannung springt nicht: Der Wert von $U_a$ am Ende des ersten Abschnitts
ist der Anfangswert des zweiten.
:::

::: hint
Im ersten Abschnitt fällt der Ausgang mit $300\,\mathrm{V/s}$, im zweiten steigt er.
:::

::: solution
Es ist $RC = 20\,\mathrm{k\Omega} \cdot 100\,\mathrm{nF} = 2\,\mathrm{ms}$.

**a)** Im ersten Abschnitt ist die Steigung
$-U_e/(RC) = -0.6\,\mathrm{V}/2\,\mathrm{ms} = -300\,\mathrm{V/s}$:

$$
U_a(t) = 1.5\,\mathrm{V} - 300\,\frac{\mathrm{V}}{\mathrm{s}} \cdot t = 0 \quad\Rightarrow\quad t_\mathrm{A} = \frac{1.5\,\mathrm{V}}{300\,\mathrm{V/s}} = 5\,\mathrm{ms}
$$

**b)** $U_a(8\,\mathrm{ms}) = 1.5\,\mathrm{V} - 300\,\mathrm{V/s} \cdot 8\,\mathrm{ms} = 1.5\,\mathrm{V} - 2.4\,\mathrm{V} = -0.9\,\mathrm{V}$

**c)** Im zweiten Abschnitt ist die Steigung
$-(-0.25\,\mathrm{V})/2\,\mathrm{ms} = +125\,\mathrm{V/s}$, und die Rampe startet bei
$-0.9\,\mathrm{V}$:

$$
U_a(20\,\mathrm{ms}) = -0.9\,\mathrm{V} + 125\,\frac{\mathrm{V}}{\mathrm{s}} \cdot 12\,\mathrm{ms} = -0.9\,\mathrm{V} + 1.5\,\mathrm{V} = 0.6\,\mathrm{V}
$$

**d)** Ab $t = 8\,\mathrm{ms}$ braucht die Rampe $0.9\,\mathrm{V}/(125\,\mathrm{V/s}) = 7.2\,\mathrm{ms}$
bis null, also $t_\mathrm{B} = 8\,\mathrm{ms} + 7.2\,\mathrm{ms} = 15.2\,\mathrm{ms}$. Die
Sättigung bei $\pm 10\,\mathrm{V}$ wird nie erreicht.
:::
