---
id: ex-vg-nichtinvertierer-impedanzwandler
title: Nichtinvertierender Verstärker und Impedanzwandler für einen Sensor
topic: verstaerker-grundschaltungen
difficulty: 4
kind: compute
minutes: 21
source: {doc: klausur-ws2025-26, page: 2, relation: inspired}
answers:
  - {key: R2, label: 'Rückkopplungswiderstand $R_2$', value: 17.55, unit: kΩ, rtol: 5.0e-3}
  - {key: Ua, label: '$U_a$ für $U_e = 0.65\,\mathrm{V}$', value: 4.875, unit: V, rtol: 5.0e-3}
  - {key: UL1, label: 'Lastspannung $U_L$ ohne Spannungsfolger', value: 0.07032, unit: V, rtol: 5.0e-3}
  - {key: UL2, label: 'Lastspannung $U_L$ mit Spannungsfolger', value: 1.1, unit: V, rtol: 5.0e-3}
  - {key: Ua0, label: '$U_a$ mit dem Sensor direkt am Verstärkereingang', value: 8.25, unit: V, rtol: 5.0e-3}
---

Ein nichtinvertierender Verstärker mit idealem OPV soll die Verstärkung $V = 7.5$ haben;
$R_1 = 2.7\,\mathrm{k\Omega}$ liegt vom invertierenden Eingang nach Masse. Der Ausgang ist auf
$\pm 12\,\mathrm{V}$ begrenzt.

![Nichtinvertierender Verstärker mit dem Spannungsteiler aus R2 und R1 im Rückkopplungszweig](fig:verstaerker-grundschaltungen-nichtinvertierer)

**a)** Dimensionieren Sie $R_2$.

**b)** Berechnen Sie $U_a$ für $U_e = 0.65\,\mathrm{V}$.

**c)** Ein Sensor ($U_0 = 1.1\,\mathrm{V}$, $R_i = 82\,\mathrm{k\Omega}$) soll eine Last
$R_L = 5.6\,\mathrm{k\Omega}$ speisen. Berechnen Sie $U_L$ ohne und mit Spannungsfolger.

![Spannungsfolger zwischen einer Quelle mit Innenwiderstand Ri und dem Lastwiderstand RL](fig:verstaerker-grundschaltungen-folger-last)

**d)** Der Sensor wird direkt an den Eingang des Verstärkers aus a) angeschlossen. Welche
Ausgangsspannung ergibt sich?

**e)** Begründen Sie, warum der Eingangswiderstand des nichtinvertierenden Verstärkers ideal
unendlich groß ist.

::: hint
$U_n = U_e$ und der Teiler aus $R_2$ und $R_1$ ist unbelastet.
:::

::: hint
Ohne Folger bilden $R_i$ und $R_L$ einen Spannungsteiler; mit Folger fließt kein Strom aus
dem Sensor.
:::

::: solution
**a)** $V = 1 + R_2/R_1 \Rightarrow R_2 = (V - 1) \cdot R_1 = 6.5 \cdot 2.7\,\mathrm{k\Omega} = 17.55\,\mathrm{k\Omega}$

**b)** $U_a = 7.5 \cdot 0.65\,\mathrm{V} = 4.875\,\mathrm{V}$, innerhalb von $\pm 12\,\mathrm{V}$.

**c)** Ohne Folger:

$$
U_L = U_0 \cdot \frac{R_L}{R_i + R_L} = 1.1\,\mathrm{V} \cdot \frac{5.6\,\mathrm{k\Omega}}{87.6\,\mathrm{k\Omega}} \approx 0.0703\,\mathrm{V}
$$

Mit Folger fließt kein Strom in den nichtinvertierenden Eingang, an $R_i$ fällt nichts ab,
und wegen $V = 1$ ist $U_L = U_0 = 1.1\,\mathrm{V}$.

**d)** Auch hier fließt kein Eingangsstrom, also $U_e = U_0$ und
$U_a = 7.5 \cdot 1.1\,\mathrm{V} = 8.25\,\mathrm{V}$ (unter $12\,\mathrm{V}$, also linear).

**e)** Die Quelle ist nur mit dem nichtinvertierenden Eingang verbunden. Beim idealen OPV
fließt in ihn kein Strom ($I_p = 0$), also ist $R_\mathrm{ein} = U_e/I_e \to \infty$. Der
Spannungsteiler $R_2$, $R_1$ hängt am Ausgang, nicht an der Quelle.
:::
