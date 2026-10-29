---
chunk: vl-03-c01
doc: vl-03
pages: '1-14'
source_sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
kind: slides
title: Operationsverstärker-Grundschaltungen (Vorlesung 3)
topics: [idealer-opv, invertierender-verstaerker, nichtinvertierender-verstaerker, integrierer]
visual_pages: [5, 11]
---

## Summary

Die Folien führen den idealen Operationsverstärker ein und leiten aus den zwei Regeln der
Gegenkopplung die Grundschaltungen her: invertierender und nichtinvertierender Verstärker,
Spannungsfolger, Summierer und Integrierer ([S. 2](src:vl-03#p=2)). Jede Schaltung wird
mit Schaltbild, Herleitung über die virtuelle Masse und einem Zahlenbeispiel gezeigt. Die
letzte Folie fasst die Verstärkungen in einer Tabelle zusammen ([S. 13](src:vl-03#p=13)).

## Course facts

- Veranstaltung: Elektronik 1, Vorlesung 3 ([S. 1](src:vl-03#p=1))
- Klausurtermin: 17.02.2027, 90 Minuten, schriftlich mit Multiple-Choice-Teil ([S. 14](src:vl-03#p=14))

## Topics

- `idealer-opv`: ideale Eigenschaften, Regeln der Gegenkopplung, S. 2–4
- `invertierender-verstaerker`: Herleitung und Beispiel, S. 5–7
- `nichtinvertierender-verstaerker`: mit Spannungsfolger, S. 8–10
- `integrierer`: Zeitbereich und Frequenzgang, S. 11–12

## Formulas

$$
V = \frac{U_\mathrm{a}}{U_\mathrm{e}} = -\frac{R_2}{R_1}
$$

Verstärkung des invertierenden Verstärkers, idealer OPV mit Gegenkopplung ([S. 5](src:vl-03#p=5)).

$$
V = 1 + \frac{R_2}{R_1}
$$

Verstärkung des nichtinvertierenden Verstärkers; $R_2 = 0$ ergibt den Spannungsfolger ([S. 8](src:vl-03#p=8)).

$$
u_\mathrm{a}(t) = -\frac{1}{RC} \int_0^t u_\mathrm{e}(\tau)\,\mathrm{d}\tau + u_\mathrm{a}(0)
$$

Ausgangsspannung des Integrierers ([S. 11](src:vl-03#p=11)).

## Definitions

- **Virtuelle Masse:** Bei Gegenkopplung und geerdetem nichtinvertierendem Eingang liegt
  der invertierende Eingang auf $0\,\mathrm{V}$, ohne mit Masse verbunden zu sein ([S. 3](src:vl-03#p=3)).
- **Idealer OPV:** unendliche Leerlaufverstärkung, unendlicher Eingangswiderstand,
  Ausgangswiderstand null ([S. 2](src:vl-03#p=2)).

## Examples

- $R_1 = 10\,\mathrm{k\Omega}$, $R_2 = 47\,\mathrm{k\Omega}$ ergibt $V = -4{,}7$ ([S. 6](src:vl-03#p=6)).
- Integrierer mit $R = 10\,\mathrm{k\Omega}$, $C = 100\,\mathrm{nF}$: $RC = 1\,\mathrm{ms}$,
  Betrag 1 bei etwa $159\,\mathrm{Hz}$ ([S. 12](src:vl-03#p=12)).

## Exercise archetypes

- `verstaerkung-aus-widerstaenden`: gegeben $R_1$, $R_2$, gesucht $V$ und $U_\mathrm{a}$ für ein gegebenes $U_\mathrm{e}$; virtuelle Masse, Knotenregel ([S. 6](src:vl-03#p=6))
- `widerstand-fuer-zielverstaerkung`: gegeben $V$ und $R_1$, gesucht $R_2$ ([S. 7](src:vl-03#p=7))
- `integrierer-sprungantwort`: Sprung am Eingang, gesucht die Zeit bis zur Sättigung ([S. 12](src:vl-03#p=12))

## Notation

- Spannungen als $U$ mit Index in Steilschrift: $U_\mathrm{e}$, $U_\mathrm{a}$; zeitabhängig klein: $u_\mathrm{a}(t)$.
- Dezimalkomma; imaginäre Einheit und Zeiger kommen in diesem Abschnitt nicht vor.

## Figures

- S. 5: Schaltbild des invertierenden Verstärkers: $U_\mathrm{e}$ über $R_1$ an den
  invertierenden Eingang, $R_2$ vom Ausgang zurück, nichtinvertierender Eingang auf Masse;
  Zählpfeile von $U_\mathrm{e}$ und $U_\mathrm{a}$ gegen Masse.
- S. 11: Schaltbild des Integrierers ($C$ im Rückkopplungszweig) und Skizze der Rampe
  $u_\mathrm{a}(t)$ für einen Eingangssprung.

## Open questions

–
