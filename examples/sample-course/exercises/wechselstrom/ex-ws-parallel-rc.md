---
id: ex-ws-parallel-rc
title: Parallelschaltung aus R und C
topic: wechselstrom
difficulty: 3
kind: compute
minutes: 15
answers:
  - {key: Y, label: 'Betrag $|\underline{Y}|$ der Admittanz', value: 1.1810, unit: mS, rtol: 5.0e-3}
  - {key: Z, label: 'Betrag $|\underline{Z}|$ der Impedanz', value: 846.73, unit: Ω, rtol: 5.0e-3}
  - {key: phi, label: 'Winkel $\varphi$ der Impedanz', value: -32.14, unit: °, atol: 0.5}
  - {key: Rs, label: 'Widerstand $R_\mathrm{s}$ der Ersatz-Reihenschaltung', value: 716.96, unit: Ω, rtol: 5.0e-3}
  - {key: Cs, label: 'Kapazität $C_\mathrm{s}$ der Ersatz-Reihenschaltung', value: 353.30, unit: nF, rtol: 5.0e-3}
---

Ein Widerstand $R = 1\,\mathrm{k\Omega}$ liegt parallel zu einem Kondensator
$C = 100\,\mathrm{nF}$. Die Schaltung wird bei $f = 1\,\mathrm{kHz}$ betrieben.

**a)** Berechnen Sie die Admittanz $\underline{Y}$ und ihren Betrag.

**b)** Berechnen Sie Betrag und Winkel der Impedanz $\underline{Z}$.

**c)** Bei dieser einen Frequenz lässt sich die Schaltung durch eine Reihenschaltung aus
$R_\mathrm{s}$ und $C_\mathrm{s}$ ersetzen. Bestimmen Sie beide Werte.

::: hint
Parallel addieren sich die Admittanzen: $\underline{Y} = 1/R + \mathrm{j}\omega C$.
:::

::: hint
Für $\underline{Z} = 1/\underline{Y}$ wird der Betrag invertiert und der Winkel negiert.
:::

::: hint
Vergleichen Sie Real- und Imaginärteil von $\underline{Z}$ mit
$R_\mathrm{s} - \mathrm{j}/(\omega C_\mathrm{s})$.
:::

::: solution
**a)** $\underline{Y} = \frac{1}{R} + \mathrm{j}\omega C = (1 + \mathrm{j}\,0{,}628)\,\mathrm{mS}$ mit
$|\underline{Y}| = \sqrt{1^2 + 0{,}628^2}\,\mathrm{mS} \approx 1{,}181\,\mathrm{mS}$.

**b)** $|\underline{Z}| = \frac{1}{|\underline{Y}|} \approx 846{,}7\,\Omega$ und
$\varphi = -\arctan(\omega RC) = -\arctan 0{,}628 \approx -32{,}1^\circ$.

**c)** In algebraischer Form ist

$$
\underline{Z} = |\underline{Z}| \cos\varphi + \mathrm{j}\,|\underline{Z}| \sin\varphi \approx (717{,}0 - \mathrm{j}\,450{,}5)\,\Omega
$$

Also $R_\mathrm{s} \approx 717\,\Omega$ und aus $1/(\omega C_\mathrm{s}) = 450{,}5\,\Omega$
folgt $C_\mathrm{s} = \frac{1}{2\pi \cdot 1\,\mathrm{kHz} \cdot 450{,}5\,\Omega} \approx 353\,\mathrm{nF}$.
Die Ersatzwerte gelten nur bei $1\,\mathrm{kHz}$.
:::
