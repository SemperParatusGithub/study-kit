---
title: Probeklausur 1, MC-Teil
---

:::: {.mcq #mc-spannungsteiler-101 type="single" difficulty="1"}
Drei gleiche Widerstände $R$ liegen in Reihe an $U_0 = 9\,\mathrm{V}$. Welche Spannung liegt
an einem von ihnen?

- [ ] $4{,}5\,\mathrm{V}$

  Die Spannung auf zwei statt auf drei Widerstände verteilt.

- [x] $3\,\mathrm{V}$

  Gleiche Widerstände, gleiche Teilspannungen: $9\,\mathrm{V}/3$.

- [ ] $9\,\mathrm{V}$

  Gesamtspannung statt Teilspannung genommen.

- [ ] $27\,\mathrm{V}$

  Multipliziert statt geteilt; eine Teilspannung kann nie größer als $U_0$ sein.

::: explanation
Durch alle drei Widerstände fließt derselbe Strom, also fällt an jedem dieselbe Spannung
$U_0/3 = 3\,\mathrm{V}$ ab.
:::
::::

:::: {.mcq #mc-spannungsteiler-102 type="single" difficulty="2"}
Eine reale Spannungsquelle liefert im Leerlauf $6\,\mathrm{V}$ und im Kurzschluss
$3\,\mathrm{A}$. Wie groß ist ihr Innenwiderstand?

- [ ] $0{,}5\,\Omega$

  Kehrwert gebildet: $I_\mathrm{k}/U_\mathrm{q}$ statt $U_\mathrm{q}/I_\mathrm{k}$.

- [ ] $18\,\Omega$

  Produkt $U_\mathrm{q} \cdot I_\mathrm{k}$ berechnet; das hat die Einheit einer Leistung.

- [x] $2\,\Omega$

  $R_\mathrm{i} = U_\mathrm{q}/I_\mathrm{k} = 6\,\mathrm{V}/3\,\mathrm{A}$.

::: explanation
Im Kurzschluss liegt die ganze Leerlaufspannung am Innenwiderstand. Daher gilt
$R_\mathrm{i} = U_\mathrm{q}/I_\mathrm{k}$.
:::
::::

:::: {.mcq #mc-spannungsteiler-103 type="kprim" difficulty="2"}
Eine Ersatzspannungsquelle hat $U_\mathrm{q} = 12\,\mathrm{V}$ und
$R_\mathrm{i} = 4\,\Omega$. Beurteilen Sie die Aussagen.

- [x] Der Kurzschlussstrom beträgt $3\,\mathrm{A}$.

  $I_\mathrm{k} = U_\mathrm{q}/R_\mathrm{i}$.

- [ ] An einer Last $R_\mathrm{L} = 4\,\Omega$ liegen $12\,\mathrm{V}$.

  Falsch: $R_\mathrm{i}$ und $R_\mathrm{L}$ teilen die Spannung je zur Hälfte, also
  $6\,\mathrm{V}$.

- [ ] Im Leerlauf beträgt die Klemmenspannung $0\,\mathrm{V}$.

  Falsch: Im Leerlauf fließt kein Strom; die Klemmenspannung ist $U_\mathrm{q}$.

- [x] Die größte Leistung, die eine Last aufnehmen kann, beträgt $9\,\mathrm{W}$.

  $U_\mathrm{q}^2/(4R_\mathrm{i}) = 144\,\mathrm{V^2}/16\,\Omega$.

::: explanation
Leerlaufspannung $U_\mathrm{q}$, Kurzschlussstrom $U_\mathrm{q}/R_\mathrm{i}$ und
Leistungsanpassung bei $R_\mathrm{L} = R_\mathrm{i}$ beschreiben die Quelle vollständig.
:::
::::

:::: {.mcq #mc-wechselstrom-101 type="single" difficulty="1"}
Gegeben ist $u(t) = 10\,\mathrm{V} \cdot \cos(1000\,\mathrm{s^{-1}} \cdot t)$. Welche
Frequenz hat die Spannung?

- [ ] $1\,\mathrm{kHz}$

  $\omega$ mit $f$ verwechselt.

- [ ] $6{,}28\,\mathrm{kHz}$

  Mit $2\pi$ multipliziert statt dividiert.

- [ ] $318\,\mathrm{Hz}$

  Durch $\pi$ statt durch $2\pi$ geteilt.

- [x] $159\,\mathrm{Hz}$

  $f = \omega/(2\pi)$.

::: explanation
Im Argument steht die Kreisfrequenz $\omega = 2\pi f$. Hier ist
$f = 1000/(2\pi)\,\mathrm{Hz} \approx 159\,\mathrm{Hz}$.
:::
::::

:::: {.mcq #mc-wechselstrom-102 type="single" difficulty="2"}
Eine Spule mit $L = 50\,\mathrm{mH}$ liegt in Reihe mit $R = 20\,\Omega$. Bei welcher
Frequenz ist $\omega L = R$?

- [x] $63{,}7\,\mathrm{Hz}$

  $f = R/(2\pi L)$.

- [ ] $400\,\mathrm{Hz}$

  $R/L$ ist die Kreisfrequenz in $\mathrm{s^{-1}}$: Faktor $2\pi$ vergessen.

- [ ] $2{,}51\,\mathrm{kHz}$

  Mit $2\pi$ multipliziert statt dividiert.

::: explanation
Aus $2\pi f L = R$ folgt $f = 20\,\Omega/(2\pi \cdot 50\,\mathrm{mH}) \approx 63{,}7\,\mathrm{Hz}$.
Dort beträgt der Phasenwinkel der Reihenschaltung $45^\circ$.
:::
::::

:::: {.mcq #mc-wechselstrom-103 type="multi" difficulty="2"}
Welche Zweipole haben bei $f = 50\,\mathrm{Hz}$ eine Impedanz mit negativem Imaginärteil?

- [ ] Eine ideale Spule

  Ihr Imaginärteil $\omega L$ ist positiv.

- [x] Ein idealer Kondensator

  $\underline{Z}_C = -\mathrm{j}/(\omega C)$.

- [ ] Ein ohmscher Widerstand

  Sein Imaginärteil ist null.

- [x] Eine Reihenschaltung aus Widerstand und Kondensator

  $\underline{Z} = R - \mathrm{j}/(\omega C)$.

::: explanation
Ein negativer Imaginärteil bedeutet kapazitives Verhalten: Die Spannung eilt dem Strom
nach. Spulen und Widerstände tragen dazu nichts Negatives bei.
:::
::::

:::: {.mcq #mc-rc-filter-101 type="single" difficulty="1"}
Ein RC-Tiefpass hat die Zeitkonstante $\tau = 0{,}5\,\mathrm{ms}$. Wie groß ist seine
Grenzfrequenz?

- [ ] $2\,\mathrm{kHz}$

  $1/\tau$ ist $\omega_\mathrm{g}$ in $\mathrm{s^{-1}}$: Faktor $2\pi$ vergessen.

- [x] $318\,\mathrm{Hz}$

  $f_\mathrm{g} = 1/(2\pi\tau)$.

- [ ] $12{,}6\,\mathrm{kHz}$

  $2\pi/\tau$: mit $2\pi$ multipliziert statt dividiert.

- [ ] $31{,}8\,\mathrm{Hz}$

  Zehnerpotenz falsch: mit $\tau = 5\,\mathrm{ms}$ gerechnet.

::: explanation
$\omega_\mathrm{g} = 1/\tau = 2000\,\mathrm{s^{-1}}$ und
$f_\mathrm{g} = \omega_\mathrm{g}/(2\pi) \approx 318\,\mathrm{Hz}$.
:::
::::

:::: {.mcq #mc-rc-filter-102 type="single" difficulty="2"}
Ein RC-Hochpass hat $f_\mathrm{g} = 1\,\mathrm{kHz}$. Wie groß ist der Betrag von
$\underline{H}$ bei $f = 100\,\mathrm{Hz}$ ungefähr?

- [ ] $+20\,\mathrm{dB}$

  Vorzeichen falsch: Ein passives RC-Filter verstärkt nicht.

- [ ] $-3\,\mathrm{dB}$

  Das ist der Wert bei $f_\mathrm{g}$, nicht eine Dekade darunter.

- [ ] $0\,\mathrm{dB}$

  Hoch- mit Tiefpass verwechselt: Der Hochpass sperrt tiefe Frequenzen.

- [x] $-20\,\mathrm{dB}$

  Eine Dekade unter $f_\mathrm{g}$, Steigung $20\,\mathrm{dB}$ pro Dekade.

::: explanation
Exakt gilt mit $x = 0{,}1$: $|\underline{H}| = x/\sqrt{1 + x^2} \approx 0{,}0995$, also
$-20{,}04\,\mathrm{dB}$.
:::
::::

:::: {.mcq #mc-rc-filter-103 type="multi" difficulty="2"}
Welche Änderungen verdoppeln die Grenzfrequenz eines RC-Tiefpasses?

- [x] $R$ halbieren

  $f_\mathrm{g} = 1/(2\pi RC)$ ist umgekehrt proportional zu $R$.

- [ ] $R$ und $C$ verdoppeln

  Dann vervierfacht sich $RC$, und $f_\mathrm{g}$ sinkt auf ein Viertel.

- [x] $C$ halbieren

  $f_\mathrm{g}$ ist umgekehrt proportional zu $C$.

- [ ] Die Eingangsamplitude verdoppeln

  Das Filter ist linear; $f_\mathrm{g}$ hängt nicht von der Amplitude ab.

- [x] Eine Last $R_\mathrm{L} = R$ parallel zu $C$ anschließen

  Der wirksame Widerstand wird $R \parallel R = R/2$.

::: explanation
Die Grenzfrequenz hängt nur vom wirksamen Produkt aus Widerstand und Kapazität ab. Halbiert
sich dieses Produkt, verdoppelt sich $f_\mathrm{g}$.
:::
::::

:::: {.mcq #mc-rc-filter-104 type="kprim" difficulty="3"}
Ein unbelasteter RC-Tiefpass mit $\tau = 2\,\mathrm{ms}$ wird zum Zeitpunkt $t = 0$ mit
einem Sprung von $0$ auf $10\,\mathrm{V}$ angeregt; der Kondensator ist anfangs ungeladen.
Beurteilen Sie die Aussagen.

- [ ] Bei $t = 10\,\mathrm{ms}$ ist $u_C$ noch kleiner als $9\,\mathrm{V}$.

  Falsch: Nach $5\tau$ gilt $u_C \approx 9{,}93\,\mathrm{V}$.

- [x] Bei $t = 2\,\mathrm{ms}$ ist $u_C \approx 6{,}3\,\mathrm{V}$.

  Richtig: $10\,\mathrm{V} \cdot (1 - \mathrm{e}^{-1})$.

- [ ] Der Strom bei $t = 0$ hängt nicht von $R$ ab.

  Falsch: $i(0) = U_0/R$.

- [x] Bei $t = 4\,\mathrm{ms}$ ist $u_C \approx 8{,}6\,\mathrm{V}$.

  Richtig: $10\,\mathrm{V} \cdot (1 - \mathrm{e}^{-2})$.

::: explanation
$u_C(t) = 10\,\mathrm{V} \cdot (1 - \mathrm{e}^{-t/2\,\mathrm{ms}})$ ergibt $6{,}32\,\mathrm{V}$
nach $\tau$, $8{,}65\,\mathrm{V}$ nach $2\tau$ und $9{,}93\,\mathrm{V}$ nach $5\tau$.
:::
::::
