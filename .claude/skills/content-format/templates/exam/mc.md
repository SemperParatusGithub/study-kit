---
title: Probeklausur 2, MC-Teil
---

:::: {.mcq #mc-rc-filter-201 type="single" difficulty="1"}
Welchen Betrag hat die Übertragungsfunktion eines RC-Tiefpasses bei der Grenzfrequenz?

- [ ] $0{,}5$

  Das wäre $-6\,\mathrm{dB}$; bei $f_\mathrm{g}$ sind es $-3\,\mathrm{dB}$.

- [ ] $1$

  Das ist der Grenzwert im Durchlassbereich für $f \to 0$.

- [x] $1/\sqrt{2}$

  $|\underline{H}| = 1/\sqrt{1 + 1}$ bei $\omega RC = 1$.

::: explanation
Bei $f_\mathrm{g}$ ist $|1 + \mathrm{j}| = \sqrt{2}$, also $-3\,\mathrm{dB}$.
:::
::::

:::: {.mcq #mc-rc-filter-202 type="single" difficulty="2"}
Welche Phase hat die Übertragungsfunktion eines RC-Hochpasses bei der Grenzfrequenz?

- [ ] $-45^\circ$

  Vorzeichen verwechselt: Das gilt für den Tiefpass.

- [x] $+45^\circ$

  $\arg(\mathrm{j}/(1 + \mathrm{j})) = 90^\circ - 45^\circ$.

- [ ] $+90^\circ$

  Das ist der Grenzwert für $f \to 0$.

::: explanation
Der Zähler $\mathrm{j}\omega RC$ trägt $+90^\circ$ bei, der Nenner bei $f_\mathrm{g}$
$-45^\circ$.
:::
::::
