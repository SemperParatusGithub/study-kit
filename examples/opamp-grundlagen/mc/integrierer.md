---
topic: integrierer
title: Integrierer
---

:::: {.mcq #mc-integrierer-001 type="single" difficulty="1"}
An einem idealen Integrierer mit entladenem Kondensator liegt ab $t = 0$ eine konstante,
positive Eingangsspannung $U_e$. Wie verläuft die Ausgangsspannung $U_a(t)$?

- [ ] Sie steigt linear an, bis $+U_\mathrm{sat}$ erreicht ist.

  Das Minuszeichen der invertierenden Schaltung ist vergessen.

- [x] Sie fällt linear ab, bis $-U_\mathrm{sat}$ erreicht ist.

  $U_a(t) = -U_e \cdot t/(RC)$ ist eine fallende Rampe, die an der Sättigung endet.

- [ ] Sie springt auf einen festen negativen Wert und bleibt dort.

  Das wäre ein invertierender Verstärker mit Widerstand statt Kondensator.

- [ ] Sie nähert sich exponentiell einem negativen Endwert.

  Ladekurve eines RC-Glieds angenommen; hier lädt ein konstanter Strom den Kondensator.

::: explanation
Wegen der virtuellen Masse fließt der konstante Strom $U_e/R$ in den Kondensator. Ein
konstanter Strom lädt ihn gleichmäßig, also ändert sich $U_a$ linear, und zwar wegen der
Inversion nach unten, bis der Ausgang bei $-U_\mathrm{sat}$ ansteht.
:::
::::

:::: {.mcq #mc-integrierer-002 type="single" difficulty="1"}
Ein Integrierer hat $R = 22\,\mathrm{k\Omega}$ und $C = 47\,\mathrm{nF}$. Bei welcher
Frequenz $f_1$ ist $|\underline{H}(j\omega)| = 1$?

- [ ] $15.39\,\mathrm{Hz}$

  Zehnerpotenz falsch: mit $C = 470\,\mathrm{nF}$ gerechnet.

- [x] $153.9\,\mathrm{Hz}$

  $f_1 = 1/(2\pi RC)$ mit $RC = 1.034\,\mathrm{ms}$.

- [ ] $967.1\,\mathrm{Hz}$

  Das ist $1/(RC)$, also $\omega_1$ in $\mathrm{s^{-1}}$: Faktor $2\pi$ vergessen.

- [ ] $1539\,\mathrm{Hz}$

  Zehnerpotenz falsch: mit $C = 4.7\,\mathrm{nF}$ gerechnet.

::: explanation
Aus $|\underline{H}| = 1/(\omega RC) = 1$ folgt $\omega_1 = 1/(RC)$ und
$f_1 = 1/(2\pi RC)$. Mit $RC = 22\,\mathrm{k\Omega} \cdot 47\,\mathrm{nF} = 1.034\,\mathrm{ms}$
ergibt das $f_1 \approx 153.9\,\mathrm{Hz}$.
:::
::::

:::: {.mcq #mc-integrierer-003 type="single" difficulty="2"}
Ein Integrierer mit $R = 10\,\mathrm{k\Omega}$ und $C = 47\,\mathrm{nF}$ erhält ab
$t = 0$ die konstante Eingangsspannung $U_e = 0.2\,\mathrm{V}$. Mit welcher Steigung
ändert sich $U_a$, solange der Ausgang nicht in der Sättigung ist?

- [ ] $+425.5\,\mathrm{V/s}$

  Vorzeichen falsch: Die Inversion des Integrierers ist vergessen.

- [ ] $-42.55\,\mathrm{V/s}$

  Zehnerpotenz falsch: mit $C = 470\,\mathrm{nF}$ gerechnet.

- [x] $-425.5\,\mathrm{V/s}$

  $\mathrm{d}U_a/\mathrm{d}t = -U_e/(RC)$ mit $RC = 0.47\,\mathrm{ms}$.

- [ ] $-2674\,\mathrm{V/s}$

  Mit $2\pi$ multipliziert, als ginge es um eine Kreisfrequenz.

::: explanation
Der Strom $U_e/R = 20\,\mathrm{\mu A}$ lädt den Kondensator. Daraus folgt
$\mathrm{d}U_a/\mathrm{d}t = -U_e/(RC) = -0.2\,\mathrm{V}/0.47\,\mathrm{ms} \approx -425.5\,\mathrm{V/s}$;
das Minus kommt von der invertierenden Schaltung.
:::
::::

:::: {.mcq #mc-integrierer-004 type="single" difficulty="2"}
Ein Integrierer mit $RC = 2\,\mathrm{ms}$ und entladenem Kondensator erhält ab $t = 0$
die Eingangsspannung $U_e = 0.5\,\mathrm{V}$. Der OPV wird mit $\pm 12\,\mathrm{V}$
versorgt, sein Ausgang sättigt bei $\pm 10\,\mathrm{V}$. Nach welcher Zeit ist der
Ausgang in der Sättigung?

- [ ] $48\,\mathrm{ms}$

  Mit der Versorgungsspannung $U_B$ statt mit $U_\mathrm{sat}$ gerechnet.

- [ ] $0.1\,\mathrm{ms}$

  Formel umgedreht: $U_e \cdot RC/U_\mathrm{sat}$ statt $U_\mathrm{sat} \cdot RC/U_e$.

- [ ] $80\,\mathrm{ms}$

  Den Hub von $-U_\mathrm{sat}$ bis $+U_\mathrm{sat}$ angesetzt; die Rampe beginnt aber bei null.

- [x] $40\,\mathrm{ms}$

  $t_\mathrm{sat} = U_\mathrm{sat} \cdot RC/U_e$.

::: explanation
Die Rampe fällt mit $U_e/(RC) = 250\,\mathrm{V/s}$ von null aus. Die Grenze
$-10\,\mathrm{V}$ ist nach $10\,\mathrm{V}/(250\,\mathrm{V/s}) = 40\,\mathrm{ms}$
erreicht.
:::
::::

:::: {.mcq #mc-integrierer-005 type="single" difficulty="2"}
Um wie viel dB liegt der Betrag des Frequenzgangs eines idealen Integrierers bei
$f = 10 \cdot f_1$?

- [x] $-20\,\mathrm{dB}$

  Der Betrag $f_1/f$ ist eine Dekade über $f_1$ gleich 0.1.

- [ ] $-40\,\mathrm{dB}$

  Steigung eines Systems zweiter Ordnung angenommen.

- [ ] $-10\,\mathrm{dB}$

  Mit $10 \lg$ statt $20 \lg$ für ein Spannungsverhältnis gerechnet.

- [ ] $-3\,\mathrm{dB}$

  Den Wert des RC-Tiefpasses an seiner Grenzfrequenz übernommen.

::: explanation
Beim Integrierer ist $|\underline{H}| = 1/(\omega RC) = f_1/f$. Bei $f = 10 \cdot f_1$
ist der Betrag 0.1, und $20 \lg 0.1 = -20\,\mathrm{dB}$: Er fällt mit
$20\,\mathrm{dB}$ pro Dekade.
:::
::::

:::: {.mcq #mc-integrierer-006 type="single" difficulty="3"}
Welchen Phasenwinkel hat der Frequenzgang $\underline{H}(j\omega) = -1/(j\omega RC)$ des
invertierenden Integrierers?

- [ ] $-90^\circ$ bei allen Frequenzen

  Das Minuszeichen der Inversion ist vergessen; so verhielte sich $1/(j\omega RC)$.

- [ ] $180^\circ$ bei allen Frequenzen

  Nur die Inversion berücksichtigt, die Phase des Kondensators vergessen.

- [x] $+90^\circ$ bei allen Frequenzen

  $-1/j = +j$, also ist $\underline{H}$ positiv imaginär.

- [ ] $-45^\circ$ bei der Frequenz $f_1$

  Die Phase des RC-Tiefpasses an seiner Grenzfrequenz übernommen.

::: explanation
Mit $1/j = -j$ wird $\underline{H} = j/(\omega RC)$, eine positive imaginäre Zahl. Ihr
Winkel ist $+90^\circ$, unabhängig von der Frequenz: Die Ausgangsspannung eilt der
Eingangsspannung um $90^\circ$ vor.
:::
::::

:::: {.mcq #mc-integrierer-007 type="single" difficulty="3"}
An einem Integrierer mit $R = 10\,\mathrm{k\Omega}$ und $C = 1\,\mathrm{\mu F}$ liegt
eine Sinusspannung mit der Amplitude $\hat{U}_e = 1\,\mathrm{V}$ und
$f = 50\,\mathrm{Hz}$. Wie groß ist die Amplitude $\hat{U}_a$ am Ausgang?

- [x] $0.3183\,\mathrm{V}$

  $\hat{U}_a = \hat{U}_e/(2\pi f RC)$ mit $RC = 10\,\mathrm{ms}$.

- [ ] $3.142\,\mathrm{V}$

  Mit $2\pi f RC$ multipliziert statt dividiert.

- [ ] $0.2251\,\mathrm{V}$

  Den Effektivwert statt der Amplitude angegeben.

- [ ] $2.000\,\mathrm{V}$

  Den Faktor $2\pi$ vergessen: $f$ statt $\omega$ eingesetzt.

::: explanation
Die Amplitude am Ausgang ist $|\underline{H}| \cdot \hat{U}_e$ mit
$|\underline{H}| = 1/(2\pi f RC)$. Mit $2\pi \cdot 50\,\mathrm{Hz} \cdot 10\,\mathrm{ms} = \pi$
ergibt das $1\,\mathrm{V}/\pi \approx 0.3183\,\mathrm{V}$.
:::
::::

:::: {.mcq #mc-integrierer-008 type="single" difficulty="2"}
Warum legt man in der Praxis einen großen Widerstand parallel zum Kondensator eines
Integrierers?

- [ ] Er erhöht die Frequenz $f_1$ des Integrierers.

  $f_1 = 1/(2\pi RC)$ hängt nur vom Eingangswiderstand $R$ und von $C$ ab.

- [x] Er begrenzt die Gleichspannungsverstärkung.

  So kann eine kleine Offsetspannung den Ausgang nicht in die Sättigung treiben.

- [ ] Er entlädt den Kondensator bei jedem Nulldurchgang.

  Ein Parallelwiderstand entlädt kontinuierlich und langsam, nicht schlagartig.

- [ ] Er begrenzt den Strom in den Kondensator.

  Der Strom ist durch $U_e/R$ am Eingang festgelegt, nicht durch den Parallelwiderstand.

::: explanation
Der ideale Integrierer verstärkt Gleichspannung unbegrenzt ($|\underline{H}| \to \infty$
für $f \to 0$). Schon eine kleine Offsetspannung wird deshalb aufintegriert. Ein
Widerstand parallel zu $C$ macht daraus bei Gleichspannung einen invertierenden
Verstärker mit endlicher Verstärkung.
:::
::::

:::: {.mcq #mc-integrierer-009 type="multi" difficulty="1"}
Welche Aussagen gelten für einen idealen Integrierer im linearen Betrieb?

- [x] Der invertierende Eingang liegt auf virtueller Masse.

  Der nichtinvertierende Eingang liegt auf Masse, und bei Gegenkopplung ist $U_d = 0$.

- [ ] Bei konstanter Eingangsspannung ist $U_a$ konstant.

  Das gilt für den Verstärker mit $R_2$; beim Integrierer entsteht eine Rampe.

- [x] Der Strom durch $R$ fließt vollständig in den Kondensator.

  In den OPV-Eingang fließt kein Strom ($I_n = 0$).

- [ ] Die Frequenz $f_1$ hängt von der Amplitude von $U_e$ ab.

  Die Schaltung ist linear; $f_1 = 1/(2\pi RC)$ hängt nur von $R$ und $C$ ab.

- [x] Der Betrag des Frequenzgangs fällt mit $20\,\mathrm{dB}$ pro Dekade.

  $|\underline{H}| = 1/(\omega RC)$ ist umgekehrt proportional zur Frequenz.

::: explanation
Die zwei Regeln des idealen OPV (virtuelle Masse, kein Eingangsstrom) schicken den Strom
$U_e/R$ in den Kondensator. Der Ausgang ist deshalb das Integral der Eingangsspannung,
und der Frequenzgang $-1/(j\omega RC)$ fällt mit $20\,\mathrm{dB}$ pro Dekade,
unabhängig von der Signalamplitude.
:::
::::

:::: {.mcq #mc-integrierer-010 type="multi" difficulty="3"}
Ein Integrierer mit entladenem Kondensator erhält ab $t = 0$ eine konstante
Eingangsspannung $U_e$. Welche Änderungen verdoppeln die Zeit $t_\mathrm{sat}$ bis zur
Sättigung (alles andere bleibt gleich)?

- [x] $R$ verdoppeln

  $t_\mathrm{sat} = U_\mathrm{sat} \cdot RC/|U_e|$ ist proportional zu $R$.

- [ ] $C$ halbieren

  Ein halb so großes $C$ halbiert $RC$ und damit auch $t_\mathrm{sat}$.

- [x] $U_e$ halbieren

  Die Rampe wird halb so steil und braucht doppelt so lange.

- [ ] $U_e$ verdoppeln

  Die Rampe wird doppelt so steil; $t_\mathrm{sat}$ halbiert sich.

- [x] $C$ verdoppeln

  $t_\mathrm{sat}$ ist proportional zu $C$.

::: explanation
Die Rampe hat die Steigung $-U_e/(RC)$ und muss von null bis $\mp U_\mathrm{sat}$ laufen,
also ist $t_\mathrm{sat} = U_\mathrm{sat} \cdot RC/|U_e|$. Doppelt so lang wird sie bei
doppeltem $R$, doppeltem $C$ oder halbem $U_e$.
:::
::::

:::: {.mcq #mc-integrierer-011 type="single" difficulty="3"}
Ein Integrierer mit $RC = 1\,\mathrm{ms}$ und $U_\mathrm{sat} = 10\,\mathrm{V}$ startet
mit $U_a(0) = -2\,\mathrm{V}$. Ab $t = 0$ liegt $U_e = 0.4\,\mathrm{V}$ an. Nach
welcher Zeit ist der Ausgang in der Sättigung?

- [ ] $25\,\mathrm{ms}$

  Den Anfangswert $U_a(0)$ nicht berücksichtigt.

- [ ] $30\,\mathrm{ms}$

  Vorzeichen des Anfangswerts falsch: $12\,\mathrm{V}$ statt $8\,\mathrm{V}$ Hub.

- [x] $20\,\mathrm{ms}$

  Die fallende Rampe braucht von $-2\,\mathrm{V}$ bis $-10\,\mathrm{V}$ nur $8\,\mathrm{V}$.

- [ ] $50\,\mathrm{ms}$

  Den Hub von $+U_\mathrm{sat}$ bis $-U_\mathrm{sat}$ angesetzt.

::: explanation
Die Rampe fällt mit $U_e/(RC) = 400\,\mathrm{V/s}$, weil $U_e$ positiv ist. Sie startet
bei $-2\,\mathrm{V}$ und muss nur noch bis $-10\,\mathrm{V}$, also $8\,\mathrm{V}$:
$8\,\mathrm{V}/(400\,\mathrm{V/s}) = 20\,\mathrm{ms}$.
:::
::::
