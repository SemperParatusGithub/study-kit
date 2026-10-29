---
topic: spannungsteiler
title: Spannungsteiler und Ersatzquellen
objectives:
  - 'Die Spannungsteilerregel für zwei Widerstände in Reihe anwenden'
  - 'Die Stromteilerregel für zwei parallele Widerstände anwenden'
  - 'Die Ausgangsspannung eines belasteten Spannungsteilers berechnen'
  - 'Eine lineare Schaltung durch die Ersatzspannungsquelle aus $U_\mathrm{q}$ und $R_\mathrm{i}$ ersetzen'
  - 'Die Bedingung für Leistungsanpassung angeben'
---

## Unbelasteter Spannungsteiler

Zwei Widerstände in Reihe an einer Spannungsquelle bilden die einfachste Schaltung, mit
der sich aus einer festen Spannung eine kleinere gewinnen lässt.

![Unbelasteter Spannungsteiler: Die Quelle U0 speist R1 und R2 in Reihe](fig:st-teiler)

Durch beide Widerstände fließt derselbe Strom $I = U_0/(R_1 + R_2)$. Multipliziert man ihn
mit dem jeweiligen Widerstand, folgt die Spannungsteilerregel.

::: theorem
**Spannungsteilerregel**

$$
U_1 = U_0 \cdot \frac{R_1}{R_1 + R_2}, \qquad U_2 = U_0 \cdot \frac{R_2}{R_1 + R_2}
$$

Die Teilspannungen verhalten sich wie die Widerstände: $U_1 : U_2 = R_1 : R_2$.
:::

::: example
**Beispiel**

An $U_0 = 10\,\mathrm{V}$ liegen $R_1 = 2\,\mathrm{k\Omega}$ und $R_2 = 3\,\mathrm{k\Omega}$
in Reihe. Dann ist $U_2 = 10\,\mathrm{V} \cdot 3/5 = 6\,\mathrm{V}$ und
$U_1 = 4\,\mathrm{V}$; zusammen ergeben sie wieder $U_0$.
:::

Übung: [Unbelasteter Spannungsteiler](ex:ex-st-unbelastet)

## Stromteiler

![Stromteiler: Die Stromquelle I0 speist R1 und R2 parallel](fig:st-stromteiler)

An parallel geschalteten Widerständen liegt dieselbe Spannung. Mit dem Ersatzwiderstand

$$
R_1 \parallel R_2 = \frac{R_1 R_2}{R_1 + R_2}
$$

ist $U = I_0 \cdot (R_1 \parallel R_2)$, und die Teilströme folgen aus $I_1 = U/R_1$ und
$I_2 = U/R_2$.

::: theorem
**Stromteilerregel**

$$
I_1 = I_0 \cdot \frac{R_2}{R_1 + R_2}, \qquad I_2 = I_0 \cdot \frac{R_1}{R_1 + R_2}
$$

Der größere Strom fließt durch den kleineren Widerstand: $I_1 : I_2 = R_2 : R_1$.
:::

::: warning
**Häufiger Fehler**

Beim Stromteiler steht im Zähler der Widerstand des *anderen* Zweigs. Wer die
Spannungsteilerregel abschreibt, vertauscht die beiden Teilströme.
:::

Übung: [Stromteiler](ex:ex-st-stromteiler)

## Belasteter Spannungsteiler

![Belasteter Spannungsteiler: Der Lastwiderstand RL liegt parallel zu R2](fig:st-teiler-last)

Schließt man an den Ausgang eine Last $R_\mathrm{L}$ an, fließt durch $R_1$ und $R_2$ nicht
mehr derselbe Strom, und die Teilerregel gilt in ihrer einfachen Form nicht mehr. Man
fasst $R_2$ und $R_\mathrm{L}$ zur Parallelschaltung zusammen und teilt erneut:

$$
U_2 = U_0 \cdot \frac{R_2 \parallel R_\mathrm{L}}{R_1 + R_2 \parallel R_\mathrm{L}}
$$

Weil $R_2 \parallel R_\mathrm{L}$ immer kleiner als $R_2$ ist, sinkt $U_2$ unter die
Leerlaufspannung. Ein niederohmiger Teiler reagiert weniger empfindlich auf die Last,
braucht dafür aber einen größeren Querstrom.

