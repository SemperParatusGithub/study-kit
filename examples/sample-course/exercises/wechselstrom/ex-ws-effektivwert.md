---
id: ex-ws-effektivwert
title: Kenngrößen einer Sinusspannung
topic: wechselstrom
difficulty: 1
kind: compute
minutes: 8
answers:
  - {key: U, label: 'Effektivwert $U$', value: 12.021, unit: V, rtol: 5.0e-3}
  - {key: T, label: 'Periodendauer $T$', value: 2.5, unit: ms, rtol: 5.0e-3}
  - {key: w, label: 'Kreisfrequenz $\omega$', value: 2513.3, unit: 1/s, rtol: 5.0e-3}
  - {key: u0, label: 'Augenblickswert $u(0)$', value: 14.722, unit: V, rtol: 5.0e-3}
  - {key: t1, label: 'Zeitpunkt $t_1$ des ersten Maximums', value: 0.20833, unit: ms, rtol: 1.0e-2}
---

Ein Funktionsgenerator liefert die Spannung

$$
u(t) = 17\,\mathrm{V} \cdot \cos\left(2\pi \cdot 400\,\mathrm{Hz} \cdot t - 30^\circ\right).
$$

**a)** Wie groß ist der Effektivwert $U$?

**b)** Bestimmen Sie die Periodendauer $T$ und die Kreisfrequenz $\omega$.

**c)** Welchen Wert hat die Spannung zum Zeitpunkt $t = 0$?

**d)** Zu welchem Zeitpunkt $t_1 > 0$ erreicht $u(t)$ zum ersten Mal ihr Maximum?

::: hint
Lesen Sie Amplitude, Frequenz und Nullphase aus der Funktionsgleichung ab. Für Sinusgrößen
gilt $U = \hat{u}/\sqrt{2}$.
:::

::: hint
Das Maximum liegt dort, wo das Argument des Kosinus null wird. Ein Winkel von
$360^\circ$ entspricht einer Periodendauer.
:::

::: solution
**a)** $U = \frac{\hat{u}}{\sqrt{2}} = \frac{17\,\mathrm{V}}{\sqrt{2}} \approx 12{,}02\,\mathrm{V}$

**b)** $T = \frac{1}{f} = \frac{1}{400\,\mathrm{Hz}} = 2{,}5\,\mathrm{ms}$ und
$\omega = 2\pi f \approx 2513\,\mathrm{s^{-1}}$.

**c)** $u(0) = 17\,\mathrm{V} \cdot \cos(-30^\circ) \approx 14{,}72\,\mathrm{V}$

**d)** Das Argument wird null, wenn $\omega t_1 = 30^\circ$ ist, also nach einem Zwölftel
der Periode:

$$
t_1 = \frac{30^\circ}{360^\circ} \cdot T = \frac{2{,}5\,\mathrm{ms}}{12} \approx 0{,}208\,\mathrm{ms}
$$
:::
