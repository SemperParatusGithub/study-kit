---
id: ex-rc-hp-dimensionieren
title: Hochpass dimensionieren
topic: rc-filter
difficulty: 2
kind: compute
minutes: 12
answers:
  - {key: R, label: 'Berechneter Widerstand $R$', value: 7.2343, unit: kΩ, rtol: 5.0e-3}
  - {key: RE12, label: 'Gewählter Normwert $R$', value: 6.8, unit: kΩ, rtol: 1.0e-3}
  - {key: fg, label: 'Grenzfrequenz $f_\mathrm{g}$ mit dem Normwert', value: 106.39, unit: Hz, rtol: 5.0e-3}
  - {key: Hdb, label: '$|\underline{H}|$ bei $50\,\mathrm{Hz}$ in dB', value: -7.425, unit: dB, atol: 0.05}
  - {key: phi, label: 'Phase $\varphi$ bei $50\,\mathrm{Hz}$', value: 64.83, unit: °, atol: 0.5}
---

Ein RC-Hochpass soll eine eingestreute Brummspannung mit $50\,\mathrm{Hz}$ dämpfen und
Signale oberhalb von etwa $100\,\mathrm{Hz}$ durchlassen. Vorhanden ist ein Kondensator
mit $C = 220\,\mathrm{nF}$.

![RC-Hochpass: C im Längszweig, R im Querzweig](fig:rc-hp-schaltung)

**a)** Welcher Widerstand $R$ ergibt genau $f_\mathrm{g} = 100\,\mathrm{Hz}$?

**b)** Widerstände gibt es in der Normreihe E12 mit den Werten 1,0; 1,2; 1,5; 1,8; 2,2;
2,7; 3,3; 3,9; 4,7; 5,6; 6,8 und 8,2 mal einer Zehnerpotenz. Wählen Sie den
nächstgelegenen Normwert und berechnen Sie die neue Grenzfrequenz.

**c)** Wie groß sind Betrag (in dB) und Phase von $\underline{H}$ bei $50\,\mathrm{Hz}$
mit dem Normwert?

::: hint
Für den Hochpass gilt dieselbe Formel für die Grenzfrequenz wie für den Tiefpass. Lösen Sie
sie nach $R$ auf.
:::

::: hint
Mit $x = f/f_\mathrm{g}$ gilt für den Hochpass $|\underline{H}| = x/\sqrt{1 + x^2}$ und
$\varphi = 90^\circ - \arctan x$.
:::

::: solution
**a)** $R = \frac{1}{2\pi f_\mathrm{g} C} = \frac{1}{2\pi \cdot 100\,\mathrm{Hz} \cdot 220\,\mathrm{nF}} \approx 7{,}23\,\mathrm{k\Omega}$

**b)** Der nächstgelegene Normwert ist $6{,}8\,\mathrm{k\Omega}$; $8{,}2\,\mathrm{k\Omega}$
liegt weiter entfernt. Damit wird

$$
f_\mathrm{g} = \frac{1}{2\pi \cdot 6{,}8\,\mathrm{k\Omega} \cdot 220\,\mathrm{nF}} \approx 106{,}4\,\mathrm{Hz}
$$

Die Grenzfrequenz liegt also knapp über $100\,\mathrm{Hz}$: Ein Signal mit
$100\,\mathrm{Hz}$ wird schon um rund $3{,}3\,\mathrm{dB}$ gedämpft.

**c)** $x = 50/106{,}4 \approx 0{,}470$:

$$
|\underline{H}| = \frac{0{,}470}{\sqrt{1 + 0{,}470^2}} \approx 0{,}425 \;\Rightarrow\; 20\lg 0{,}425 \approx -7{,}43\,\mathrm{dB}, \qquad \varphi = 90^\circ - \arctan 0{,}470 \approx 64{,}8^\circ
$$

Die Brummspannung wird also nur auf rund $43\,\%$ abgeschwächt: So nahe an der
Grenzfrequenz dämpft ein Filter erster Ordnung wenig.

Muss der Durchlassbereich ab $100\,\mathrm{Hz}$ sicher eingehalten werden, nimmt man den
nächstgrößeren Normwert $8{,}2\,\mathrm{k\Omega}$ mit $f_\mathrm{g} \approx 88\,\mathrm{Hz}$.
Dafür wird die Brummspannung noch schwächer gedämpft, mit $-6{,}1\,\mathrm{dB}$ statt
$-7{,}4\,\mathrm{dB}$.
:::
