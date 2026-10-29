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

:::: {.mcq #mc-rc-filter-002 type="single" difficulty="1"}
Welchen Betrag hat die Übertragungsfunktion eines RC-Tiefpasses bei der Grenzfrequenz?

- [ ] $0{,}5$

  Das wäre $-6\,\mathrm{dB}$; bei $f_\mathrm{g}$ sind es $-3\,\mathrm{dB}$.

- [ ] $1$

  Das ist der Grenzwert im Durchlassbereich für $f \to 0$.

- [ ] $0{,}1$

  So klein wird der Betrag erst eine Dekade oberhalb von $f_\mathrm{g}$.

- [x] $1/\sqrt{2}$

  $|\underline{H}| = 1/\sqrt{1 + 1}$ bei $\omega RC = 1$.

::: explanation
Bei $f_\mathrm{g}$ sind Real- und Imaginärteil des Nenners gleich groß:
$|1 + \mathrm{j}| = \sqrt{2}$. Das entspricht $20\lg(1/\sqrt{2}) \approx -3\,\mathrm{dB}$.
:::
::::

:::: {.mcq #mc-rc-filter-003 type="single" difficulty="2"}
Welche Phase hat die Übertragungsfunktion eines RC-Hochpasses bei der Grenzfrequenz?

- [ ] $-45^\circ$

  Vorzeichen verwechselt: Das gilt für den Tiefpass.

- [x] $+45^\circ$

  $\arg(\mathrm{j}/(1 + \mathrm{j})) = 90^\circ - 45^\circ$.

- [ ] $+90^\circ$

  Das ist der Grenzwert für $f \to 0$.

- [ ] $0^\circ$

  Das ist der Grenzwert für $f \to \infty$.

::: explanation
Der Hochpass hat den Zähler $\mathrm{j}\omega RC$ mit $+90^\circ$. Der Nenner trägt bei
$f_\mathrm{g}$ $-45^\circ$ bei, zusammen also $+45^\circ$.
:::
::::

:::: {.mcq #mc-rc-filter-004 type="single" difficulty="2"}
Ein RC-Tiefpass hat $f_\mathrm{g} = 2\,\mathrm{kHz}$. Wie groß ist der Betrag von
$\underline{H}$ bei $f = 20\,\mathrm{kHz}$ ungefähr?

- [x] $-20\,\mathrm{dB}$

  Eine Dekade über $f_\mathrm{g}$, Steigung $20\,\mathrm{dB}$ pro Dekade.

- [ ] $-40\,\mathrm{dB}$

  Steigung $40\,\mathrm{dB}$ pro Dekade: Das gilt erst für ein Filter zweiter Ordnung.

- [ ] $-3\,\mathrm{dB}$

  Das ist der Wert bei $f_\mathrm{g}$, nicht eine Dekade darüber.

- [ ] $-10\,\mathrm{dB}$

  Mit $10\lg$ statt $20\lg$ gerechnet: Leistungs- statt Amplitudenmaß.

::: explanation
Exakt ist $|\underline{H}| = 1/\sqrt{1 + 10^2} \approx 0{,}0995$, also
$-20{,}04\,\mathrm{dB}$. Die Asymptote liefert $-20\,\mathrm{dB}$.
:::
::::

:::: {.mcq #mc-rc-filter-005 type="single" difficulty="2"}
Ein ungeladener Kondensator $C = 10\,\mathrm{\mu F}$ wird über $R = 10\,\mathrm{k\Omega}$
an $U_0 = 10\,\mathrm{V}$ geladen. Welche Spannung hat er nach $t = 100\,\mathrm{ms}$?

- [ ] $3{,}68\,\mathrm{V}$

  $U_0\,\mathrm{e}^{-1}$: Das ist die Entladekurve, nicht die Ladekurve.

- [ ] $5\,\mathrm{V}$

  Angenommen, nach $\tau$ sei die Hälfte erreicht; das ist erst nach $\tau \ln 2$ der Fall.

- [x] $6{,}32\,\mathrm{V}$

  $\tau = RC = 100\,\mathrm{ms}$, also $U_0\,(1 - \mathrm{e}^{-1})$.

- [ ] $10\,\mathrm{V}$

  Nach einer Zeitkonstante ist der Kondensator noch nicht voll geladen.

::: explanation
Nach $t = \tau$ hat der Kondensator $63{,}2\,\%$ der Endspannung erreicht; praktisch voll
geladen ist er erst nach etwa $5\tau$.
:::
::::

:::: {.mcq #mc-rc-filter-006 type="single" difficulty="3"}
Ein RC-Tiefpass wird am Ausgang mit $R_\mathrm{L} = R$ belastet. Wie ändert sich seine
Grenzfrequenz?

- [ ] Sie halbiert sich.

  Die Last als Widerstand in Reihe zu $R$ gedeutet; sie liegt aber parallel zu $C$.

- [ ] Sie bleibt gleich, nur die Verstärkung sinkt.

  Die Verstärkung sinkt tatsächlich, aber der wirksame Widerstand vor $C$ ändert sich auch.

- [x] Sie verdoppelt sich.

  $\tau' = (R \parallel R)\,C = RC/2$.

- [ ] Sie steigt um den Faktor $\sqrt{2}$.

  $\sqrt{2}$ gehört zum Betrag bei $f_\mathrm{g}$, nicht zur Verschiebung der Frequenz.

::: explanation
Von den Kondensatorklemmen aus gesehen ist der Innenwiderstand $R \parallel R_\mathrm{L}$.
Mit $R_\mathrm{L} = R$ halbiert sich die Zeitkonstante, und $f_\mathrm{g}$ verdoppelt sich.
:::
::::

:::: {.mcq #mc-rc-filter-007 type="multi" difficulty="2" pin-last="true"}
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

:::: {.mcq #mc-rc-filter-008 type="multi" difficulty="3"}
Ein unbelasteter RC-Tiefpass mit $\tau = RC$ wird mit einem Spannungssprung der Höhe $U_0$
angeregt; der Kondensator ist anfangs ungeladen. Welche Aussagen über $u_C(t)$ sind
richtig?

- [x] Nach $t = \tau$ hat $u_C$ rund $63\,\%$ von $U_0$ erreicht.

  $1 - \mathrm{e}^{-1} \approx 0{,}632$.

- [ ] Nach $t = 2\tau$ ist der Kondensator vollständig geladen.

  Falsch: Nach $2\tau$ sind es erst $86{,}5\,\%$; praktisch voll ist er nach etwa $5\tau$.

- [ ] Der Ladestrom ist bei $t = 0$ null und steigt dann an.

  Falsch: $i(0) = U_0/R$ ist der größte Wert; danach fällt der Strom exponentiell.

- [x] Die Tangente an $u_C(t)$ im Ursprung erreicht den Endwert $U_0$ bei $t = \tau$.

  Die Anfangssteigung ist $U_0/\tau$.

::: explanation
$u_C(t) = U_0(1 - \mathrm{e}^{-t/\tau})$ und $i(t) = (U_0/R)\,\mathrm{e}^{-t/\tau}$. Mit der
Tangentenregel liest man $\tau$ aus einem gemessenen Verlauf ab.
:::
::::

:::: {.mcq #mc-rc-filter-009 type="kprim" difficulty="2"}
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

:::: {.mcq #mc-rc-filter-010 type="kprim" difficulty="3"}
Ein unbelasteter RC-Tiefpass hat $R = 1\,\mathrm{k\Omega}$ und $C = 1\,\mathrm{\mu F}$.
Beurteilen Sie die Aussagen.

- [x] Die Zeitkonstante beträgt $\tau = 1\,\mathrm{ms}$.

  $RC = 10^3\,\Omega \cdot 10^{-6}\,\mathrm{F}$.

- [ ] Die Grenzfrequenz beträgt $f_\mathrm{g} = 1\,\mathrm{kHz}$.

  Falsch: $\omega_\mathrm{g}$ mit $f_\mathrm{g}$ verwechselt; $f_\mathrm{g} = 1/(2\pi\tau) \approx 159\,\mathrm{Hz}$.

- [ ] Bei $f = 159\,\mathrm{Hz}$ beträgt die Phase $-90^\circ$.

  Falsch: $159\,\mathrm{Hz}$ ist $f_\mathrm{g}$, dort beträgt die Phase $-45^\circ$.

- [x] Die Grenzkreisfrequenz beträgt $\omega_\mathrm{g} = 1000\,\mathrm{s^{-1}}$.

  $\omega_\mathrm{g} = 1/\tau$.

::: explanation
$\tau = 1\,\mathrm{ms}$, $\omega_\mathrm{g} = 1/\tau = 1000\,\mathrm{s^{-1}}$ und
$f_\mathrm{g} = \omega_\mathrm{g}/(2\pi) \approx 159\,\mathrm{Hz}$. Bei $f_\mathrm{g}$ ist die
Phase $-45^\circ$; $-90^\circ$ erreicht sie erst für $f \to \infty$.
:::
::::
