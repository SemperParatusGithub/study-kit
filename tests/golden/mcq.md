# sk-file: mc/rc-filter.md

:::: {.mcq #mc-rc-filter-101 type="single" difficulty="1"}
Single choice with three options: welche Einheit hat $\tau = RC$?

- [ ] $\mathrm{\Omega}$

  Nur die Einheit von $R$.

- [x] $\mathrm{s}$

  $\mathrm{\Omega} \cdot \mathrm{F} = \mathrm{s}$.

- [ ] $\mathrm{Hz}$

  Kehrwert: $1/\tau$ hat die Einheit $\mathrm{s^{-1}}$.

::: explanation
Die Zeitkonstante ist eine Zeit.
:::
::::

:::: {.mcq #mc-rc-filter-102 type="single" difficulty="2" source="vl-05:14" tags="grenzfrequenz,rechnen"}
Single choice with five options: $R = 1\,\mathrm{k\Omega}$, $C = 100\,\mathrm{nF}$. Wie groß ist $f_\mathrm{g}$?

- [x] $1{,}59\,\mathrm{kHz}$

  $f_\mathrm{g} = 1/(2\pi RC)$.

- [ ] $10\,\mathrm{kHz}$

  $1/(RC)$: Faktor $2\pi$ vergessen.

- [ ] $159\,\mathrm{Hz}$

  Zehnerpotenz falsch.

- [ ] $62{,}8\,\mathrm{kHz}$

  $2\pi/(RC)$ statt $1/(2\pi RC)$.

- [ ] $1{,}13\,\mathrm{kHz}$

  Durch $\sqrt{2}$ geteilt: Effektivwert mit Amplitude verwechselt.

::: explanation
$$
f_\mathrm{g} = \frac{1}{2\pi \cdot 1\,\mathrm{k\Omega} \cdot 100\,\mathrm{nF}} \approx 1{,}59\,\mathrm{kHz}
$$
:::
::::

:::: {.mcq #mc-rc-filter-103 type="multi" difficulty="2" pin-last="true"}
Multi with four options and a pinned last option. Welche Aussagen gelten?

- [x] Oberhalb von $f_\mathrm{g}$ fällt der Betrag mit $20\,\mathrm{dB}$ pro Dekade.

  Ein Pol erster Ordnung.

- [ ] Bei $f_\mathrm{g}$ beträgt die Phase $-90^\circ$.

  Es sind $-45^\circ$.

- [x] Für $f \to 0$ gilt $|\underline{H}| \to 1$.

  Gleichanteil wird durchgelassen.

- [ ] Keine der Aussagen ist richtig.

  Zwei Aussagen sind richtig.

::: explanation
Siehe [die Rechenaufgabe](mc:mc-rc-filter-102) und [das Thema](topic:rc-filter).
:::
::::

:::: {.mcq #mc-rc-filter-104 type="multi" difficulty="3"}
Multi with six options, one of them a figure: welche Bauteile speichern Energie?

- [x] Kondensator

  Im elektrischen Feld: $W = \frac{1}{2} C U^2$.

- [x] Spule

  Im magnetischen Feld.

- [ ] Ohmscher Widerstand

  Wandelt Energie in Wärme um.

- [ ] Ideale Spannungsquelle

  Liefert Energie, speichert sie nicht.

- [ ] Ideale Diode

  Kein Speicher.

- [ ] ![Das Bode-Diagramm](fig:rc-bode)

  Ein Diagramm ist kein Bauteil.

::: explanation
Speicher sind $L$ und $C$.
:::
::::

:::: {.mcq #mc-rc-filter-105 type="kprim" difficulty="2"}
Kprim: beurteilen Sie für den RC-Tiefpass.

- [x] Bei $f = f_\mathrm{g}$ gilt $|\underline{H}| = 1/\sqrt{2}$.

  Definition der Grenzfrequenz.

- [x] Bei $f = f_\mathrm{g}$ beträgt die Phase $-45^\circ$.

  $\arg\underline{H} = -\arctan(1)$.

- [ ] Für $f \gg f_\mathrm{g}$ fällt $|\underline{H}|$ mit $40\,\mathrm{dB}$ pro Dekade.

  Erste Ordnung: $20\,\mathrm{dB}$ pro Dekade.

- [ ] Für $f \to 0$ gilt $|\underline{H}| \to 0$.

  Der Gleichanteil wird durchgelassen.

::: explanation
$$
\underline{H}(\mathrm{j}\omega) = \frac{1}{1 + \mathrm{j}\omega RC}, \qquad \varphi(\omega) = -\arctan(\omega RC)
$$
:::
::::

:::: {.mcq #mc-rc-filter-106 type="kprim" difficulty="4"}
Kprim with all statements true: $u(t) = \begin{cases} 0 & t < 0 \\ 1{,}5\,\mathrm{V} & t \geq 0 \end{cases}$.

- [x] $u$ springt bei $t = 0$.

  Sprungfunktion.

- [x] $u(1\,\mathrm{s}) = 1{,}5\,\mathrm{V}$.

  Zweiter Fall.

- [x] $u(-1\,\mathrm{s}) = 0$.

  Erster Fall.

- [x] $u$ ist beschränkt.

  $|u| \leq 1{,}5\,\mathrm{V}$.

::: explanation
Alle vier Aussagen folgen direkt aus der Fallunterscheidung.
:::
::::

# sk-file: exams/probeklausur-1/mc.md

:::: {.mcq #pk1-mc-01 type="single" difficulty="1"}
Exam question: welche Einheit hat die Kapazität?

- [x] $\mathrm{F}$

  Farad.

- [ ] $\mathrm{H}$

  Henry ist die Einheit der Induktivität.

- [ ] $\mathrm{S}$

  Siemens ist die Einheit des Leitwerts.

::: explanation
$C = Q/U$, also $\mathrm{A\,s/V} = \mathrm{F}$.
:::
::::
