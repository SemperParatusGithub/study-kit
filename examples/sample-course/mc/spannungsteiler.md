---
topic: spannungsteiler
title: Spannungsteiler und Ersatzquellen
---

:::: {.mcq #mc-spannungsteiler-001 type="single" difficulty="1"}
Ein unbelasteter Spannungsteiler aus $R_1 = 3\,\mathrm{k\Omega}$ und
$R_2 = 1\,\mathrm{k\Omega}$ liegt an $U_0 = 12\,\mathrm{V}$. Wie groß ist die Spannung
$U_2$ über $R_2$?

- [ ] $9\,\mathrm{V}$

  Das ist $U_1$ über $R_1$: Im Zähler steht der falsche Widerstand.

- [x] $3\,\mathrm{V}$

  $U_2 = U_0 \cdot R_2/(R_1 + R_2) = 12\,\mathrm{V} \cdot 1/4$.

- [ ] $4\,\mathrm{V}$

  $U_0 \cdot R_2/R_1$: Im Nenner fehlt $R_2$, es muss die Summe beider Widerstände stehen.

- [ ] $6\,\mathrm{V}$

  Gleichmäßige Aufteilung angenommen; das gilt nur für $R_1 = R_2$.

::: explanation
Durch beide Widerstände fließt derselbe Strom $I = 12\,\mathrm{V}/4\,\mathrm{k\Omega} = 3\,\mathrm{mA}$,
also ist $U_2 = I R_2 = 3\,\mathrm{V}$. Die Teilspannungen verhalten sich wie die Widerstände.
:::
::::

:::: {.mcq #mc-spannungsteiler-002 type="single" difficulty="1"}
Ein Strom $I_0 = 30\,\mathrm{mA}$ teilt sich auf die parallelen Widerstände
$R_1 = 100\,\Omega$ und $R_2 = 200\,\Omega$ auf. Welcher Strom fließt durch $R_1$?

- [ ] $10\,\mathrm{mA}$

  Spannungsteilerregel angewendet: $R_1$ im Zähler statt $R_2$.

- [ ] $15\,\mathrm{mA}$

  Gleichmäßige Aufteilung angenommen; die Ströme hängen aber von den Widerständen ab.

- [ ] $30\,\mathrm{mA}$

  Parallel- mit Reihenschaltung verwechselt: Nur in Reihe fließt durch beide derselbe Strom.

- [x] $20\,\mathrm{mA}$

  $I_1 = I_0 \cdot R_2/(R_1 + R_2) = 30\,\mathrm{mA} \cdot 2/3$.

::: explanation
Beide Widerstände liegen an derselben Spannung, daher fließt durch den kleineren
Widerstand der größere Strom: $I_1 : I_2 = R_2 : R_1 = 2 : 1$.
:::
::::

:::: {.mcq #mc-spannungsteiler-003 type="single" difficulty="2"}
Ein Teiler mit $R_1 = R_2 = 10\,\mathrm{k\Omega}$ an $U_0 = 10\,\mathrm{V}$ wird mit
$R_\mathrm{L} = 10\,\mathrm{k\Omega}$ parallel zu $R_2$ belastet. Wie groß ist $U_2$?

- [ ] $5\,\mathrm{V}$

  Die Last wurde ignoriert; das ist die Leerlaufspannung.

- [x] $3{,}33\,\mathrm{V}$

  $R_2 \parallel R_\mathrm{L} = 5\,\mathrm{k\Omega}$, also $U_2 = 10\,\mathrm{V} \cdot 5/15$.

- [ ] $6{,}67\,\mathrm{V}$

  Das ist die Spannung über $R_1$, nicht über der Last.

- [ ] $2{,}5\,\mathrm{V}$

  Die Parallelschaltung nur im Zähler eingesetzt, im Nenner aber $R_1 + R_2$ stehen
  lassen.

::: explanation
Mit Last gilt die Teilerregel nur, wenn man $R_2$ durch $R_2 \parallel R_\mathrm{L}$
ersetzt, und zwar in Zähler und Nenner.
:::
::::

:::: {.mcq #mc-spannungsteiler-004 type="single" difficulty="2"}
Ein Teiler aus $R_1 = 3\,\mathrm{k\Omega}$ und $R_2 = 6\,\mathrm{k\Omega}$ liegt an
$U_0 = 12\,\mathrm{V}$; die Klemmen A und B liegen an $R_2$. Wie groß ist der
Innenwiderstand der Ersatzspannungsquelle?

- [ ] $9\,\mathrm{k\Omega}$

  $R_1$ und $R_2$ in Reihe addiert; von den Klemmen aus liegen sie aber parallel.

- [ ] $6\,\mathrm{k\Omega}$

  Die Quelle durch einen Leerlauf statt durch einen Kurzschluss ersetzt; dann bliebe nur
  $R_2$ übrig.

- [ ] $3\,\mathrm{k\Omega}$

  Nur $R_1$ berücksichtigt, als gehöre $R_2$ schon zur Last.

- [x] $2\,\mathrm{k\Omega}$

  $R_\mathrm{i} = R_1 \parallel R_2 = 3 \cdot 6/9\,\mathrm{k\Omega}$.

::: explanation
Für $R_\mathrm{i}$ wird die ideale Spannungsquelle kurzgeschlossen. Von A und B aus
gesehen liegen $R_1$ und $R_2$ dann parallel. Kontrolle:
$U_\mathrm{q} = 8\,\mathrm{V}$, $I_\mathrm{k} = 4\,\mathrm{mA}$, $U_\mathrm{q}/I_\mathrm{k} = 2\,\mathrm{k\Omega}$.
:::
::::

:::: {.mcq #mc-spannungsteiler-005 type="single" difficulty="2"}
Eine lineare Quelle mit $U_\mathrm{q}$ und $R_\mathrm{i}$ speist einen Lastwiderstand
$R_\mathrm{L}$. Für welchen Wert von $R_\mathrm{L}$ nimmt die Last die größte Leistung
auf?

- [x] $R_\mathrm{L} = R_\mathrm{i}$

  Leistungsanpassung: $P_\mathrm{L} = U_\mathrm{q}^2 R_\mathrm{L}/(R_\mathrm{i} + R_\mathrm{L})^2$
  ist dort maximal.

- [ ] $R_\mathrm{L} \to \infty$

  Dann ist die Spannung maximal, aber der Strom und damit die Leistung null.

- [ ] $R_\mathrm{L} \to 0$

  Dann ist der Strom maximal, aber die Spannung an der Last und damit die Leistung null.

- [ ] $R_\mathrm{L} = 2R_\mathrm{i}$

  Hier ist die Lastspannung größer, der Strom aber kleiner; die Leistung erreicht nur
  $8/9$ des Maximums.

::: explanation
Die Ableitung von $P_\mathrm{L}(R_\mathrm{L})$ wird bei $R_\mathrm{L} = R_\mathrm{i}$ null.
Dann liegt an der Last die halbe Leerlaufspannung $U_\mathrm{q}/2$, und es gilt
$P_\mathrm{max} = U_\mathrm{q}^2/(4R_\mathrm{i})$.
:::
::::

:::: {.mcq #mc-spannungsteiler-006 type="single" difficulty="3"}
Eine reale Spannungsquelle besteht aus einer idealen Quelle mit
$U_\mathrm{q} = 10\,\mathrm{V}$ und einem Innenwiderstand $R_\mathrm{i} = 50\,\Omega$ in
Reihe. Wie groß ist die größte Leistung, die sie an eine Last abgeben kann?

- [ ] $2\,\mathrm{W}$

  $U_\mathrm{q}^2/R_\mathrm{i}$: Die volle Quellspannung an der Last angenommen.

- [x] $0{,}5\,\mathrm{W}$

  $P_\mathrm{max} = U_\mathrm{q}^2/(4R_\mathrm{i}) = 100\,\mathrm{V^2}/200\,\Omega$.

- [ ] $1\,\mathrm{W}$

  $U_\mathrm{q}^2/(2R_\mathrm{i})$ gibt die ideale Quelle insgesamt ab, an Last und
  Innenwiderstand zusammen.

::: explanation
Bei Leistungsanpassung ist $R_\mathrm{L} = 50\,\Omega$; an der Last liegen
$5\,\mathrm{V}$, und es fließen $0{,}1\,\mathrm{A}$. Das ergibt $0{,}5\,\mathrm{W}$ in der
Last und, weil $R_\mathrm{i}$ hier ein realer Widerstand ist, noch einmal so viel im
Innenwiderstand.
:::
::::

:::: {.mcq #mc-spannungsteiler-007 type="multi" difficulty="2"}
Welche Aussagen über den unbelasteten Spannungsteiler aus $R_1$ und $R_2$ sind richtig?

- [x] Durch $R_1$ und $R_2$ fließt derselbe Strom.

  Ohne Last sind beide Widerstände in Reihe geschaltet.

- [ ] Verdoppelt man beide Widerstände, halbiert sich $U_2$.

  Das Verhältnis bleibt gleich; nur der Querstrom halbiert sich.

- [x] Das Verhältnis $U_2/U_0$ hängt nur von $R_1$ und $R_2$ ab, nicht von $U_0$.

  Die Schaltung ist linear: $U_2/U_0 = R_2/(R_1 + R_2)$.

- [ ] Am größeren Widerstand liegt die kleinere Teilspannung.

  Umgekehrt: Bei gleichem Strom ist die Spannung proportional zum Widerstand.

- [ ] Eine Last parallel zu $R_2$ erhöht $U_2$.

  $R_2 \parallel R_\mathrm{L}$ ist kleiner als $R_2$, daher sinkt $U_2$.

::: explanation
Der unbelastete Teiler ist eine Reihenschaltung. Die Teilspannungen sind proportional zu
den Widerständen und skalieren linear mit $U_0$.
:::
::::

:::: {.mcq #mc-spannungsteiler-008 type="multi" difficulty="3"}
Eine Schaltung wird an den Klemmen A und B durch eine Ersatzspannungsquelle aus
$U_\mathrm{q}$ und $R_\mathrm{i}$ ersetzt. Welche Aussagen sind richtig?

- [ ] Zur Bestimmung von $R_\mathrm{i}$ werden ideale Spannungsquellen durch Leerläufe
  ersetzt.

  Spannungsquellen werden kurzgeschlossen; nur Stromquellen werden durch Leerläufe
  ersetzt.

- [x] $U_\mathrm{q}$ ist die Spannung an den offenen Klemmen.

  Ohne Last fällt an $R_\mathrm{i}$ keine Spannung ab.

- [ ] Die Ersatzquelle liefert auch die Verlustleistung im Inneren der ursprünglichen
  Schaltung richtig.

  Gleichwertig ist nur das Verhalten an den Klemmen, nicht das Innere.

- [x] Es gilt $R_\mathrm{i} = U_\mathrm{q}/I_\mathrm{k}$ mit dem Kurzschlussstrom
  $I_\mathrm{k}$.

  Bei Kurzschluss liegt $U_\mathrm{q}$ ganz an $R_\mathrm{i}$.

::: explanation
Die Ersatzspannungsquelle bildet nur die Klemmenkennlinie nach: Leerlaufspannung und
Kurzschlussstrom stimmen überein, Ströme und Leistungen im Inneren im Allgemeinen nicht.
:::
::::

:::: {.mcq #mc-spannungsteiler-009 type="kprim" difficulty="2"}
Zwei Widerstände $R_1 = 1\,\mathrm{k\Omega}$ und $R_2 = 4\,\mathrm{k\Omega}$ liegen parallel
an einer Stromquelle mit $I_0 = 10\,\mathrm{mA}$. Beurteilen Sie die Aussagen.

- [x] Der Gesamtwiderstand beträgt $800\,\Omega$.

  $R_1 \parallel R_2 = 1 \cdot 4/5\,\mathrm{k\Omega}$.

- [ ] Durch $R_1$ fließen $2\,\mathrm{mA}$.

  Falsch: $I_1 = I_0 \cdot R_2/(R_1 + R_2) = 8\,\mathrm{mA}$. Die $2\,\mathrm{mA}$ entstehen
  mit $R_1$ im Zähler.

- [x] An beiden Widerständen liegen $8\,\mathrm{V}$.

  $U = I_0 \cdot 800\,\Omega = 8\,\mathrm{V}$.

- [ ] Der Gesamtwiderstand ist größer als der kleinere Einzelwiderstand.

  Falsch: Eine Parallelschaltung ist immer kleiner als ihr kleinster Zweigwiderstand.

::: explanation
Zuerst den Ersatzwiderstand bestimmen, dann die gemeinsame Spannung; die Teilströme folgen
mit dem ohmschen Gesetz: $8\,\mathrm{mA}$ durch $R_1$ und $2\,\mathrm{mA}$ durch $R_2$.
:::
::::

:::: {.mcq #mc-spannungsteiler-010 type="kprim" difficulty="3"}
Ein Spannungsteiler aus $R_1$ und $R_2$ wird mit $R_\mathrm{L}$ parallel zu $R_2$ belastet.
Beurteilen Sie die Aussagen.

- [ ] Für $R_\mathrm{L} \to 0$ geht $U_2$ gegen $U_0$.

  Falsch: $R_\mathrm{L} \to 0$ ist ein Kurzschluss am Ausgang, also $U_2 \to 0$.

- [x] Für $R_\mathrm{L} \to \infty$ geht $U_2$ gegen $U_0 \cdot R_2/(R_1 + R_2)$.

  Richtig: Das ist der Leerlauf.

- [ ] Der Strom durch $R_1$ hängt nicht von $R_\mathrm{L}$ ab.

  Falsch: Durch $R_1$ fließt die Summe aus dem Strom durch $R_2$ und dem Laststrom.

- [x] Bei gleichem Verhältnis $R_1 : R_2$ wirkt sich die Last umso weniger aus, je kleiner
  $R_1$ und $R_2$ sind.

  Richtig: Der Innenwiderstand $R_1 \parallel R_2$ wird kleiner.

::: explanation
Mit der Ersatzspannungsquelle gilt $U_2 = U_\mathrm{q} R_\mathrm{L}/(R_\mathrm{i} + R_\mathrm{L})$
mit $R_\mathrm{i} = R_1 \parallel R_2$. Ein kleiner Innenwiderstand macht den Teiler
belastbarer, kostet aber Querstrom.
:::
::::
