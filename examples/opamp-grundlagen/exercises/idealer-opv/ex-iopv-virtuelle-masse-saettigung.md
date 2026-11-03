---
id: ex-iopv-virtuelle-masse-saettigung
title: Virtuelle Masse und ihre Grenze
topic: idealer-opv
difficulty: 2
kind: concept
minutes: 14
source: {doc: altes-uebungsblatt02-scan, page: 1, relation: adapted}
answers:
  - {key: Ua1, label: 'Ausgangsspannung $U_a$ bei $U_e = 0.5\,\mathrm{V}$', value: -7.3333, unit: V, rtol: 5.0e-3}
  - {key: Uemax, label: 'Größte Eingangsspannung $|U_e|_\mathrm{max}$ ohne Sättigung', value: 0.81818, unit: V, rtol: 5.0e-3}
  - {key: Ua2, label: 'Ausgangsspannung $U_a$ bei $U_e = 1\,\mathrm{V}$', value: -12, unit: V, rtol: 5.0e-3}
  - {key: Un, label: 'Spannung $U_n$ am invertierenden Eingang bei $U_e = 1\,\mathrm{V}$', value: 0.17021, unit: V, rtol: 5.0e-3}
---

Ein invertierender Verstärker mit einem idealen OPV ist mit $R_1 = 15\,\mathrm{k\Omega}$
und $R_2 = 220\,\mathrm{k\Omega}$ aufgebaut. Der Ausgang ist auf $\pm 12\,\mathrm{V}$
begrenzt ($U_\mathrm{sat} = 12\,\mathrm{V}$).

![Invertierender Verstärker mit R1 = 15 kΩ im Eingang und R2 = 220 kΩ in der Rückführung](fig:idealer-opv-invertierer-15k-220k)

**a)** Erklären Sie, warum der invertierende Eingang auf $0\,\mathrm{V}$ liegt, obwohl er
nicht mit Masse verbunden ist. Welche Voraussetzungen müssen dafür gelten?

**b)** Berechnen Sie $U_a$ für $U_e = 0.5\,\mathrm{V}$.

**c)** Bis zu welchem Betrag der Eingangsspannung arbeitet die Schaltung linear?

**d)** Jetzt ist $U_e = 1\,\mathrm{V}$. Welche Ausgangsspannung stellt sich ein?

**e)** Welche Spannung $U_n$ liegt in d) am invertierenden Eingang? Was folgt daraus für
die virtuelle Masse?

::: hint
Die virtuelle Masse folgt aus der Regel $U_p = U_n$; überlegen Sie, wodurch diese Regel
zustande kommt und wann sie gilt.
:::

::: hint
In der Sättigung ist $U_a$ fest. Weil weiterhin kein Strom in den Eingang fließt, fließt
durch $R_1$ und $R_2$ derselbe Strom.
:::

::: hint
Der Strom durch die Reihenschaltung aus $R_1$ und $R_2$ ist $(U_e - U_a)/(R_1 + R_2)$.
:::

::: solution
**a)** Der Ausgang ist über $R_2$ auf den invertierenden Eingang zurückgeführt
(Gegenkopplung). Weil $U_a = V_0 U_d$ endlich bleibt und $V_0 \to \infty$ geht, muss
$U_d = U_a/V_0 \to 0$ sein, also $U_n = U_p$. Da $U_p$ auf Masse liegt, ist $U_n = 0$:
virtuelle Masse. Voraussetzungen: Gegenkopplung und linearer Betrieb, also
$|U_a| < U_\mathrm{sat}$.

**b)** Knotenregel an der virtuellen Masse, $U_e/R_1 + U_a/R_2 = 0$:

$$
U_a = -\frac{R_2}{R_1} U_e = -\frac{220\,\mathrm{k\Omega}}{15\,\mathrm{k\Omega}} \cdot 0.5\,\mathrm{V} \approx -14.67 \cdot 0.5\,\mathrm{V} \approx -7.33\,\mathrm{V}
$$

Wegen $7.33\,\mathrm{V} < 12\,\mathrm{V}$ ist die Schaltung linear.

**c)** Aus $|U_a| = \frac{R_2}{R_1} |U_e| < U_\mathrm{sat}$:

$$
|U_e|_\mathrm{max} = U_\mathrm{sat} \cdot \frac{R_1}{R_2} = 12\,\mathrm{V} \cdot \frac{15}{220} \approx 0.818\,\mathrm{V}
$$

**d)** Rechnerisch ergäbe sich $U_a = -14.67\,\mathrm{V}$. Das liegt außerhalb des
Aussteuerbereichs, der Ausgang ist in der negativen Sättigung: $U_a = -12\,\mathrm{V}$.

**e)** Der Eingang nimmt keinen Strom auf, also fließt durch $R_1$ und $R_2$ derselbe
Strom:

$$
I = \frac{U_e - U_a}{R_1 + R_2} = \frac{1\,\mathrm{V} + 12\,\mathrm{V}}{235\,\mathrm{k\Omega}} \approx 55.3\,\mathrm{\mu A}
$$

$$
U_n = U_e - I R_1 = 1\,\mathrm{V} - 55.3\,\mathrm{\mu A} \cdot 15\,\mathrm{k\Omega} \approx 0.170\,\mathrm{V}
$$

Der invertierende Eingang liegt nicht mehr auf $0\,\mathrm{V}$: In der Sättigung wirkt die
Gegenkopplung nicht, $U_d = -0.170\,\mathrm{V} \ne 0$, und die virtuelle Masse gilt nicht
mehr.
:::
