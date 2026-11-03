---
id: ex-vg-impedanzwandler-sensor
title: Hochohmiger Sensor mit und ohne Spannungsfolger
topic: verstaerker-grundschaltungen
difficulty: 2
kind: compute
minutes: 10
source: {doc: altes-uebungsblatt02-scan, page: 1, relation: adapted}
answers:
  - {key: UL, label: 'Lastspannung $U_L$ ohne Spannungsfolger', value: 0.041655, unit: V, rtol: 5.0e-3}
  - {key: anteil, label: 'Anteil von $U_L$ an $U_0$ ohne Spannungsfolger', value: 4.6283, unit: '%', rtol: 5.0e-3}
  - {key: IL, label: 'Laststrom mit Spannungsfolger', value: 272.73, unit: µA, rtol: 5.0e-3}
---

Ein Sensor verhält sich wie eine Spannungsquelle mit $U_0 = 0.9\,\mathrm{V}$ und
Innenwiderstand $R_i = 68\,\mathrm{k\Omega}$. Er soll einen Lastwiderstand
$R_L = 3.3\,\mathrm{k\Omega}$ speisen.

![Spannungsfolger zwischen einer Quelle mit Innenwiderstand Ri und dem Lastwiderstand RL](fig:verstaerker-grundschaltungen-folger-last)

**a)** Welche Spannung $U_L$ liegt an der Last, wenn der Sensor direkt angeschlossen wird?

**b)** Wie viel Prozent von $U_0$ sind das?

**c)** Nun wird ein idealer Spannungsfolger dazwischengeschaltet (Bild). Welche Spannung
liegt jetzt an der Last, und welchen Strom liefert der OPV-Ausgang in die Last?

::: hint
Ohne Folger bilden $R_i$ und $R_L$ einen unbelasteten Spannungsteiler.
:::

::: hint
Mit Folger fließt kein Strom in den nichtinvertierenden Eingang; an $R_i$ fällt also keine
Spannung ab.
:::

::: solution
**a)** Spannungsteiler aus $R_i$ und $R_L$:

$$
U_L = U_0 \cdot \frac{R_L}{R_i + R_L} = 0.9\,\mathrm{V} \cdot \frac{3.3\,\mathrm{k\Omega}}{71.3\,\mathrm{k\Omega}} \approx 0.04166\,\mathrm{V}
$$

**b)** $U_L/U_0 = 3.3/71.3 \approx 4.63\,\%$: Fast die ganze Spannung fällt am
Innenwiderstand ab.

**c)** Wegen $I_p = 0$ ist $U_p = U_0$, und mit $V = 1$ liegt $U_L = U_0 = 0.9\,\mathrm{V}$ an der
Last. Den Laststrom $U_L/R_L = 0.9\,\mathrm{V}/3.3\,\mathrm{k\Omega} \approx 272.7\,\mathrm{\mu A}$
liefert der OPV aus seiner Versorgung, nicht der Sensor.
:::
