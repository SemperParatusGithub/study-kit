# Sample materials

Self-written stand-ins for a lecturer's PDFs, used to run `/register-new-subject` end to end
(docs/architecture.md §5.4, Phase 6). The subject, op-amp basic circuits, is deliberately not
the one of `examples/sample-course` (RC networks), so a run shows that the pipeline is not
tuned to the sample course. Everything is in German, like the course it should produce.

Only the sources are in the repository. `just sample-materials` (or
`uv run --frozen python examples/sample-materials/build.py [--out DIR]`) renders the circuit
figures with `studykit.figures`, compiles the Typst sources with the pinned Typst and writes
the PDFs into `_build/materials/`, which is gitignored: PDFs are never committed. The build
is deterministic (`SOURCE_DATE_EPOCH=0`, embedded fonts only, seeded noise for the scan).

| Source | PDF in `_build/materials/` | Kind | Content |
|---|---|---|---|
| `src/vl03-folien.typ` | `VL03_Operationsverstaerker_Grundschaltungen.pdf` | slides | 14 slides (16:9): ideal op-amp, the two rules under negative feedback, inverting and non-inverting amplifier, voltage follower, summing amplifier, integrator, summary table, exam date 17.02.2027 |
| `src/skript-kap4.typ` | `Skript_Kapitel4_Operationsverstaerker.pdf` | script | Lecture notes excerpt, chapter 4: the same circuits derived in prose, finite open-loop gain, the integrator's frequency response |
| `src/uebung03.typ` | `Uebung03_OPV_Grundschaltungen.pdf` | exercises | Exercise sheet 3: inverting amplifier, non-inverting amplifier, summing amplifier, integrator |
| `src/uebung03-loesung.typ` | `Uebung03_OPV_Grundschaltungen_Loesung.pdf` | solutions | Worked solutions to sheet 3 |
| `src/klausur-ws2526.typ` | `Klausur_WS2025-26.pdf` | exam | Past exam WS 2025/26: 90 minutes, 60 points (pass at 30), an MC part of six questions (2 points each, all-or-nothing, no negative marking) and three calculation tasks |
| `src/klausur-ws2526-loesung.typ` | `Klausur_WS2025-26_Loesung.pdf` | exam-solutions | Model solution with the points per step |
| `src/scan-uebung02.typ` | `Altes_Uebungsblatt02_Scan.pdf` | exercises (scan) | An old exercise sheet rendered at 100 ppi, rotated by about 1.3°, blurred, darkened at one edge and given seeded noise and dust, then wrapped into a PDF **without a text layer**: the page ingest must flag as visual |

`src/common.typ` holds the shared page setup (A4 handouts and 16:9 slides; deliberately not
the study-kit house style). `figures/*.py` are `studykit.figures` scripts for the circuits
(inverting, non-inverting, integrator, and a symbolic inverting amplifier for the sheet and the
exam); the build renders them into `_build/work/figures/` and the Typst sources include the SVGs.

Every number in the materials was computed with Python, not by hand. A few of them, to check
an ingested course against: inverting amplifier 47 kΩ / 10 kΩ gives V = −4.7; the integrator
with R = 10 kΩ and C = 100 nF has RC = 1 ms and |H| = 1 at about 159 Hz; in the past exam,
15 kΩ / 2.2 kΩ gives V ≈ −6.82, and R = 47 kΩ, C = 220 nF with a 1 V step reaches −11 V after
about 113.7 ms.

To try the ingest side on them:

```sh
just sample-materials
uv run --frozen studykit ingest scan examples/sample-materials/_build/materials --dry-run
```
