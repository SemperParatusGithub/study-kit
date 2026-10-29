# sk-file: summary/02-rc-filter.md

## Kästen mit Titel

Every box type with a title paragraph made of one bold span; titles may hold math.

::: definition
**Grenzfrequenz $f_\mathrm{g}$**

Bei $f_\mathrm{g} = \frac{1}{2\pi RC}$ gilt $|\underline{H}| = 1/\sqrt{2} \approx 0{,}707$.
:::

::: theorem
**Spannungsteilerregel**

$$
U_2 = U \frac{R_2}{R_1 + R_2}
$$
:::

::: example
**Zahlenbeispiel**

Mit $R = 1\,\mathrm{k\Omega}$ und $C = 100\,\mathrm{nF}$ ist $f_\mathrm{g} \approx 1{,}59\,\mathrm{kHz}$.

![Bode-Diagramm des Beispiels](fig:rc-bode)
:::

::: note
**Merke**

- $\tau = RC$
- nach $5\tau$ praktisch eingeschwungen
:::

::: warning
**Häufiger Fehler**

$\omega_\mathrm{g}$ und $f_\mathrm{g}$ unterscheiden sich um $2\pi$ ([VL 5, S. 14](src:vl-05#p=14)).
:::

::: takeaways
**Das Wichtigste**

1. Die Grenzfrequenz folgt aus $|\underline{Z}_C| = R$.
2. Oberhalb fällt der Betrag mit $20\,\mathrm{dB}$ pro Dekade.
:::

## Kästen ohne Titel

::: definition
Ohne Titelzeile: der Kasten heißt „Definition“.
:::

::: theorem
Ohne Titelzeile.
:::

::: example
Ohne Titelzeile.
:::

::: note
**Fett** am Anfang, aber nicht allein: kein Titel.
:::

::: warning
Ohne Titelzeile.
:::

::: takeaways
Ohne Titelzeile.
:::

## Fallunterscheidung und Dezimalkomma

$$
u_C(t) = \begin{cases} 0 & t < 0 \\ U_0 \left(1 - \mathrm{e}^{-t/\tau}\right) & t \geq 0 \end{cases}
$$

$$
\mathrm{sgn}(x) = \begin{cases} -1 & \text{für } x < 0 \\ 0{,}5 & \text{für } x = 0 \\ 1 & \text{sonst} \end{cases}
$$

| Größe | Wert |
|---|---|
| $R$ | $3{,}3\,\mathrm{k\Omega}$ |
| $C$ | $47\,\mathrm{nF}$ |

```python
tau = 3.3e3 * 47e-9
```

Verweise: [Übung](ex:ex-rc-tp-grenzfrequenz), [Thema](topic:gleichstrom),
[Frage](mc:mc-rc-filter-003), [Klausur](exam:probeklausur-1),
[Vorlesung](src:vl-05) und [extern](https://example.org).

# sk-file: exercises/rc-filter/ex-rc-tp-grenzfrequenz.md

Gegeben ist der RC-Tiefpass.

![RC-Tiefpass](fig:rc-tp-schaltung)

**a)** Bestimmen Sie $f_\mathrm{g}$.

**b)** Wie groß ist $|\underline{H}(f_\mathrm{g})|$ in dB?

::: hint
Prinzip: Wirk- und Blindwiderstand sind bei $f_\mathrm{g}$ betragsmäßig gleich.
:::

::: hint
Ansatz: $R = \frac{1}{2\pi f_\mathrm{g} C}$.
:::

::: hint
Zwischenergebnis: $RC = 0{,}1\,\mathrm{ms}$.
:::

::: solution
**a)** $f_\mathrm{g} = \frac{1}{2\pi RC} \approx 1{,}59\,\mathrm{kHz}$

**b)** $20\log_{10}\frac{1}{\sqrt{2}} \approx -3{,}01\,\mathrm{dB}$

![Bode-Diagramm mit markierter Grenzfrequenz](fig:rc-bode)
:::

# sk-file: exams/probeklausur-1/01-pk1-t1.md

Ein Spannungsteiler mit $R_1 = 2{,}2\,\mathrm{k\Omega}$ und $R_2 = 3{,}3\,\mathrm{k\Omega}$ liegt an $10\,\mathrm{V}$.

::: hint
Spannungsteilerregel.
:::

::: solution
$U_2 = 6\,\mathrm{V}$
:::

# sk-file: cheatsheet.md

## RC-Filter

::: definition
**Grenzfrequenz**

$f_\mathrm{g} = \frac{1}{2\pi RC}$
:::

::: note
$\tau = RC$
:::

::: warning
$\omega_\mathrm{g} = 2\pi f_\mathrm{g}$
:::

# sk-file: overview.md

## Worum geht es?

RC-Netzwerke.

## Themenkarte

![Themen und ihre Abhängigkeiten](fig:topic-map)
