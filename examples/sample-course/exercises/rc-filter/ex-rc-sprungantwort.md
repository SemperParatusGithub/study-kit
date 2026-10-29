---
id: ex-rc-sprungantwort
title: Sprungantwort eines RC-Glieds
topic: rc-filter
difficulty: 3
kind: compute
minutes: 15
answers:
  - {key: tau, label: 'Zeitkonstante $\tau$', value: 47, unit: ms, rtol: 5.0e-3}
  - {key: uC, label: 'Spannung $u_C(\tau)$', value: 3.1606, unit: V, rtol: 5.0e-3}
  - {key: t4, label: 'Zeitpunkt, zu dem $u_C = 4\,\mathrm{V}$ ist', value: 75.644, unit: ms, rtol: 5.0e-3}
  - {key: i0, label: 'Ladestrom $i(0)$', value: 0.5, unit: mA, rtol: 5.0e-3}
  - {key: tr, label: 'Anstiegszeit $t_\mathrm{r}$ von $10\,\%$ auf $90\,\%$', value: 103.27, unit: ms, rtol: 5.0e-3}
---

Ein ungeladener Kondensator $C = 4{,}7\,\mathrm{\mu F}$ wird zum Zeitpunkt $t = 0$ über
$R = 10\,\mathrm{k\Omega}$ an die Gleichspannung $U_0 = 5\,\mathrm{V}$ gelegt.

**a)** Berechnen Sie die Zeitkonstante $\tau$.

**b)** Welche Spannung hat der Kondensator nach der Zeit $\tau$?

**c)** Wann erreicht $u_C$ den Wert $4\,\mathrm{V}$?

**d)** Wie groß ist der Ladestrom unmittelbar nach dem Einschalten?

**e)** Berechnen Sie die Anstiegszeit $t_\mathrm{r}$, in der $u_C$ von $10\,\%$ auf
$90\,\%$ des Endwerts steigt.

::: hint
Es gilt $u_C(t) = U_0\,(1 - \mathrm{e}^{-t/\tau})$ mit $\tau = RC$.
:::

::: hint
Nach $t$ aufgelöst: $t = -\tau \ln(1 - u_C/U_0)$.
:::

::: hint
Für die Anstiegszeit bestimmen Sie die beiden Zeitpunkte für $10\,\%$ und $90\,\%$ und
bilden die Differenz; $U_0$ kürzt sich heraus.
:::

::: solution
**a)** $\tau = RC = 10\,\mathrm{k\Omega} \cdot 4{,}7\,\mathrm{\mu F} = 47\,\mathrm{ms}$

**b)** $u_C(\tau) = 5\,\mathrm{V} \cdot (1 - \mathrm{e}^{-1}) \approx 3{,}16\,\mathrm{V}$, also
$63{,}2\,\%$ des Endwerts.

**c)** $t = -\tau \ln\left(1 - \frac{4}{5}\right) = \tau \ln 5 \approx 75{,}6\,\mathrm{ms}$

**d)** Im ersten Augenblick ist der Kondensator spannungslos, die ganze Spannung liegt an
$R$: $i(0) = U_0/R = 0{,}5\,\mathrm{mA}$.

**e)** $t_{10} = -\tau \ln 0{,}9$ und $t_{90} = -\tau \ln 0{,}1$, also

$$
t_\mathrm{r} = t_{90} - t_{10} = \tau \ln\frac{0{,}9}{0{,}1} = \tau \ln 9 \approx 2{,}20\,\tau \approx 103\,\mathrm{ms}
$$

![Normierte Sprungantwort des RC-Glieds mit τ = 47 ms; die Anstiegszeit beträgt 103 ms](fig:rc-sprung-47ms)
:::