![Ausgangsspannung zweier Teiler mit R1 = R2 an U0 = 10 V über dem Lastwiderstand; im Leerlauf liefern beide 5 V](fig:st-lastkennlinie)

Übungen: [Belasteter Spannungsteiler](ex:ex-st-belastet),
[Belasteter Teiler allgemein](ex:ex-st-belastet-allgemein)

## Ersatzspannungsquelle

::: definition
**Ersatzspannungsquelle**

Jede lineare Schaltung aus Quellen und Widerständen verhält sich an zwei Klemmen A und B
wie eine ideale Spannungsquelle $U_\mathrm{q}$ in Reihe mit einem Innenwiderstand
$R_\mathrm{i}$.
:::

![Ersatzspannungsquelle aus Uq und Ri mit dem Lastwiderstand RL an den Klemmen A und B](fig:st-ersatzquelle)

Die beiden Kenngrößen bestimmt man getrennt:

- **Leerlaufspannung:** Die Klemmen bleiben offen; die Spannung $U_\mathrm{AB}$ zwischen
  ihnen ist $U_\mathrm{q}$.
- **Innenwiderstand:** Ideale Spannungsquellen werden durch Kurzschlüsse, ideale
  Stromquellen durch Leerläufe ersetzt; der Widerstand zwischen A und B ist
  $R_\mathrm{i}$. Alternativ gilt $R_\mathrm{i} = U_\mathrm{q}/I_\mathrm{k}$ mit dem
  Kurzschlussstrom $I_\mathrm{k}$.

Für den Spannungsteiler mit den Klemmen an $R_2$ ergibt das
$U_\mathrm{q} = U_0 \cdot R_2/(R_1 + R_2)$ und $R_\mathrm{i} = R_1 \parallel R_2$. Eine Last
bildet mit dem Innenwiderstand einen einfachen Teiler. Für die Lastspannung, beim Teiler
also $U_2$, gilt:

$$
U_\mathrm{L} = U_\mathrm{q} \cdot \frac{R_\mathrm{L}}{R_\mathrm{i} + R_\mathrm{L}}
$$

::: example
**Beispiel**

Für $U_0 = 12\,\mathrm{V}$ und $R_1 = R_2 = 1\,\mathrm{k\Omega}$ ist
$U_\mathrm{q} = 6\,\mathrm{V}$ und $R_\mathrm{i} = 500\,\Omega$. Eine Last
$R_\mathrm{L} = 1\,\mathrm{k\Omega}$ erhält
$U_\mathrm{L} = 6\,\mathrm{V} \cdot 1000/1500 = 4\,\mathrm{V}$, genau wie mit
$R_2 \parallel R_\mathrm{L}$ gerechnet.
:::

::: note
**Leistungsanpassung**

Die Last nimmt die größte Leistung auf, wenn $R_\mathrm{L} = R_\mathrm{i}$ ist:

$$
P_\mathrm{max} = \frac{U_\mathrm{q}^2}{4 R_\mathrm{i}}
$$

Im Ersatzmodell wird dann in $R_\mathrm{i}$ genauso viel Leistung umgesetzt wie in der
Last. Einen Wirkungsgrad von $50\,\%$ hat aber nur eine Quelle, deren Verluste wirklich in
einem Innenwiderstand entstehen, etwa eine Batterie. Die Ersatzspannungsquelle gibt nur
das Verhalten an den Klemmen richtig wieder: Beim Teiler aus dem Beispiel setzen $R_1$ und
$R_2$ bei $R_\mathrm{L} = 500\,\Omega$ zusammen $90\,\mathrm{mW}$ um, die Last nur
$18\,\mathrm{mW}$. Der Wirkungsgrad beträgt dort also rund $17\,\%$.
:::

Übung: [Ersatzspannungsquelle eines Teilers](ex:ex-st-ersatzquelle)

::: takeaways
- Spannungsteiler: Die Teilspannungen verhalten sich wie die Widerstände, solange durch
  beide derselbe Strom fließt.
- Stromteiler: Die Teilströme verhalten sich umgekehrt wie die Widerstände.
- Eine Last parallel zu $R_2$ senkt $U_2$; man rechnet mit $R_2 \parallel R_\mathrm{L}$
  oder mit der Ersatzspannungsquelle.
- $U_\mathrm{q}$ ist die Leerlaufspannung, $R_\mathrm{i}$ der Widerstand an den Klemmen bei
  kurzgeschlossenen Spannungsquellen.
:::
