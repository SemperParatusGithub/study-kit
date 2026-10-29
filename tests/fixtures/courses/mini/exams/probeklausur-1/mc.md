---
title: Probeklausur 1, MC-Teil
---

:::: {.mcq #mc-spannungsteiler-101 type="single" difficulty="1"}
Zwei gleiche Widerstände teilen $U = 10\,\mathrm{V}$. Wie groß ist die Teilspannung?

- [x] $5\,\mathrm{V}$

  Gleiche Widerstände, gleiche Spannungen.

- [ ] $10\,\mathrm{V}$

  Gesamtspannung statt Teilspannung genommen.

- [ ] $2{,}5\,\mathrm{V}$

  Zweimal halbiert.

::: explanation
Nach der Teilerregel ist $U_2 = U \cdot R/(2R) = U/2$.
:::
::::

:::: {.mcq #mc-rc-tiefpass-101 type="multi" difficulty="2"}
Welche Größen bestimmen die Grenzfrequenz eines RC-Tiefpasses?

- [x] Der Widerstand $R$.

  $f_\mathrm{g}$ hängt von $RC$ ab.

- [x] Die Kapazität $C$.

  $f_\mathrm{g}$ hängt von $RC$ ab.

- [ ] Die Eingangsamplitude.

  Das System ist linear, die Amplitude skaliert nur.

- [ ] Die Phase des Eingangssignals.

  Eine Phasenverschiebung des Eingangs ändert $\underline{H}$ nicht.

::: explanation
Es gilt $f_\mathrm{g} = 1/(2\pi RC)$, nur das Produkt $RC$ zählt.
:::
::::

:::: {.mcq #mc-rc-tiefpass-102 type="kprim" difficulty="3"}
Beurteilen Sie für den RC-Tiefpass mit $\underline{H} = 1/(1 + \mathrm{j}\omega RC)$:

- [x] Für $\omega \to \infty$ geht die Phase gegen $-90^\circ$.

  Der Imaginärteil dominiert den Nenner.

- [ ] Für $\omega \to 0$ geht die Phase gegen $-90^\circ$.

  Für kleine Frequenzen ist $\underline{H} \approx 1$.

- [x] Bei $\omega = 1/(RC)$ ist $|\underline{H}| = 1/\sqrt{2}$.

  Real- und Imaginärteil des Nenners sind gleich.

- [ ] Der Betrag steigt oberhalb von $\omega = 1/(RC)$.

  Tiefpass: der Betrag fällt.

::: explanation
Die Phase ist $-\arctan(\omega RC)$ und läuft von $0^\circ$ nach $-90^\circ$.
:::
::::
