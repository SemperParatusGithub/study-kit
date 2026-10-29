---
topic: rc-filter
title: RC-Filter und Bode-Diagramm
---

:::: {.mcq #mc-rc-filter-001 type="single" difficulty="1"}
Ein RC-Tiefpass hat $R = 3{,}3\,\mathrm{k\Omega}$ und $C = 10\,\mathrm{nF}$. Wie groß ist
seine Grenzfrequenz $f_\mathrm{g}$?

- [ ] $30{,}3\,\mathrm{kHz}$

  Das ist $1/(RC)$, also $\omega_\mathrm{g}$ in $\mathrm{s^{-1}}$: Faktor $2\pi$ vergessen.

- [ ] $482\,\mathrm{Hz}$

  Zehnerpotenz falsch: mit $C = 100\,\mathrm{nF}$ gerechnet.

- [x] $4{,}82\,\mathrm{kHz}$

  $f_\mathrm{g} = 1/(2\pi RC)$.

- [ ] $190\,\mathrm{kHz}$

  $2\pi/(RC)$: mit $2\pi$ multipliziert statt dividiert.

::: explanation
Bei $f_\mathrm{g}$ ist $|\underline{Z}_C| = R$, also $2\pi f_\mathrm{g} RC = 1$. Mit
$RC = 33\,\mathrm{\mu s}$ ergibt das $f_\mathrm{g} \approx 4{,}82\,\mathrm{kHz}$.
:::
::::

:::: {.mcq #mc-rc-filter-002 type="multi" difficulty="2" pin-last="true"}
Welche Aussagen gelten für den unbelasteten RC-Tiefpass erster Ordnung?

- [ ] Für $f \to 0$ wirkt der Kondensator wie ein Kurzschluss.

  Falsch: Bei tiefen Frequenzen wirkt er wie ein Leerlauf; deshalb gilt $|\underline{H}| \to 1$.

- [x] Oberhalb von $f_\mathrm{g}$ fällt der Betrag mit $20\,\mathrm{dB}$ pro Dekade.

  Ein Pol erster Ordnung.

- [ ] Die Grenzfrequenz hängt von der Amplitude der Eingangsspannung ab.

  Falsch: Das System ist linear; $f_\mathrm{g}$ hängt nur von $R$ und $C$ ab.

- [x] Bei $f_\mathrm{g}$ eilt die Ausgangsspannung der Eingangsspannung um $45^\circ$ nach.

  $\varphi = -\arctan 1 = -45^\circ$.

- [ ] Keine der Aussagen ist richtig.

  Zwei der Aussagen sind richtig.

::: explanation
$\underline{H} = 1/(1 + \mathrm{j}f/f_\mathrm{g})$: Der Betrag fällt oberhalb von $f_\mathrm{g}$
mit $20\,\mathrm{dB}$ pro Dekade, die Phase läuft von $0^\circ$ über $-45^\circ$ nach
$-90^\circ$.
:::
::::

:::: {.mcq #mc-rc-filter-003 type="kprim" difficulty="2"}
Beurteilen Sie die Aussagen zum unbelasteten RC-Hochpass.

- [ ] Für $f \to 0$ gilt $|\underline{H}| \to 1$.

  Falsch: Der Kondensator im Längszweig sperrt Gleichspannung, also $|\underline{H}| \to 0$.

- [x] Es gilt $\underline{H}(\mathrm{j}\omega) = \mathrm{j}\omega RC/(1 + \mathrm{j}\omega RC)$.

  Richtig: Spannungsteiler mit $R$ im Querzweig.

- [x] Unterhalb von $f_\mathrm{g}$ steigt $|\underline{H}|$ mit $20\,\mathrm{dB}$ pro Dekade.

  Richtig: Der Zähler $\mathrm{j}\omega RC$ wächst proportional zur Frequenz.

- [ ] Die Grenzfrequenz ist $f_\mathrm{g} = 2\pi RC$.

  Falsch: $f_\mathrm{g} = 1/(2\pi RC)$; $2\pi RC$ hat die Einheit einer Zeit.

::: explanation
Hoch- und Tiefpass aus denselben Bauteilen haben dieselbe Grenzfrequenz. Der Hochpass
lässt hohe Frequenzen durch und dämpft tiefe mit $20\,\mathrm{dB}$ pro Dekade.
:::
::::
