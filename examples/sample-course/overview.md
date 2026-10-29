---
title: Überblick
---

## Worum geht es?

Dieser Beispielkurs behandelt Netzwerke aus Widerständen und Kondensatoren, vom
Gleichstrom bis zum Frequenzgang. Am Anfang stehen [Spannungsteiler und
Ersatzquellen](topic:spannungsteiler): Wie teilt sich eine Spannung auf, und was ändert eine
Last? Die [komplexe Wechselstromrechnung](topic:wechselstrom) überträgt diese Regeln auf
Sinusgrößen, indem sie Spulen und Kondensatoren als komplexe Widerstände behandelt. Im
Schwerpunktthema [RC-Filter und Bode-Diagramm](topic:rc-filter) kommt beides zusammen:
Ein RC-Glied ist ein frequenzabhängiger Spannungsteiler, dessen Verhalten man im
Bode-Diagramm und in der Sprungantwort abliest.

## Themenkarte

![Themen des Kurses und ihre Abhängigkeiten; RC-Filter ist der Schwerpunkt](fig:topic-map)

## Wie die Themen zusammenhängen

Die Spannungsteilerregel ist der rote Faden. Im Gleichstromkreis teilt sie eine Spannung im
Verhältnis zweier Widerstände. In der Wechselstromrechnung gilt dieselbe Regel für
Impedanzen, nur mit komplexen Zahlen. Der RC-Tiefpass ist genau dieser Teiler aus $R$ und
$1/(\mathrm{j}\omega C)$:

$$
\underline{H} = \frac{1/(\mathrm{j}\omega C)}{R + 1/(\mathrm{j}\omega C)} = \frac{1}{1 + \mathrm{j}\omega RC}
$$

Auch die Ersatzspannungsquelle kehrt wieder: Hängt am Ausgang eines Filters eine Last,
bestimmt der Innenwiderstand der Ersatzquelle die neue Grenzfrequenz. Wer die beiden
ersten Themen sicher beherrscht, muss für die RC-Filter nur noch Zeitkonstante,
Grenzfrequenz und Bode-Diagramm dazulernen.

## Die Klausur auf einen Blick

Die Klausur am 15. Februar 2027 dauert 120 Minuten und bringt 100 Punkte. Erlaubt sind ein
nicht programmierbarer Taschenrechner und ein selbst geschriebenes Formelblatt mit zwei
Seiten. Es gibt kein Altklausurmaterial; die Aufteilung folgt der Kursbeschreibung:

| Teil | Inhalt | Punkte |
|---|---|---|
| Rechenaufgabe | Ersatzspannungsquelle und belasteter Teiler | 20 |
| Rechenaufgabe | Impedanz und Zeigerdiagramm | 20 |
| Rechenaufgabe | RC-Filter im Bode-Diagramm | 24 |
| Rechenaufgabe | Sprungantwort eines RC-Glieds | 16 |
| MC-Teil | 10 Fragen (Single Choice, Multiple Choice, Kprim) zu je 2 Punkten | 20 |

Im MC-Teil zählt eine Frage nur, wenn sie vollständig richtig beantwortet ist; falsche
Antworten geben keinen Abzug. Mit gut einer Minute pro Punkt bleibt keine Zeit, Formeln
herzuleiten: Die Standardrechnungen müssen sitzen. Die
[Probeklausur 1](exam:probeklausur-1) hat genau dieses Format und gilt ab 50 Punkten als
bestanden.

## So lernst du dieses Fach

- Arbeite die Themen in der Reihenfolge der Themenkarte durch. Lies zuerst die
  Zusammenfassung, rechne dann die Übungen ohne Hinweise und öffne einen Hinweis erst,
  wenn du festhängst.
- Beginne jedes Thema mit einer leichten Übung, etwa dem
  [unbelasteten Spannungsteiler](ex:ex-st-unbelastet) oder der
  [Grenzfrequenz eines RC-Tiefpasses](ex:ex-rc-tp-grenzfrequenz), und steigere dann die
  Schwierigkeit.
- Beantworte die MC-Fragen eines Themas erst nach den Übungen. Lies bei jeder falschen
  Antwort die Begründung: Die falschen Optionen beschreiben typische Fehler wie einen
  vergessenen Faktor $2\pi$ oder Effektivwert und Amplitude.
- Führe dein Formelblatt von Anfang an mit und schreibe die Probeklausur in den letzten zwei
  Wochen unter Zeitdruck.

## Voraussetzungen

- Ohmsches Gesetz, Kirchhoffsche Regeln, Reihen- und Parallelschaltung von Widerständen
- Komplexe Zahlen in algebraischer und exponentieller Form, Betrag und Winkel
- Trigonometrische Funktionen, Logarithmus und Exponentialfunktion
