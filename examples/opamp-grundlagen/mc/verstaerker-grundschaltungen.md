---
topic: verstaerker-grundschaltungen
title: 'Invertierender und nichtinvertierender Verstärker, Spannungsfolger und Summierer'
---

:::: {.mcq #mc-verstaerker-grundschaltungen-001 type="single" difficulty="1"}
Ein invertierender Verstärker mit idealem OPV hat $R_1 = 4.7\,\mathrm{k\Omega}$ und
$R_2 = 22\,\mathrm{k\Omega}$. Wie groß ist seine Spannungsverstärkung $V$?

- [ ] $4.681$

  Minuszeichen vergessen: Der invertierende Verstärker dreht das Vorzeichen um.

- [ ] $-0.2136$

  Kehrwert: $-R_1/R_2$ statt $-R_2/R_1$, die Widerstände sind vertauscht.

- [x] $-4.681$

  $V = -R_2/R_1 = -22/4.7$.

- [ ] $5.681$

  Formel des nichtinvertierenden Verstärkers $1 + R_2/R_1$ verwendet.

::: explanation
Die Knotenregel an der virtuellen Masse gibt $U_e/R_1 + U_a/R_2 = 0$, also
$V = -R_2/R_1 = -22\,\mathrm{k\Omega}/4.7\,\mathrm{k\Omega} \approx -4.681$.
:::
::::

:::: {.mcq #mc-verstaerker-grundschaltungen-002 type="single" difficulty="1"}
Ein nichtinvertierender Verstärker hat $R_1 = 1.5\,\mathrm{k\Omega}$ (nach Masse) und
$R_2 = 6.8\,\mathrm{k\Omega}$ (Rückkopplung). Wie groß ist $V$?

- [ ] $4.533$

  Die Eins vergessen: nur $R_2/R_1$ gerechnet.

- [ ] $-4.533$

  Formel des invertierenden Verstärkers verwendet.

- [ ] $0.1807$

  Das ist der Rückkopplungsfaktor $k = R_1/(R_1 + R_2)$, nicht die Verstärkung $1/k$.

- [x] $5.533$

  $V = 1 + R_2/R_1 = 1 + 6.8/1.5$.

::: explanation
Wegen $U_n = U_e$ und des unbelasteten Teilers gilt $U_e = U_a \cdot R_1/(R_1 + R_2)$, also
$V = 1 + R_2/R_1 \approx 5.533$.
:::
::::

:::: {.mcq #mc-verstaerker-grundschaltungen-003 type="single" difficulty="1"}
Welche Kombination aus Spannungsverstärkung und Eingangswiderstand hat ein idealer
Spannungsfolger?

- [ ] $V = 1$ und $R_\mathrm{ein} = 0$

  Verwechselt mit dem Ausgangswiderstand, der beim Folger gegen null geht.

- [x] $V = 1$ und $R_\mathrm{ein} \to \infty$

  Ausgang direkt am invertierenden Eingang, in den nichtinvertierenden fließt kein Strom.

- [ ] $V = -1$ und $R_\mathrm{ein} \to \infty$

  Vorzeichenfehler: Der Folger ist ein nichtinvertierender Verstärker mit $R_2 = 0$.

- [ ] $V = V_0$ und $R_\mathrm{ein} \to \infty$

  Die Leerlaufverstärkung gilt nur ohne Gegenkopplung.

::: explanation
Mit $R_2 = 0$ und $R_1 \to \infty$ wird aus $V = 1 + R_2/R_1$ genau $V = 1$. Die Quelle sieht
nur den nichtinvertierenden Eingang, also $R_\mathrm{ein} \to \infty$; der Ausgangswiderstand
geht gegen null.
:::
::::

:::: {.mcq #mc-verstaerker-grundschaltungen-004 type="single" difficulty="2"}
Ein Summierer hat $R_F = 10\,\mathrm{k\Omega}$, $R_1 = 10\,\mathrm{k\Omega}$ und
$R_2 = 5\,\mathrm{k\Omega}$; an den Eingängen liegen $U_1 = 0.6\,\mathrm{V}$ und
$U_2 = 0.4\,\mathrm{V}$. Wie groß ist $U_a$?

- [ ] $-1.0\,\mathrm{V}$

  Spannungen ohne Gewichte addiert, als wären alle Widerstände gleich.

- [ ] $1.4\,\mathrm{V}$

  Minuszeichen des Summierers vergessen.

- [x] $-1.4\,\mathrm{V}$

  $-R_F \cdot (U_1/R_1 + U_2/R_2) = -(0.6\,\mathrm{V} + 0.8\,\mathrm{V})$.

- [ ] $-0.8\,\mathrm{V}$

  Gewicht von $U_2$ umgedreht: $R_2/R_F$ statt $R_F/R_2$.

::: explanation
Die Ströme in die virtuelle Masse sind $60\,\mathrm{\mu A}$ und $80\,\mathrm{\mu A}$; ihre
Summe $140\,\mathrm{\mu A}$ fließt durch $R_F$ und ergibt
$U_a = -10\,\mathrm{k\Omega} \cdot 140\,\mathrm{\mu A} = -1.4\,\mathrm{V}$.
:::
::::

:::: {.mcq #mc-verstaerker-grundschaltungen-005 type="single" difficulty="1"}
Welchen Eingangswiderstand sieht die Signalquelle an einem invertierenden Verstärker mit
idealem OPV?

- [x] $R_\mathrm{ein} = R_1$

  $R_1$ liegt zwischen Eingang und virtueller Masse.

- [ ] $R_\mathrm{ein} \to \infty$

  Das gilt für den nichtinvertierenden Verstärker, nicht für den invertierenden.

- [ ] $R_\mathrm{ein} = R_2$

  $R_2$ liegt im Rückkopplungszweig, nicht zwischen Quelle und Knoten.

- [ ] $R_\mathrm{ein} = R_1 + R_2$

  Als ob der Strom durch beide Widerstände nach Masse flösse; der Knoten ist aber selbst
  virtuelle Masse.

::: explanation
Der invertierende Eingang liegt auf $0\,\mathrm{V}$. Die Quelle treibt also
$I_e = U_e/R_1$, und der Eingangswiderstand ist $U_e/I_e = R_1$.
:::
::::

:::: {.mcq #mc-verstaerker-grundschaltungen-006 type="single" difficulty="2"}
Ein invertierender Verstärker mit $R_1 = 2\,\mathrm{k\Omega}$ und $R_2 = 18\,\mathrm{k\Omega}$
ist am Ausgang auf $\pm 12\,\mathrm{V}$ begrenzt. Welche Ausgangsspannung stellt sich für
$U_e = 1.5\,\mathrm{V}$ ein?

- [ ] $-13.5\,\mathrm{V}$

  Rechnerischer Wert ohne Blick auf die Ausgangsgrenze.

- [ ] $+12\,\mathrm{V}$

  Vorzeichen falsch: Der Ausgang sättigt mit dem Vorzeichen von $V \cdot U_e$.

- [x] $-12\,\mathrm{V}$

  $V \cdot U_e = -13.5\,\mathrm{V}$ liegt jenseits der Grenze, der Ausgang bleibt bei $-12\,\mathrm{V}$.

- [ ] $0\,\mathrm{V}$

  In der Sättigung bricht der Ausgang nicht zusammen, er bleibt an der Grenze.

::: explanation
$V = -9$, also wäre $U_a = -13.5\,\mathrm{V}$. Der Ausgang kann nicht unter
$-12\,\mathrm{V}$ und bleibt dort; die virtuelle Masse gilt in der Sättigung nicht mehr.
:::
::::

:::: {.mcq #mc-verstaerker-grundschaltungen-007 type="single" difficulty="3"}
Ein invertierender Verstärker hat $R_1 = 5.6\,\mathrm{k\Omega}$ und $R_2 = 39\,\mathrm{k\Omega}$,
der Ausgang ist auf $\pm 11\,\mathrm{V}$ begrenzt. Bis zu welcher Amplitude der
Eingangsspannung bleibt der Ausgang linear?

- [ ] $1.381\,\mathrm{V}$

  Mit $1 + R_2/R_1$ gerechnet, der Verstärkung des nichtinvertierenden Verstärkers.

- [ ] $3.159\,\mathrm{V}$

  Den ganzen Hub von $22\,\mathrm{V}$ statt der Grenze $11\,\mathrm{V}$ durch $|V|$ geteilt.

- [ ] $76.61\,\mathrm{V}$

  Mit $|V|$ multipliziert statt dividiert.

- [x] $1.579\,\mathrm{V}$

  $U_\mathrm{sat}/|V| = 11\,\mathrm{V}/6.964$.

::: explanation
$|V| = 39/5.6 \approx 6.964$. Der Ausgang erreicht $\pm 11\,\mathrm{V}$ bei
$|U_e| = 11\,\mathrm{V}/6.964 \approx 1.579\,\mathrm{V}$; größere Amplituden werden
abgeschnitten.
:::
::::

:::: {.mcq #mc-verstaerker-grundschaltungen-008 type="single" difficulty="3"}
Ein invertierender Verstärker ($R_1 = 10\,\mathrm{k\Omega}$, $R_2 = 56\,\mathrm{k\Omega}$) wird
aus einer Quelle mit Innenwiderstand $R_i = 2.5\,\mathrm{k\Omega}$ gespeist. Wie groß ist die
Verstärkung $U_a/U_0$ bezogen auf die Leerlaufspannung?

- [ ] $-5.6$

  Innenwiderstand nicht berücksichtigt.

- [x] $-4.48$

  $-R_2/(R_1 + R_i) = -56/12.5$.

- [ ] $-5.85$

  $R_i$ zu $R_2$ addiert statt zu $R_1$.

- [ ] $-7.467$

  $R_i$ von $R_1$ abgezogen statt addiert.

::: explanation
Der Quellenstrom fließt durch $R_i$ und $R_1$ in Reihe bis zur virtuellen Masse. In der
Knotenregel ersetzt $R_1 + R_i = 12.5\,\mathrm{k\Omega}$ den Widerstand $R_1$, also
$U_a/U_0 = -56/12.5 = -4.48$.
:::
::::

:::: {.mcq #mc-verstaerker-grundschaltungen-009 type="single" difficulty="2"}
Eine Quelle mit $U_0 = 2.5\,\mathrm{V}$ und $R_i = 39\,\mathrm{k\Omega}$ wird ohne
Spannungsfolger direkt an eine Last $R_L = 4.7\,\mathrm{k\Omega}$ angeschlossen. Welche
Spannung liegt an der Last?

- [ ] $2.5\,\mathrm{V}$

  Das gilt erst mit Spannungsfolger; direkt angeschlossen teilt sich die Spannung auf.

- [ ] $2.231\,\mathrm{V}$

  Das ist die Spannung an $R_i$: Teilerverhältnis $R_i/(R_i + R_L)$ statt $R_L/(R_i + R_L)$.

- [ ] $0.3013\,\mathrm{V}$

  $U_0 \cdot R_L/R_i$: Im Nenner fehlt $R_L$.

- [x] $0.2689\,\mathrm{V}$

  Spannungsteiler $U_0 \cdot R_L/(R_i + R_L)$.

::: explanation
$R_i$ und $R_L$ bilden einen Spannungsteiler:
$U_L = 2.5\,\mathrm{V} \cdot 4.7/43.7 \approx 0.2689\,\mathrm{V}$. Erst ein Spannungsfolger
dazwischen bringt die volle Leerlaufspannung an die Last.
:::
::::

:::: {.mcq #mc-verstaerker-grundschaltungen-010 type="single" difficulty="2"}
Ein nichtinvertierender Verstärker soll $V = 12$ haben, $R_1 = 1.8\,\mathrm{k\Omega}$ liegt
nach Masse. Welchen Wert braucht $R_2$?

- [ ] $21.6\,\mathrm{k\Omega}$

  $R_2 = V \cdot R_1$: die Eins der Formel $1 + R_2/R_1$ vergessen.

- [x] $19.8\,\mathrm{k\Omega}$

  $R_2 = (V - 1) \cdot R_1 = 11 \cdot 1.8\,\mathrm{k\Omega}$.

- [ ] $23.4\,\mathrm{k\Omega}$

  $(V + 1) \cdot R_1$: beim Umstellen das Vorzeichen der Eins vertauscht.

- [ ] $163.6\,\Omega$

  $R_1/(V - 1)$: Verhältnis beim Umstellen umgedreht.

::: explanation
Aus $V = 1 + R_2/R_1$ folgt $R_2 = (V - 1) \cdot R_1 = 11 \cdot 1.8\,\mathrm{k\Omega} = 19.8\,\mathrm{k\Omega}$.
:::
::::

:::: {.mcq #mc-verstaerker-grundschaltungen-011 type="single" difficulty="1"}
An einem invertierenden Verstärker liegt eine Sinusspannung. Welche Phasenlage hat die
Ausgangsspannung gegenüber der Eingangsspannung?

- [ ] $0^\circ$, gleichphasig

  Das gilt für den nichtinvertierenden Verstärker.

- [ ] $90^\circ$ nacheilend

  Eine Phase von $90^\circ$ entsteht erst mit einem Kondensator, etwa beim Integrierer.

- [x] $180^\circ$, gegenphasig

  Das Minuszeichen in $V = -R_2/R_1$ kehrt das Vorzeichen um.

- [ ] $45^\circ$ nacheilend

  Wie bei einem RC-Tiefpass an der Grenzfrequenz; hier gibt es keinen Kondensator.

::: explanation
$V = -R_2/R_1$ ist reell und negativ. Jeder Augenblickswert wird mit einer negativen Zahl
multipliziert, die Ausgangsspannung ist also gegenphasig.
:::
::::

:::: {.mcq #mc-verstaerker-grundschaltungen-012 type="multi" difficulty="2"}
Welche Aussagen gelten für den nichtinvertierenden Verstärker mit idealem OPV im linearen
Betrieb?

- [x] Die Verstärkung ist mindestens 1.

  $V = 1 + R_2/R_1 \ge 1$, weil $R_2/R_1 \ge 0$ ist.

- [ ] Sein Eingangswiderstand ist $R_1$.

  Falsch: Das gilt für den invertierenden Verstärker; hier fließt kein Strom in den Eingang.

- [x] Am invertierenden Eingang liegt die Spannung $U_e$.

  Wegen $U_d = 0$ ist $U_n = U_p = U_e$.

- [ ] Die Verstärkung ist $R_2/R_1$.

  Falsch: Die Eins fehlt, richtig ist $1 + R_2/R_1$.

- [x] Ausgangs- und Eingangsspannung sind gleichphasig.

  $V$ ist positiv.

::: explanation
Der Eingang liegt direkt am nichtinvertierenden Eingang, in den kein Strom fließt. Wegen
$U_d = 0$ teilt der unbelastete Teiler $U_a$ genau auf $U_e$ herunter; daraus folgt
$V = 1 + R_2/R_1$, positiv und mindestens 1.
:::
::::

:::: {.mcq #mc-verstaerker-grundschaltungen-013 type="multi" difficulty="3" pin-last="true"}
Welche Aussagen gelten für einen Summierer mit idealem OPV und den Eingangswiderständen
$R_1$, $R_2$, $R_3$?

- [x] Die Eingänge beeinflussen sich gegenseitig nicht.

  Der Knoten ist eine virtuelle Masse; jeder Strom hängt nur von seiner Spannung ab.

- [ ] Für beliebige $R_i$ gilt $U_a = -(U_1 + U_2 + U_3)$.

  Falsch: Das gilt nur mit $R_1 = R_2 = R_3 = R_F$; sonst hat jeder Eingang sein Gewicht.

- [x] Der Eingangswiderstand am Eingang $i$ ist $R_i$.

  Jeder Eingang sieht seinen Widerstand gegen die virtuelle Masse.

- [ ] Eine Verdopplung von $R_F$ ändert nur das Gewicht von $U_1$.

  Falsch: $R_F$ steht in jedem Gewicht $-R_F/R_i$, alle Gewichte verdoppeln sich.

- [ ] Keine der Aussagen ist richtig.

  Zwei der Aussagen sind richtig.

::: explanation
$U_a = -R_F \cdot (U_1/R_1 + U_2/R_2 + U_3/R_3)$: Jeder Eingang treibt seinen Strom in die
virtuelle Masse, unabhängig von den anderen, und sieht dabei seinen Widerstand. $R_F$ skaliert
alle Gewichte gleich.
:::
::::

:::: {.mcq #mc-verstaerker-grundschaltungen-014 type="multi" difficulty="2"}
Welche Schaltungen haben mit idealem OPV einen unendlich großen Eingangswiderstand?

- [ ] Invertierender Verstärker

  Falsch: Die Quelle sieht $R_1$ gegen die virtuelle Masse.

- [x] Nichtinvertierender Verstärker

  Die Quelle liegt nur am nichtinvertierenden Eingang, $I_p = 0$.

- [ ] Summierer, an jedem seiner Eingänge

  Falsch: Jeder Eingang sieht seinen Widerstand $R_i$.

- [x] Spannungsfolger

  Sonderfall des nichtinvertierenden Verstärkers, ebenfalls $I_p = 0$.

::: explanation
Unendlich ist der Eingangswiderstand dort, wo die Quelle nur am nichtinvertierenden Eingang
hängt. Wo sie über einen Widerstand an der virtuellen Masse liegt, ist es dieser Widerstand.
:::
::::

:::: {.mcq #mc-verstaerker-grundschaltungen-015 type="single" difficulty="3"}
Warum liegt der invertierende Eingang eines invertierenden Verstärkers im linearen Betrieb
auf $0\,\mathrm{V}$ (virtuelle Masse)?

- [ ] Er ist im OPV intern mit Masse verbunden.

  Es gibt keine Verbindung; deshalb heißt sie „virtuell“, und kein Strom fließt nach Masse.

- [ ] Durch $R_1$ fließt im Betrieb kein Strom.

  Durch $R_1$ fließt $U_e/R_1$; stromlos sind nur die OPV-Eingänge.

- [x] Die Gegenkopplung regelt $U_d$ auf null, und $U_p$ liegt auf Masse.

  Aus $U_d = 0$ und $U_p = 0$ folgt $U_n = 0$.

- [ ] Der Ausgangswiderstand des idealen OPV ist null.

  Der Ausgangswiderstand betrifft den Ausgang, nicht die Spannung am Eingang.

::: explanation
Bei Gegenkopplung stellt sich der Ausgang so ein, dass $U_d = U_a/V_0 \to 0$ wird. Weil der
nichtinvertierende Eingang auf Masse liegt, ist dann auch $U_n = 0$, ohne dass eine
Verbindung zur Masse besteht; in der Sättigung geht das verloren.
:::
::::

:::: {.mcq #mc-verstaerker-grundschaltungen-016 type="single" difficulty="3"}
Ein Summierer mit $R_F = 47\,\mathrm{k\Omega}$ soll $U_1$ mit dem Gewicht $-4$ bewerten. Welchen
Wert braucht $R_1$?

- [ ] $188\,\mathrm{k\Omega}$

  $R_F$ mit dem Gewicht multipliziert statt dividiert.

- [ ] $1.175\,\mathrm{k\Omega}$

  Zehnerpotenz falsch: $47\,\mathrm{k\Omega}/4$ um den Faktor 10 verschoben.

- [ ] $15.67\,\mathrm{k\Omega}$

  $R_F/3$: Gewicht um eins verringert, als wäre es $1 + R_F/R_1$.

- [x] $11.75\,\mathrm{k\Omega}$

  $R_1 = R_F/4$.

::: explanation
Das Gewicht des Eingangs ist $-R_F/R_1 = -4$, also
$R_1 = R_F/4 = 47\,\mathrm{k\Omega}/4 = 11.75\,\mathrm{k\Omega}$.
:::
::::
