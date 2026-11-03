---
topic: idealer-opv
title: Idealer Operationsverstärker und Gegenkopplung
---

:::: {.mcq #mc-idealer-opv-001 type="single" difficulty="1"}
Welche Leerlaufverstärkung $V_0$ hat ein idealer Operationsverstärker?

- [ ] $V_0 = 1$

  Das ist die Verstärkung des Spannungsfolgers, nicht die des OPV selbst.

- [ ] $V_0 \approx 10^5$

  Das ist ein typischer realer Wert; das ideale Modell nimmt den Grenzwert an.

- [x] $V_0 \to \infty$

  Das ideale Modell setzt die Leerlaufverstärkung unendlich groß.

- [ ] $V_0 = 0$

  Mit $V_0 = 0$ gäbe der OPV gar kein Signal aus; verwechselt mit $U_d = 0$.

::: explanation
Der ideale OPV hat $V_0 \to \infty$. Reale OPV erreichen $10^5$ bis $10^6$; mit
Gegenkopplung ist das so viel, dass die Rechnung mit $V_0 \to \infty$ kaum abweicht.
:::
::::

:::: {.mcq #mc-idealer-opv-002 type="single" difficulty="1"}
Welchen Ausgangswiderstand $R_a$ hat ein idealer Operationsverstärker?

- [x] $R_a \to 0$

  Die Ausgangsspannung hängt dann nicht von der Last ab.

- [ ] $R_a \to \infty$

  Das gilt für den Eingangswiderstand $R_e$, nicht für den Ausgang.

- [ ] $R_a = R_2$

  $R_2$ ist ein äußerer Widerstand der Rückführung, kein Teil des OPV.

- [ ] $R_a = R_1$

  $R_1$ gehört zur äußeren Beschaltung und bestimmt den Eingangswiderstand der Schaltung.

::: explanation
Ideal sind $R_e \to \infty$ (keine Eingangsströme) und $R_a \to 0$: Der Ausgang wirkt
wie eine ideale Spannungsquelle, deren Spannung bei jeder Last erhalten bleibt.
:::
::::

:::: {.mcq #mc-idealer-opv-003 type="single" difficulty="1"}
Was versteht man bei einem Operationsverstärker unter Gegenkopplung?

- [ ] Die Rückführung vom Ausgang auf den nichtinvertierenden Eingang

  Das ist Mitkopplung: Sie verstärkt jede Abweichung und treibt den Ausgang in die Sättigung.

- [ ] Die direkte Verbindung der beiden Eingänge miteinander

  Der virtuelle Kurzschluss ist keine Verbindung, sondern eine Folge der Gegenkopplung.

- [ ] Die Rückführung vom Eingang auf die Versorgungsspannung

  Die Versorgung hat mit der Rückkopplung nichts zu tun.

- [x] Die Rückführung vom Ausgang auf den invertierenden Eingang

  Ein Anstieg von $U_a$ hebt $U_n$ an und wirkt sich so selbst entgegen.

::: explanation
Bei Gegenkopplung gelangt ein Teil von $U_a$ an den invertierenden Eingang. Steigt $U_a$,
sinkt $U_d = U_p - U_n$, und der Ausgang stellt sich auf einen stabilen Wert ein.
:::
::::

:::: {.mcq #mc-idealer-opv-004 type="single" difficulty="2"}
Ein OPV ohne Rückkopplung hat $V_0 = 10^5$ und $U_\mathrm{sat} = 12\,\mathrm{V}$. Bis zu
welchem Betrag der Differenzspannung $U_d$ arbeitet er linear?

- [ ] $1.2\,\mathrm{mV}$

  Zehnerpotenz falsch: mit $V_0 = 10^4$ gerechnet.

- [x] $120\,\mathrm{\mu V}$

  $U_\mathrm{sat}/V_0 = 12\,\mathrm{V}/10^5$.

- [ ] $240\,\mathrm{\mu V}$

  Den ganzen Aussteuerbereich $2 U_\mathrm{sat}$ statt $U_\mathrm{sat}$ eingesetzt.

- [ ] $12\,\mathrm{\mu V}$

  Zehnerpotenz falsch: mit $V_0 = 10^6$ gerechnet.

::: explanation
Der Ausgang erreicht die Sättigung bei $V_0 \cdot |U_d| = U_\mathrm{sat}$, also bei
$|U_d| = 12\,\mathrm{V}/10^5 = 120\,\mathrm{\mu V}$. Größere Differenzspannungen ändern
$U_a$ nicht mehr.
:::
::::

:::: {.mcq #mc-idealer-opv-005 type="single" difficulty="2"}
Ein OPV ohne Rückkopplung hat $V_0 = 2 \cdot 10^5$ und $U_\mathrm{sat} = 13\,\mathrm{V}$.
Welche Ausgangsspannung stellt sich bei $U_d = 0.1\,\mathrm{mV}$ ein?

- [ ] $20\,\mathrm{V}$

  Sättigung übersehen: $V_0 \cdot U_d$ ist größer als $U_\mathrm{sat}$.

- [ ] $2\,\mathrm{V}$

  Zehnerpotenz falsch: $0.1\,\mathrm{mV}$ als $10^{-5}\,\mathrm{V}$ eingesetzt.

- [x] $13\,\mathrm{V}$

  Rechnerisch $20\,\mathrm{V}$, begrenzt auf $U_\mathrm{sat}$.

- [ ] $0\,\mathrm{V}$

  $U_d = 0$ gilt nur mit Gegenkopplung, hier ist $U_d$ gegeben.

::: explanation
$V_0 \cdot U_d = 2 \cdot 10^5 \cdot 10^{-4}\,\mathrm{V} = 20\,\mathrm{V}$ übersteigt die
Sättigungsspannung. Der Ausgang bleibt deshalb bei $+U_\mathrm{sat} = 13\,\mathrm{V}$
stehen.
:::
::::

:::: {.mcq #mc-idealer-opv-006 type="single" difficulty="2"}
Bei einem invertierenden Verstärker liegt der nichtinvertierende Eingang auf Masse. Was
gilt im linearen Betrieb für den invertierenden Eingang?

- [ ] Er ist intern mit Masse verbunden, deshalb ist $U_n = 0$.

  Es gibt keine Verbindung; $U_n = 0$ stellt erst die Gegenkopplung her.

- [x] Es ist $U_n = 0$, aber von dort fließt kein Strom nach Masse.

  Virtuelle Masse: gleiches Potential wie Masse, ohne Verbindung und ohne Strom.

- [ ] Der Strom durch $R_1$ fließt in den invertierenden Eingang.

  Ideal ist $I_n = 0$; der Strom durch $R_1$ fließt weiter über $R_2$.

- [ ] Es ist $U_n = U_a$, weil $R_2$ beide Punkte verbindet.

  Über $R_2$ fällt eine Spannung ab; nur beim Spannungsfolger gilt $U_n = U_a$.

::: explanation
Mit Gegenkopplung gilt $U_n = U_p = 0$ (virtuelle Masse), und wegen $I_n = 0$ fließt der
Strom $U_e/R_1$ vollständig über $R_2$ zum Ausgang. Daraus folgt die Knotengleichung
$U_e/R_1 + U_a/R_2 = 0$.
:::
::::

:::: {.mcq #mc-idealer-opv-007 type="single" difficulty="3"}
Ein nichtinvertierender Verstärker hat $R_1 = 1\,\mathrm{k\Omega}$ nach Masse,
$R_2 = 19\,\mathrm{k\Omega}$ in der Rückführung und einen OPV mit $V_0 = 10^4$. Um wie
viel Prozent liegt seine Verstärkung unter dem idealen Wert $1/k$?

- [ ] $0.01\,\%$

  Das ist $1/V_0$: Der Rückkopplungsfaktor $k$ fehlt in der Schleifenverstärkung.

- [ ] $5\,\%$

  Das ist der Rückkopplungsfaktor $k$ selbst, nicht der Fehler.

- [ ] $0.002\,\%$

  Der Fehler $0.002$ ist ein Anteil; als Prozentwert ist er $100$-mal größer.

- [x] $0.2\,\%$

  $1/(1 + k V_0) = 1/501$.

::: explanation
Mit $k = 1/20 = 0.05$ ist die Schleifenverstärkung $k V_0 = 500$. Der relative Fehler
gegenüber $1/k = 20$ ist $1/(1 + k V_0) = 1/501 \approx 0.002 = 0.2\,\%$.
:::
::::

:::: {.mcq #mc-idealer-opv-008 type="single" difficulty="3"}
Ein invertierender Verstärker hat $R_1 = 10\,\mathrm{k\Omega}$,
$R_2 = 100\,\mathrm{k\Omega}$ und $U_\mathrm{sat} = 12\,\mathrm{V}$. Welche Spannung $U_n$
liegt bei $U_e = 1.5\,\mathrm{V}$ am invertierenden Eingang?

- [ ] $0\,\mathrm{V}$

  Virtuelle Masse angenommen, obwohl der Ausgang in der Sättigung ist.

- [x] $0.273\,\mathrm{V}$

  Teiler zwischen $U_e$ und $U_a = -12\,\mathrm{V}$, weil der Ausgang gesättigt ist.

- [ ] $1.5\,\mathrm{V}$

  Den Spannungsabfall an $R_1$ vergessen und $U_n = U_e$ gesetzt.

- [ ] $-1.09\,\mathrm{V}$

  Nur $U_a$ geteilt und den Beitrag von $U_e$ vergessen.

::: explanation
Rechnerisch wäre $U_a = -10 \cdot 1.5\,\mathrm{V} = -15\,\mathrm{V}$, also ist
$U_a = -12\,\mathrm{V}$. Ohne Eingangsstrom fließt durch beide Widerstände
$I = 13.5\,\mathrm{V}/110\,\mathrm{k\Omega}$, und
$U_n = U_e - I R_1 \approx 0.273\,\mathrm{V}$: Die virtuelle Masse gilt nicht mehr.
:::
::::

:::: {.mcq #mc-idealer-opv-009 type="multi" difficulty="2"}
Welche Aussagen gelten für einen idealen OPV mit Gegenkopplung im linearen Betrieb?

- [x] Die Verstärkung hängt nur von der äußeren Beschaltung ab.

  Mit $V_0 \to \infty$ wird $V = 1/k$, und $k$ bilden die äußeren Widerstände.

- [ ] Die Regeln gelten auch, wenn der Ausgang in der Sättigung ist.

  In der Sättigung wirkt die Gegenkopplung nicht, und $U_d \ne 0$.

- [x] $U_d = U_a/V_0$ geht gegen null, obwohl $U_a$ endlich ist.

  Daraus folgt der virtuelle Kurzschluss $U_p = U_n$.

- [ ] Die beiden Eingänge sind niederohmig miteinander verbunden.

  Der Kurzschluss ist nur virtuell: gleiches Potential, aber kein Strom.

- [ ] Der Strom durch die Rückführung fließt in den invertierenden Eingang.

  Ideal ist $I_n = 0$; der Strom fließt über die äußeren Widerstände.

::: explanation
Gegenkopplung und $V_0 \to \infty$ erzwingen $U_d = U_a/V_0 \to 0$; mit $I_p = I_n = 0$
bestimmen allein die äußeren Bauteile das Verhalten. Beides gilt nur, solange
$|U_a| < U_\mathrm{sat}$ ist.
:::
::::

:::: {.mcq #mc-idealer-opv-010 type="multi" difficulty="3"}
Welche Aussagen gelten für die Verstärkung $V = V_0/(1 + k V_0)$ einer Gegenkopplung mit
dem Rückkopplungsfaktor $k$?

- [ ] Verdoppelt sich $V_0$, verdoppelt sich auch $V$.

  Für $k V_0 \gg 1$ ändert sich $V$ kaum; die Gegenkopplung macht $V$ unempfindlich.

- [x] Für $k V_0 \gg 1$ gilt $V \approx 1/k$.

  Die $1$ im Nenner ist dann gegen $k V_0$ vernachlässigbar.

- [ ] Beim nichtinvertierenden Verstärker ist $k = R_2/(R_1 + R_2)$.

  Zurückgeführt wird der Anteil an $R_1$ nach Masse: $k = R_1/(R_1 + R_2)$.

- [x] Der relative Fehler gegenüber $1/k$ ist $1/(1 + k V_0)$.

  $(1/k - V)/(1/k) = 1 - k V_0/(1 + k V_0) = 1/(1 + k V_0)$.

::: explanation
Die Schleifenverstärkung $k V_0$ bestimmt die Genauigkeit: Je größer sie ist, desto
näher liegt $V$ bei $1/k$, und der relative Fehler ist $1/(1 + k V_0)$. Beim
nichtinvertierenden Verstärker ist $1/k = 1 + R_2/R_1$.
:::
::::
