# Outline: Elektronik 1 – Operationsverstärker (opv)

Written by the synthesis step of /register-new-subject from the chunk notes in
`sources/notes/`. Weights: exam point shares from `analysis/exam-profile.yaml`
(confidence medium), falling back to lecture pages per topic. Topic ids are fixed once
written; `course.yaml: topics` holds the same ids, titles, weights and prerequisites.

## Topics

| # | id | Title | Weight | Prerequisites | Chunks | Past exams |
|---|---|---|---|---|---|---|
| 1 | idealer-opv | Idealer Operationsverstärker | 0.10 | – | vl-03-c01, skript-4-c01 | MC 2 of 6 |
| 2 | invertierender-verstaerker | Invertierender Verstärker | 0.30 | idealer-opv | vl-03-c01, ue-03-c01, klausur-ws2526-c01 | 1 of 1 |
| 3 | integrierer | Integrierer | 0.60 | invertierender-verstaerker | vl-03-c01, skript-4-c01, klausur-ws2526-c01 | 1 of 1 |

## idealer-opv: Idealer Operationsverstärker

- Sources: vl-03-c01 (p. 2–4), skript-4-c01 (p. 1–3)
- Candidate slugs merged: idealer-opv, gegenkopplung, virtuelle-masse
- Key formulas: $U_\mathrm{d} = 0$ and $I_\mathrm{p} = I_\mathrm{n} = 0$ under negative feedback
- Archetypes: MC part (definitions, the two rules)

## invertierender-verstaerker: Invertierender Verstärker

- Sources: vl-03-c01 (p. 5–7), ue-03-c01 (p. 1), klausur-ws2526-c01 (p. 1)
- Candidate slugs merged: invertierender-verstaerker, verstaerkung-berechnen
- Key formulas: $V = -R_2/R_1$
- Archetypes: invertierer-dimensionieren (14 of 48 task points)

## integrierer: Integrierer

- Sources: vl-03-c01 (p. 11–12), skript-4-c01 (p. 4–6), klausur-ws2526-c01 (p. 2)
- Candidate slugs merged: integrierer, frequenzgang-integrierer
- Key formulas: $u_\mathrm{a}(t) = -\frac{1}{RC}\int_0^t u_\mathrm{e}\,\mathrm{d}\tau$
- Archetypes: integrierer-saettigung (18 of 48 task points)

## Chunks

| Chunk | Document | Pages | Kind | Topics |
|---|---|---|---|---|
| vl-03-c01 | vl-03 | 1–14 | slides | idealer-opv, invertierender-verstaerker, integrierer |
| skript-4-c01 | skript-4 | 1–6 | script | idealer-opv, integrierer |
| ue-03-c01 | ue-03 | 1 | exercises | invertierender-verstaerker |
| klausur-ws2526-c01 | klausur-ws2526 | 1–2 | exam | invertierender-verstaerker, integrierer |
