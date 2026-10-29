---
topic: wechselstrom
title: Komplexe Wechselstromrechnung
---

:::: {.mcq #mc-wechselstrom-001 type="single" difficulty="1"}
Eine sinusförmige Spannung hat die Amplitude $\hat{u} = 10\,\mathrm{V}$. Wie groß ist ihr
Effektivwert?

- [ ] $14{,}1\,\mathrm{V}$

  Mit $\sqrt{2}$ multipliziert statt dividiert.

- [ ] $6{,}37\,\mathrm{V}$

  Das ist der Gleichrichtwert $2\hat{u}/\pi$, der Mittelwert des Betrags.

- [x] $7{,}07\,\mathrm{V}$

  $U = \hat{u}/\sqrt{2}$.

- [ ] $10\,\mathrm{V}$

  Amplitude und Effektivwert gleichgesetzt.

::: explanation
Der Effektivwert ist die Wurzel aus dem Mittelwert des Quadrats. Für eine Sinusgröße ergibt
das $\hat{u}/\sqrt{2} \approx 0{,}707\,\hat{u}$.
:::
::::

:::: {.mcq #mc-wechselstrom-002 type="single" difficulty="1"}
Welche Impedanz hat eine ideale Spule mit $L = 10\,\mathrm{mH}$ bei
$f = 1\,\mathrm{kHz}$?

- [x] $\mathrm{j}\,62{,}8\,\Omega$

  $\underline{Z}_L = \mathrm{j}\omega L = \mathrm{j} \cdot 2\pi \cdot 1\,\mathrm{kHz} \cdot 10\,\mathrm{mH}$.

- [ ] $\mathrm{j}\,10\,\Omega$

  Mit $f$ statt mit $\omega = 2\pi f$ gerechnet: Faktor $2\pi$ vergessen.

- [ ] $-\mathrm{j}\,62{,}8\,\Omega$

  Falsches Vorzeichen: Ein negativer Imaginärteil gehört zu einem Kondensator.

- [ ] $62{,}8\,\Omega$

  Ohne $\mathrm{j}$ wäre es ein ohmscher Widerstand; Strom und Spannung wären in Phase.

::: explanation
Die Spannung an der Spule eilt dem Strom um $90^\circ$ voraus. Deshalb ist ihre Impedanz
rein positiv imaginär und wächst proportional mit der Frequenz.
:::
::::

:::: {.mcq #mc-wechselstrom-003 type="single" difficulty="2"}
Ein Kondensator mit $C = 1\,\mathrm{\mu F}$ liegt an einer Sinusspannung mit
$f = 50\,\mathrm{Hz}$. Wie groß ist der Betrag seines Blindwiderstands?

- [ ] $20\,\mathrm{k\Omega}$

  $1/(fC)$: Faktor $2\pi$ vergessen.

- [ ] $318\,\Omega$

  Zehnerpotenz falsch: mit $C = 10\,\mathrm{\mu F}$ gerechnet.

- [ ] $0{,}314\,\mathrm{m\Omega}$

  $\omega C$ statt $1/(\omega C)$ berechnet.

- [x] $3{,}18\,\mathrm{k\Omega}$

  $X_C = 1/(2\pi \cdot 50\,\mathrm{Hz} \cdot 1\,\mathrm{\mu F})$.

::: explanation
Der Blindwiderstand eines Kondensators ist $1/(\omega C)$. Er sinkt mit wachsender Frequenz
und mit wachsender Kapazität.
:::
::::

:::: {.mcq #mc-wechselstrom-004 type="single" difficulty="2"}
In einer RL-Reihenschaltung gilt $R = 50\,\Omega$ und $\omega L = 120\,\Omega$. Wie groß ist
der Betrag der Impedanz?

- [ ] $170\,\Omega$

  Die Beträge algebraisch addiert, als wären beide Größen in Phase.

- [x] $130\,\Omega$

  $|\underline{Z}| = \sqrt{50^2 + 120^2}\,\Omega$.

- [ ] $109\,\Omega$

  Die Quadrate subtrahiert statt addiert.

- [ ] $46{,}2\,\Omega$

  Eine Parallelschaltung angenommen: $R\,\omega L/\sqrt{R^2 + (\omega L)^2}$.

::: explanation
Realteil $R$ und Imaginärteil $\omega L$ stehen senkrecht aufeinander, daher gilt der Satz
des Pythagoras: $|\underline{Z}| = \sqrt{R^2 + (\omega L)^2}$.
:::
::::

:::: {.mcq #mc-wechselstrom-005 type="single" difficulty="2"}
Welcher Phasenwinkel $\varphi = \varphi_u - \varphi_i$ gehört zu einem idealen
Kondensator?

- [ ] $+90^\circ$

  Das gilt für die Spule: Dort eilt die Spannung dem Strom voraus.

- [ ] $0^\circ$

  Das gilt für einen ohmschen Widerstand.

- [ ] $-45^\circ$

  Das gilt für eine RC-Reihenschaltung mit $R = X_C$, nicht für den Kondensator allein.

- [x] $-90^\circ$

  Der Strom eilt der Spannung um $90^\circ$ voraus.

::: explanation
$\underline{Z}_C = -\mathrm{j}/(\omega C)$ liegt auf der negativen imaginären Achse; sein
Winkel ist $-90^\circ$.
:::
::::

:::: {.mcq #mc-wechselstrom-006 type="single" difficulty="3"}
Ein Zweipol hat die Impedanz $\underline{Z} = (40 - \mathrm{j}\,30)\,\Omega$. Welche
Aussage trifft zu?

- [x] Ohmsch-kapazitiv, $|\underline{Z}| = 50\,\Omega$

  Negativer Imaginärteil, $\sqrt{40^2 + 30^2}\,\Omega = 50\,\Omega$.

- [ ] Ohmsch-induktiv, $|\underline{Z}| = 50\,\Omega$

  Das Vorzeichen des Imaginärteils falsch gedeutet: Induktiv wäre ein positiver
  Imaginärteil.

- [ ] Ohmsch-kapazitiv, $|\underline{Z}| = 70\,\Omega$

  Real- und Imaginärteil algebraisch addiert.

- [ ] Ohmsch-kapazitiv, $|\underline{Z}| = 10\,\Omega$

  Real- und Imaginärteil voneinander abgezogen.

::: explanation
Der Winkel ist $\varphi = -\arctan(30/40) \approx -36{,}9^\circ$: Die Spannung eilt dem
Strom nach, wie bei einer Reihenschaltung aus Widerstand und Kondensator.
:::
::::

:::: {.mcq #mc-wechselstrom-007 type="multi" difficulty="2"}
Welche Aussagen gelten für den Blindwiderstand $X_C$ eines idealen Kondensators?

- [ ] $X_C$ steigt linear mit der Kapazität.

  Falsch: $X_C = 1/(\omega C)$ sinkt, wenn $C$ steigt.

- [x] $X_C$ ist umgekehrt proportional zur Frequenz.

  $X_C = 1/(2\pi f C)$.

- [ ] Bei sehr hohen Frequenzen wirkt der Kondensator wie ein Leerlauf.

  Verwechslung mit der Spule: Bei hohen Frequenzen wirkt der Kondensator wie ein
  Kurzschluss.

- [x] Bei Gleichspannung wirkt der Kondensator im eingeschwungenen Zustand wie ein
  Leerlauf.

  Für $f \to 0$ geht $X_C \to \infty$.

::: explanation
Je schneller sich die Spannung ändert und je größer die Kapazität ist, desto größer ist der
Umladestrom. Darum sinkt $X_C = 1/(\omega C)$ mit $\omega$ und mit $C$.
:::
::::

:::: {.mcq #mc-wechselstrom-008 type="multi" difficulty="3"}
Zwei Sinusspannungen gleicher Frequenz mit den Effektivwerten $U_1 = 3\,\mathrm{V}$ und
$U_2 = 4\,\mathrm{V}$ liegen in Reihe. Welche Effektivwerte kann die Summenspannung je nach
Phasenlage annehmen?

- [x] $7\,\mathrm{V}$

  Bei gleicher Phase addieren sich die Beträge.

- [x] $5\,\mathrm{V}$

  Bei $90^\circ$ Phasenverschiebung: $\sqrt{3^2 + 4^2}\,\mathrm{V}$.

- [ ] $8\,\mathrm{V}$

  Unmöglich: Der Betrag einer Zeigersumme ist höchstens $U_1 + U_2 = 7\,\mathrm{V}$.

- [x] $1\,\mathrm{V}$

  Bei Gegenphase subtrahieren sich die Beträge.

- [ ] $0{,}5\,\mathrm{V}$

  Unmöglich: Der Betrag ist mindestens $|U_1 - U_2| = 1\,\mathrm{V}$.

::: explanation
Zeiger addieren sich wie Vektoren. Nach der Dreiecksungleichung liegt der Betrag der Summe
zwischen $|U_1 - U_2| = 1\,\mathrm{V}$ und $U_1 + U_2 = 7\,\mathrm{V}$.
:::
::::

:::: {.mcq #mc-wechselstrom-009 type="kprim" difficulty="2"}
Beurteilen Sie die Aussagen zur komplexen Wechselstromrechnung.

- [x] Die Impedanz einer Spule ist $\underline{Z}_L = \mathrm{j}\omega L$.

  Richtig: positiv imaginär und proportional zur Frequenz.

- [ ] Die Impedanz eines Kondensators ist $\underline{Z}_C = \mathrm{j}\omega C$.

  Falsch: $\underline{Z}_C = 1/(\mathrm{j}\omega C) = -\mathrm{j}/(\omega C)$.

- [x] In einer Reihenschaltung addieren sich die komplexen Impedanzen.

  Richtig, wie Widerstände im Gleichstromkreis.

- [ ] In einer Reihenschaltung ist die Gesamtspannung stets die Summe der Effektivwerte der
  Teilspannungen.

  Falsch: Die Zeiger addieren sich, die Beträge nur bei gleicher Phase.

::: explanation
Mit Impedanzen rechnet man wie mit Widerständen, aber komplex. Effektivwerte sind Beträge
von Zeigern und addieren sich deshalb im Allgemeinen nicht.
:::
::::

:::: {.mcq #mc-wechselstrom-010 type="kprim" difficulty="3"}
Ein Zweipol nimmt an $\underline{U} = 230\,\mathrm{V}$ (Nullphase $0^\circ$) den Strom
$\underline{I} = 2\,\mathrm{A} \cdot \mathrm{e}^{-\mathrm{j}60^\circ}$ auf. Beurteilen Sie
die Aussagen.

- [x] $|\underline{Z}| = 115\,\Omega$.

  $230\,\mathrm{V}/2\,\mathrm{A}$.

- [ ] Der Realteil von $\underline{Z}$ beträgt $99{,}6\,\Omega$.

  Falsch: Das ist der Imaginärteil $115\,\Omega \cdot \sin 60^\circ$; der Realteil ist
  $115\,\Omega \cdot \cos 60^\circ = 57{,}5\,\Omega$.

- [x] Der Zweipol verhält sich ohmsch-induktiv.

  Richtig: $\varphi = \varphi_u - \varphi_i = +60^\circ$.

- [ ] Die Amplitude des Stroms beträgt $2\,\mathrm{A}$.

  Falsch: $2\,\mathrm{A}$ ist der Effektivwert, die Amplitude ist
  $2\sqrt{2}\,\mathrm{A} \approx 2{,}83\,\mathrm{A}$.

::: explanation
$\underline{Z} = \underline{U}/\underline{I} = 115\,\Omega \cdot \mathrm{e}^{\mathrm{j}60^\circ} = (57{,}5 + \mathrm{j}\,99{,}6)\,\Omega$.
Ein positiver Winkel bedeutet, dass der Strom der Spannung nacheilt.
:::
::::
