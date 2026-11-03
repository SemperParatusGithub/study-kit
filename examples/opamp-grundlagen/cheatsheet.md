---
title: Formelblatt Operationsverstärker-Grundschaltungen
max_pages: 2
priority: [verstaerker-grundschaltungen, integrierer, idealer-opv]
---

## Idealer Operationsverstärker und Gegenkopplung

$$
U_a = V_0 \cdot (U_p - U_n) = V_0 \cdot U_d
\qquad
|U_d|_\mathrm{max} = \frac{U_\mathrm{sat}}{V_0}
$$

Ideal: $V_0 \to \infty$, $R_\mathrm{ein} \to \infty$, $R_a \to 0$. Ohne Rückkopplung ist der
Ausgang fast immer in der Sättigung.

$$
k = \frac{R_1}{R_1 + R_2}
\qquad
V = \frac{U_a}{U_e} = \frac{V_0}{1 + k V_0} \quad\to\quad \frac{1}{k} \quad \text{für } k V_0 \gg 1
\qquad
F = \frac{1/k - V}{1/k} = \frac{1}{1 + k V_0}
$$

::: definition
**Regeln mit Gegenkopplung (linearer Betrieb)**

$$
I_p = I_n = 0, \qquad U_p = U_n
$$

Liegt $U_p$ auf Masse, ist der invertierende Eingang virtuelle Masse: $U_n = 0$, aber kein
Strom fließt dort nach Masse.
:::

::: warning
In der Sättigung gelten die Regeln nicht: $U_n \ne U_p$, der Strom durch $R_1$ und $R_2$
folgt aus dem Spannungsteiler zwischen $U_e$ und $U_a$.
:::

## Invertierender und nichtinvertierender Verstärker, Spannungsfolger und Summierer

Vorgehen: Knotengleichung am invertierenden Eingang, auflösen, Zahlen einsetzen, mit
$\pm U_\mathrm{sat}$ vergleichen.

| Schaltung | Übertragung | Eingangswiderstand |
|---|---|---|
| Invertierender Verstärker | $U_a = -\frac{R_2}{R_1} \cdot U_e$ | $R_1$ |
| Nichtinvertierender Verstärker | $U_a = \left(1 + \frac{R_2}{R_1}\right) \cdot U_e$ | $\to \infty$ |
| Spannungsfolger | $U_a = U_e$ | $\to \infty$ |
| Summierer | $U_a = -R_F \sum_i \frac{U_i}{R_i}$ | $R_i$ je Eingang |

$$
\frac{U_e - 0}{R_1} + \frac{U_a - 0}{R_2} = 0 \quad\Rightarrow\quad V = \frac{U_a}{U_e} = -\frac{R_2}{R_1}
\qquad
R_2 = (V - 1) \cdot R_1
$$

Quelle mit Innenwiderstand $R_i$ am invertierenden Verstärker ($R_i$ in Reihe zu $R_1$):

$$
\frac{U_a}{U_0} = -\frac{R_2}{R_1 + R_i}
$$

Summierer ($k$ Eingänge an der virtuellen Masse):

$$
U_a = -R_F \cdot \left( \frac{U_1}{R_1} + \frac{U_2}{R_2} + \ldots + \frac{U_k}{R_k} \right)
$$

Sättigung: linear bis

$$
|U_e|_\mathrm{max} = \frac{U_\mathrm{sat}}{|V|}
$$

darüber bleibt $U_a = \pm U_\mathrm{sat}$ mit dem Vorzeichen von $V \cdot U_e$.

Impedanzwandler (Quelle $U_0$, $R_i$, Last $R_L$):

$$
U_L = U_0 \cdot \frac{R_L}{R_i + R_L} \quad \text{(direkt)}, \qquad U_L = U_0 \quad \text{(mit Folger)}
$$

::: warning
Summierer: jeder Eingang hat sein Gewicht $-R_F/R_i$; $-(U_1 + U_2)$ nur für
$R_i = R_F$. Vorzeichen negativer Eingänge mitnehmen.
:::

## Integrierer

$$
C \cdot \frac{\mathrm{d}U_a}{\mathrm{d}t} = -\frac{U_e}{R} \quad\Rightarrow\quad U_a(t) = -\frac{1}{RC} \int_0^t U_e(\tau)\,\mathrm{d}\tau + U_a(0)
$$

Konstantes $U_e$ (Rampe) und stückweise konstantes $U_e$:

$$
U_a(t) = -\frac{U_e}{RC} \cdot t + U_a(0), \qquad \frac{\mathrm{d}U_a}{\mathrm{d}t} = -\frac{U_e}{RC}
\qquad
U_a(t) = U_a(t_k) - \frac{U_{e,k}}{RC} \cdot (t - t_k) \quad \text{für } t_k \le t < t_{k+1}
$$

Zeit bis zur Sättigung ($+$: $U_a(0)$ hat das Vorzeichen von $U_e$):

$$
t_\mathrm{sat} = \frac{U_\mathrm{sat} \pm U_a(0)}{|U_e|} \cdot RC
$$

Frequenzgang ($+90^\circ$ bei allen Frequenzen, $-20\,\mathrm{dB}$ pro Dekade):

$$
\underline{H}(j\omega) = \frac{\underline{U}_a}{\underline{U}_e} = -\frac{1}{j\omega RC} = \frac{j}{\omega RC}, \qquad |\underline{H}| = \frac{1}{\omega RC} = \frac{1}{2\pi f RC}
\qquad
f_1 = \frac{1}{2\pi RC}
\qquad
\hat{U}_a = |\underline{H}| \cdot \hat{U}_e = \frac{\hat{U}_e}{\omega RC}
$$

::: warning
Die Rampe endet bei $U_\mathrm{sat}$, nicht bei $U_B$. Positives $U_e$ ergibt eine fallende
Rampe. $f_1$ ist keine Grenzfrequenz eines Tiefpasses: $|\underline{H}(f_1)| = 1$.
:::
