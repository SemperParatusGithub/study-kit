---
topic: rc-filter
title: RC-Filter und Bode-Diagramm
---

:::: {.mcq #mc-rc-filter-003 type="single" difficulty="1" source="uebung-04:2"}
Ein RC-Tiefpass hat $R = 1\,\mathrm{k\Omega}$ und $C = 100\,\mathrm{nF}$. Wie groß ist $f_\mathrm{g}$?

- [x] $1{,}59\,\mathrm{kHz}$

  $f_\mathrm{g} = 1/(2\pi RC)$.

- [ ] $10\,\mathrm{kHz}$

  Das ist $1/(RC)$, also $\omega_\mathrm{g}$ in $\mathrm{s^{-1}}$: Faktor $2\pi$ vergessen.

- [ ] $159\,\mathrm{Hz}$

  Zehnerpotenz falsch: mit $C = 1\,\mathrm{\mu F}$ gerechnet.

- [ ] $62{,}8\,\mathrm{kHz}$

  $2\pi/(RC)$ statt $1/(2\pi RC)$.

::: explanation
Bei $f_\mathrm{g}$ gilt $|\underline{Z}_C| = R$, also $2\pi f_\mathrm{g} RC = 1$.
:::
::::

:::: {.mcq #mc-rc-filter-011 type="multi" difficulty="2" pin-last="true"}
Welche Aussagen gelten für den RC-Tiefpass erster Ordnung?

- [x] Oberhalb von $f_\mathrm{g}$ fällt der Betrag mit $20\,\mathrm{dB}$ pro Dekade.

  Ein Pol erster Ordnung.

- [ ] Bei $f_\mathrm{g}$ beträgt die Phase $-90^\circ$.

  Bei $f_\mathrm{g}$ ist $\arg\underline{H} = -\arctan 1 = -45^\circ$.

- [x] Für $f \to 0$ gilt $|\underline{H}| \to 1$.

  Der Kondensator sperrt den Gleichanteil nicht ab.

- [ ] Keine der Aussagen ist richtig.

  Die erste Aussage ist richtig.

::: explanation
Die Grenzfrequenz trennt Durchlass- und Sperrbereich; siehe [die erste Frage](mc:mc-rc-filter-003).
:::
::::

:::: {.mcq #mc-rc-filter-020 type="kprim" difficulty="2"}
Beurteilen Sie für den RC-Tiefpass:

- [x] Bei $f = f_\mathrm{g}$ gilt $|\underline{H}| = 1/\sqrt{2}$.

  Definition der Grenzfrequenz.

- [x] Bei $f = f_\mathrm{g}$ beträgt die Phase $-45^\circ$.

  $\arg\underline{H} = -\arctan(1)$.

- [ ] Für $f \gg f_\mathrm{g}$ fällt $|\underline{H}|$ mit $40\,\mathrm{dB}$ pro Dekade.

  Erste Ordnung: $20\,\mathrm{dB}$ pro Dekade.

- [ ] Für $f \to 0$ gilt $|\underline{H}| \to 0$.

  Der Gleichanteil wird durchgelassen: $|\underline{H}| \to 1$.

::: explanation
$$
\underline{H}(\mathrm{j}\omega) = \frac{1}{1 + \mathrm{j}\omega RC}
$$
:::
::::
