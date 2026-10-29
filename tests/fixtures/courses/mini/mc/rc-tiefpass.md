---
topic: rc-tiefpass
title: RC-Tiefpass
---

:::: {.mcq #mc-rc-tiefpass-001 type="single" difficulty="1" source="ue-02:2"}
Ein RC-Tiefpass hat $R = 1\,\mathrm{k\Omega}$ und $C = 100\,\mathrm{nF}$. Wie groß ist $f_\mathrm{g}$?

- [x] $1{,}59\,\mathrm{kHz}$

  $f_\mathrm{g} = 1/(2\pi RC)$.

- [ ] $10\,\mathrm{kHz}$

  Das ist $1/(RC)$, also $\omega_\mathrm{g}$: Faktor $2\pi$ vergessen.

- [ ] $159\,\mathrm{Hz}$

  Zehnerpotenz falsch: mit $C = 1\,\mathrm{\mu F}$ gerechnet.

- [ ] $62{,}8\,\mathrm{kHz}$

  $2\pi/(RC)$ statt $1/(2\pi RC)$.

::: explanation
Bei $f_\mathrm{g}$ gilt $|\underline{Z}_C| = R$, also $2\pi f_\mathrm{g} RC = 1$.
:::
::::

:::: {.mcq #mc-rc-tiefpass-002 type="multi" difficulty="2" pin-last="true" tags="bode,phase"}
Welche Aussagen gelten für den RC-Tiefpass erster Ordnung?

- [x] Oberhalb von $f_\mathrm{g}$ fällt der Betrag mit $20\,\mathrm{dB}$ pro Dekade.

  Ein Pol erster Ordnung.

- [x] Bei $f_\mathrm{g}$ beträgt die Phase $-45^\circ$.

  $\arg\underline{H} = -\arctan 1$.

- [ ] Bei $f_\mathrm{g}$ beträgt die Phase $-90^\circ$.

  Verwechslung mit der Phase für $f \to \infty$.

- [ ] Keine der Aussagen ist richtig.

  Die ersten beiden Aussagen sind richtig.

::: explanation
Ein Pol bei $\omega_\mathrm{g} = 1/(RC)$ gibt $-20\,\mathrm{dB}$ pro Dekade und $-45^\circ$ bei $f_\mathrm{g}$.
:::
::::

:::: {.mcq #mc-rc-tiefpass-003 type="kprim" difficulty="2"}
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
Betrag und Phase folgen aus $\underline{H} = 1/(1 + \mathrm{j} f/f_\mathrm{g})$.
:::
::::
