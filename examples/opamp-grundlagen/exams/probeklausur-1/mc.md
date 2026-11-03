---
title: Probeklausur 1, MC-Teil
---

:::: {.mcq #mc-idealer-opv-101 type="single" difficulty="1"}
Ein idealer OPV arbeitet mit Gegenkopplung im linearen Bereich. Was gilt für die
Differenzspannung $U_d$ und die Eingangsströme?

- [ ] $U_d$ ist gleich $U_a$, die Eingangsströme sind null.

  Ausgang und Eingang verwechselt: $U_a = V_0 U_d$, nicht $U_d = U_a$.

- [ ] $U_d$ ist null, die Eingänge sind leitend verbunden.

  Virtueller Kurzschluss als echter Kurzschluss verstanden: Zwischen den Eingängen fließt
  kein Strom.

- [x] $U_d$ ist null, die Eingangsströme sind null.

  $U_d = U_a/V_0 \to 0$ bei endlichem $U_a$, und der ideale OPV nimmt keinen Strom auf.

- [ ] $U_d$ ist gleich $U_\mathrm{sat}/V_0$, die Eingangsströme sind null.

  Das ist die Aussteuergrenze ohne Rückkopplung, nicht der Wert im gegengekoppelten Betrieb.

::: explanation
Mit Gegenkopplung stellt der OPV seinen Ausgang so ein, dass $U_d = U_a/V_0$ wegen
$V_0 \to \infty$ verschwindet (virtueller Kurzschluss). Die Eingänge sind dabei
hochohmig; es fließt kein Strom hinein oder zwischen ihnen.
:::
::::

:::: {.mcq #mc-verstaerker-grundschaltungen-101 type="multi" difficulty="2"}
Ein invertierender Verstärker mit idealem OPV hat $R_1 = 4.7\,\mathrm{k\Omega}$ und
$R_2 = 47\,\mathrm{k\Omega}$ und arbeitet linear. Welche Aussagen gelten?

- [x] Die Spannungsverstärkung ist $V = -10$.

  $V = -R_2/R_1 = -47\,\mathrm{k\Omega}/4.7\,\mathrm{k\Omega}$.

- [x] Die Signalquelle sieht den Eingangswiderstand $4.7\,\mathrm{k\Omega}$.

  $R_1$ führt auf die virtuelle Masse, also ist $R_\mathrm{ein} = R_1$.

- [ ] Ausgangs- und Eingangsspannung sind gleichphasig.

  Vorzeichen übersehen: Die negative Verstärkung dreht die Phase um $180^\circ$.

- [ ] Am invertierenden Eingang liegt die Spannung $U_e$.

  Das gilt für den nichtinvertierenden Verstärker; hier liegt dort die virtuelle Masse.

::: explanation
Die virtuelle Masse am invertierenden Eingang ergibt $V = -R_2/R_1 = -10$ und den
Eingangswiderstand $R_1$. Das Minuszeichen bedeutet Gegenphase.
:::
::::

:::: {.mcq #mc-verstaerker-grundschaltungen-102 type="single" difficulty="1"}
An einem idealen Spannungsfolger liegt $U_e = 2.4\,\mathrm{V}$. Wie groß ist $U_a$?

- [x] $2.4\,\mathrm{V}$

  Der Spannungsfolger hat $V = 1$.

- [ ] $-2.4\,\mathrm{V}$

  Mit dem invertierenden Verstärker verwechselt.

- [ ] $0\,\mathrm{V}$

  Virtuelle Masse angenommen; hier liegt $U_e$ am nichtinvertierenden Eingang.

- [ ] $1.2\,\mathrm{V}$

  Einen Spannungsteiler $1:1$ angenommen; der Folger hat keinen Teiler.

::: explanation
Der Ausgang ist direkt auf den invertierenden Eingang zurückgeführt:
$U_a = U_n = U_p = U_e$.
:::
::::

:::: {.mcq #mc-verstaerker-grundschaltungen-103 type="single" difficulty="2"}
Ein Summierer hat $R_F = 20\,\mathrm{k\Omega}$, $R_1 = 10\,\mathrm{k\Omega}$ und
$R_2 = 40\,\mathrm{k\Omega}$; an den Eingängen liegen $U_1 = 0.5\,\mathrm{V}$ und
$U_2 = 1.2\,\mathrm{V}$. Wie groß ist $U_a$?

- [ ] $-1.7\,\mathrm{V}$

  Gewichte $R_F/R_i$ vergessen: einfach $U_1 + U_2$ summiert.

- [x] $-1.6\,\mathrm{V}$

  $U_a = -(2 \cdot 0.5\,\mathrm{V} + 0.5 \cdot 1.2\,\mathrm{V})$.

- [ ] $1.6\,\mathrm{V}$

  Das Minuszeichen des invertierenden Summierers fehlt.

- [ ] $-2.65\,\mathrm{V}$

  Gewichte umgekehrt: $R_i/R_F$ statt $R_F/R_i$.

::: explanation
Jeder Eingang speist über $R_i$ die virtuelle Masse; die Ströme fließen gemeinsam durch
$R_F$: $U_a = -R_F (U_1/R_1 + U_2/R_2) = -(1.0\,\mathrm{V} + 0.6\,\mathrm{V})$.
:::
::::

:::: {.mcq #mc-verstaerker-grundschaltungen-104 type="single" difficulty="1"}
Ein nichtinvertierender Verstärker hat $R_1 = 2\,\mathrm{k\Omega}$ nach Masse und
$R_2 = 10\,\mathrm{k\Omega}$ in der Rückführung. Wie groß ist $V$?

- [ ] $5$

  Die $1$ in $1 + R_2/R_1$ vergessen.

- [ ] $-5$

  Formel des invertierenden Verstärkers verwendet.

- [ ] $0.1667$

  Rückkopplungsfaktor $k = R_1/(R_1 + R_2)$ statt $1/k$.

- [x] $6$

  $V = 1 + R_2/R_1 = 1 + 5$.

::: explanation
Der Teiler aus $R_2$ und $R_1$ führt den Anteil $k = R_1/(R_1 + R_2)$ der
Ausgangsspannung zurück; die Verstärkung ist $V = 1/k = 1 + R_2/R_1$.
:::
::::

:::: {.mcq #mc-integrierer-101 type="single" difficulty="2"}
Ein Integrierer hat $R = 10\,\mathrm{k\Omega}$ und $C = 100\,\mathrm{nF}$. Wie groß ist
$|\underline{H}|$ bei $f = 1\,\mathrm{kHz}$?

- [ ] $6.283$

  $\omega RC$ statt $1/(\omega RC)$ gerechnet.

- [x] $0.1592$

  $|\underline{H}| = 1/(2\pi f RC)$ mit $RC = 1\,\mathrm{ms}$.

- [ ] $1.592$

  Zehnerpotenz falsch: mit $f = 100\,\mathrm{Hz}$ gerechnet.

- [ ] $0.1125$

  Zusätzlich durch $\sqrt{2}$ geteilt, als wäre es ein Effektivwert.

::: explanation
Der Integrierer hat $|\underline{H}| = 1/(\omega RC)$. Mit
$\omega RC = 2\pi \cdot 1\,\mathrm{kHz} \cdot 1\,\mathrm{ms} \approx 6.283$ ist
$|\underline{H}| \approx 0.159$; die Frequenz liegt also über $f_1 \approx 159\,\mathrm{Hz}$.
:::
::::
