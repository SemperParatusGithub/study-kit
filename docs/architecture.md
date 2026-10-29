# study-kit architecture

This is the reference specification for study-kit. It was produced by a research and
judge-panel design pass (4 research agents, 3 design lenses, 1 judge) on 2026-10-29 and
then amended with the user's decisions. When code and this document disagree, fix one of
them in the same change.

## 0. Decisions

| Area | Decision |
|---|---|
| License | MIT |
| Unverified items | Quarantined: hidden on the site and in PDFs, listed in the report |
| MC defaults (no past exams) | 10–25 questions per topic by weight; 60% single, 25% multi, 15% Kprim; multi all-or-nothing; no negative marking. Past exams override. |
| Search | Pagefind in v1 (§3.5) |
| Course data | `courses/` inside the repo, gitignored; never committed |
| Language | Skills, agents, UI and code in English; generated content follows `course.lang` |
| Commits | Conventional Commits, one logical change each, never a Co-Authored-By trailer |

## 1. Repository layout

Entries marked *(Phase n)* are planned and do not exist yet.

```
study-kit/
├── README.md  LICENSE  CLAUDE.md  .editorconfig  .gitignore
├── justfile                        # single entry point for humans, Claude and CI (§4.2)
├── toolchain.toml                  # pandoc/typst/just: exact version, URL, sha256 per platform; minimum versions of uv, node, pnpm
├── .python-version                 # 3.14
├── pyproject.toml  uv.lock         # package "studykit" (src layout); [tool.uv] exclude-newer = "7 days"
├── .githooks/commit-msg            # Conventional Commits; reject a Co-Authored-By trailer on every commit
├── .githooks/pre-commit            # reject staged paths under courses/ (except README) and PDFs outside tests/fixtures/
├── .github/workflows/ci.yml  guard.yml
├── .github/scripts/guard.sh        # the guard workflow's checks: `commits`, `courses`, `pdfs`
├── .github/scripts/test-hooks.sh   # tests of the git hooks and guard.sh in throwaway repositories (`just test`)
├── src/studykit/
│   ├── cli.py                      # argparse (stdlib); --json on doctor, ls, index, lint, validate, render, check-links
│   ├── tools.py                    # `tools install`: pandoc, typst and just → .tools/bin, sha256-checked
│   ├── doctor.py                   # `doctor`: tool versions, site packages, Typst fonts, git hooks, courses/ ignored, port 4321
│   ├── model.py                    # pydantic models: the single schema source
│   ├── yamlio.py                   # restricted SafeLoader (no YAML-1.1 yes/no/on/off, no sexagesimal) + scalar-style lint
│   ├── content.py                  # discovery, frontmatter split, fence-line and math scanners, MC parser
│   ├── index.py                    # `index`: _build/index.json (ids, topics, exams, sources, figures)
│   ├── findings.py                 # Finding (path:line:col SK-CODE message (fix: …)) and its parser
│   ├── pandoc.py                   # run pandoc with the shared defaults and filter metadata (targets: html | typst | json)
│   ├── lint.py  validate.py        # per-file lint (hook) / full validation, findings as SK-codes
│   ├── render.py                   # `render`: the site loader's bridge to pandoc (§3.2)
│   ├── sitecheck.py                # the Site stage of `validate --release` (§4.3)
│   ├── checklinks.py               # `check-links`: internal links and anchors of the built site
│   ├── golden.py                   # `golden`: the golden math corpus through KaTeX and pandoc → Typst
│   ├── figures/                    # house.mplstyle palette.py core.py keypoints.py plot.py signals.py
│   │                               # circuit.py block.py graph.py labels.py builtins.py
│   │                               # finalize.py validate.py child.py runner.py
│   ├── check.py  verify.py  blind.py   # (Phase 5) check-script API, runner + ledger, blind views
│   ├── pdf.py  cheatsheet.py       # (Phase 4) assemble → pandoc → typst; page-fit loop
│   ├── ingest.py                   # (Phase 6) scan, copy, page text, chunk plan
│   ├── plan.py                     # (Phase 5) deterministic scheduler
│   ├── progress.py                 # (Phase 5) import browser export, examiner log, report and mastery
│   ├── status.py                   # (Phase 6) pipeline state derived from outputs
│   └── calc.py                     # (Phase 5) `studykit calc "<sympy>"` for tutor and examiner
├── pandoc/
│   ├── defaults/common.yaml web.yaml typst.yaml json.yaml
│   ├── filters/studykit.lua + lib/{guard,blocks,mcq,math,figures,alttext,refs,meta,i18n,solutions}.lua
│   └── math-denylist.json          # denied math constructs and their replacements (§2.3), read by math.lua and lint
├── typst/
│   ├── studykit.typ                # house library; a Phase 3 stub with the API the filter calls (Phase 4: the real look)
│   └── pandoc-template.typ         # ~15 lines; imports the house library
├── site/                           # Astro (kept out of the repo root so Vite never watches .venv)
│   ├── package.json  pnpm-workspace.yaml  pnpm-lock.yaml  astro.config.mjs  tsconfig.json
│   ├── pagefind.yml  playwright.config.ts
│   ├── src/content.config.ts
│   ├── src/loaders/pandoc.ts       # custom content loader over `studykit render`
│   ├── src/lib/{katex,figures,courses,store,scoring,shuffle,leitner,answer,stats,plan,format,html,findings,types}.ts
│   ├── src/lib/sys.mjs             # the only module with node: imports (the site has no @types/node)
│   ├── src/elements/*.ts           # custom elements (§3.2), dashboard.ts (fills the shell's placeholders), util.ts, index.ts
│   ├── src/layouts/  src/pages/  src/components/  src/scripts/site.ts
│   ├── src/styles/{tokens,base,content,elements,code,print}.css
│   ├── scripts/check-math.mjs      # KaTeX strict check, called by the Math stage (lint, validate) and `golden`
│   ├── scripts/pagefind.mjs        # search index after `astro build` (§3.5)
│   └── tests/unit/*.test.ts  tests/e2e/*.spec.ts  tests/elements/ (harness with its own Playwright config and tsconfig.json)
├── schemas/*.schema.json           # generated from pydantic; committed; drift-checked by `just test`
├── examples/
│   ├── sample-course/              # self-written German mini course `sample-course` using every feature (CI fixture)
│   └── sample-materials/           # (Phase 6) self-written Typst sources for fake slides, exercise sheet, exam + one rasterised "scan"
├── tests/py/  tests/golden/{math.md,math-denied.md,math.typ.snap,blocks.md,mcq.md,figures/}
├── tests/fixtures/{bad/<SK-CODE>/,courses/mini/,pandoc/{ok,bad}/,figures/gallery/}
├── .claude/
│   ├── settings.json
│   ├── agents/                     # (Phase 5/6) ingester.md exam-analyst.md author.md verifier.md tutor.md examiner.md
│   └── skills/                     # (Phase 5) §5.2
└── courses/README.md               # the only tracked file under courses/
```

`.gitignore` entries:
- `/courses/*` and `!/courses/README.md`
- `/.tools` (no trailing slash, so a symlinked `.tools` is ignored too), `/.venv/`, `/.cache/`, `node_modules/`, `__pycache__/`
- `/site/dist/`, `/site/.astro/`, `**/_build/`
- `.claude/settings.local.json`, `.claude/agent-memory*/`, `.claude/worktrees/`
- `.DS_Store`

`site/.gitignore` ignores `/public/pagefind/` (§3.5).

`STUDYKIT_COURSES_DIR` defaults to `courses/`. The justfile makes it absolute, relative to the
repository root. Without just, a relative value means different things: Python resolves it
against the working directory, the site (`src/lib/sys.mjs`) against `site/`. CI points it at
`examples/`; validate's Site stage points it at a temporary directory outside the repository.

## 2. Content schema

### 2.1 Per-course directory

```
courses/<id>/                       # id: ^[a-z0-9][a-z0-9-]{1,39}$
├── course.yaml
├── overview.md                     # top-level overview, first tab (§2.12)
├── summary/<nn>-<topic>.md         # one chapter per topic, ordered by nn
├── exercises/<topic>/<ex-id>.md    # one exercise per file
├── mc/<topic>.md                   # one MC bank per topic  ← MC section
├── exams/<exam-id>/exam.yaml  NN-<task-id>.md  mc.md?
├── cheatsheet.md
├── plan.yaml                       # written by `studykit plan` (Phase 5), never by an LLM; until then by hand
├── figures/<slug>.py
├── checks/<item-id>.py | <item-id>.json    # (Phase 5) verifier output
├── sources/raw/*.pdf  manifest.yaml  text/<doc>/p0001.txt  notes/<chunk>.md  outline.md
├── analysis/exam-profile.yaml  notation.yaml
├── state/verify/<item-id>.json     # (Phase 5) ledger, one file per item (no locking)
├── progress/browser/*.json  examiner.jsonl  mastery.json  report.md    # (Phase 5)
├── _history/<timestamp>/…          # (Phase 5) copies saved by /regenerate before overwriting
└── _build/{index.json,figures,typ,pdf,blind,logs}
```

Discovery (`content.py`) knows the content kinds above (course, overview, summary, exercise,
mc, exam, exam task, exam MC, cheat sheet, plan, figure scripts, exam profile, notation,
manifest, outline). It never enters `_build`, `_history`, `state`, `progress`, `checks`,
`sources/raw`, `sources/text` and `sources/notes`; any other file in the course is
SK-STRUCT-PATH.

**Schemas.** The pydantic models in `model.py` are the single source. `just schema` exports them to `schemas/*.schema.json`, which editors use through `# yaml-language-server: $schema=…`; `just test` fails when the committed files are stale (`schema export --check`). `analysis/exam-profile.yaml`, `analysis/notation.yaml` and `sources/manifest.yaml` have no model yet and get only the YAML lint; validate reads the profile's archetype ids and the manifest's document ids and page counts. The site declares only a minimal `astro/zod` schema for the fields it renders, so a site that no longer matches the data fails the strict build of the sample course.

**IDs.**
- Kebab-case ASCII, unique per course, with prefixes `ex-`, `mc-<topic>-NNN`, and `<prefix>-tN` for exam tasks (any kebab prefix, e.g. `pk1-t1` in `probeklausur-1`).
- IDs are never renamed. Retired IDs go into `course.yaml: retired_ids`, and lint rejects reusing one.

**YAML rules** (linted from PyYAML parser events):
- Double-quoted scalars are not allowed, because `"\frac"` silently becomes a form feed.
- Any value containing a backslash must be single-quoted or a `|-` block scalar.
- Control characters are rejected.
- `course.yaml` may not contain LaTeX at all.

### 2.2 `course.yaml`

```yaml
# yaml-language-server: $schema=../../schemas/course.schema.json
schema: 1
id: get2
title: Grundlagen der Elektrotechnik 2
short: GET2
lang: de                        # language of generated content; UI chrome stays English
semester: WS 2026/27
exam:
  date: 2027-02-15              # null = unknown → placeholder in the plan, the report warns
  duration_min: 120
  points: 100
  format: written               # written | mc | oral | mixed
  aids: ['Nicht programmierbarer Taschenrechner', 'Selbst geschriebenes Formelblatt']
  mc:
    present: true               # from the exam profile, else from the user
    types: [single, multi, kprim]
    scoring: all-or-nothing     # all-or-nothing | partial | kprim
    negative_marking: false
cheatsheet: {allowed: true, max_pages: 2}   # validator caps at 3
study: {start: 2026-11-02, hours_per_week: 8, blocked: ['2026-12-21..2027-01-06']}
topics:                         # the only allowed topic ids; order = teaching order; prerequisites acyclic
  - {id: gleichstrom,  title: Gleichstromnetzwerke,          weight: 0.15, prereq: []}
  - {id: wechselstrom, title: Komplexe Wechselstromrechnung, weight: 0.30, prereq: [gleichstrom]}
  - {id: rc-filter,    title: RC-Filter und Bode-Diagramm,   weight: 0.25, prereq: [wechselstrom]}
focus: [wechselstrom]
skip: []
targets: {exercises_per_topic: auto, mc_per_topic: auto, mock_exams: 2}   # auto = f(weight)
retired_ids: []
status: draft                   # draft | ready; /register-new-subject sets ready when publish is green
```

### 2.3 Markdown conventions: one dialect, one parser

**Reader:** `commonmark_x-smart-raw_html-raw_attribute-yaml_metadata_block-alerts-emoji`.
- `studykit.pandoc` blanks the frontmatter (line numbers stay right) before pandoc reads a
  file; the site renders through `studykit render`, so there is one pandoc call site.
- Smart quotes are off; write „…“ directly.
- Raw HTML is an error (SK-BLOCK-RAW). pandoc 3.13 still produces RawBlock/RawInline for
  commonmark_x despite `-raw_html`, so `guard.lua` rejects them; raw Typst needs
  `raw_attribute`, which is off.

**Container blocks.** This is a closed list. Every fence has a blank line before and after it. Unknown classes, and any paragraph that starts with `:::`, are hard errors in `guard.lua`.

| Block | Exact fence | Allowed in | Rule |
|---|---|---|---|
| `hint` | `::: hint` | exercise, exam task | 1–3, ordered: principle → set-up → key intermediate result |
| `solution` | `::: solution` | exercise, exam task | exactly one, the last block |
| `definition` `theorem` `example` `note` `warning` `takeaways` | `::: definition` … | summary; cheat sheet allows only definition, note and warning | if the first child is a paragraph made of one bold span, it becomes the box title |
| `mcq` | `:::: {.mcq #mc-rc-filter-003 type="single" difficulty="2"}` | `mc/*.md`, `exams/*/mc.md` | the only block with attributes; exactly 4 colons |
| `explanation` | `::: explanation` | inside `mcq` | exactly one |

**Math** is the subset that both KaTeX and texmath handle. KaTeX checks it in strict mode, and pandoc→Typst checks it with `--fail-if-warnings` plus `math.lua`.
- Inline math is `$x$`, with no space just inside the dollars and no digit right after the closing `$`.
- Display math puts `$$` alone on a line, with no blank lines inside.
- Units are written `3{,}3\,\mathrm{k\Omega}`. Use `{,}` for the German decimal comma, `\mathrm{j}` for the imaginary unit and `\underline{U}` for phasors. Words go inside `\text{…}`.
- Allowed environments: `aligned`, `gathered`, `cases`, `pmatrix`, `bmatrix`, `Bmatrix`.
- **Denied, and the lint names the replacement:**

  | Denied | Use instead |
  |---|---|
  | `\overset`, `\stackrel` | `:=`, `\Rightarrow`, or `\;\circ\!-\!\bullet\;` for a Laplace correspondence |
  | `\xrightarrow`, `\xleftarrow` | `\Rightarrow`/`\to` (`\Leftarrow`/`\gets`), with the condition in prose |
  | `\underset` | a plain subscript, or say it in prose |
  | `\color`, `\textcolor` | no colour in formulas; emphasise in the text |
  | `\tag`, `\label`, `\eqref`, `\ref` | name the formula in prose |
  | `vmatrix`, `Vmatrix` | `\left\|\begin{matrix}…\end{matrix}\right\|` |
  | `array`; `matrix` outside `\left( \right)`, `\left[ \right]`, `\left\| \right\|`, `\left\{ \right\}`; `\hline` | `pmatrix`/`bmatrix`/`Bmatrix`, or a Markdown table |
  | `\big`, `\Big`, `\bigg`, `\Bigg` and their `l`/`r`/`m` forms | `\left( … \right)`, or plain delimiters |
  | `\\|`, `\left\lVert` | `\lVert … \rVert` without `\left`/`\right`; `\left.…\right\|_{…}` for an evaluation bar |
  | `\mathsf` | `\mathrm` (e.g. `^\mathrm{T}`) |
  | `\operatorname*` | `\operatorname{…}` with a normal subscript, or `\max`, `\min`, `\lim` |
  | `\limits` | a normal subscript and superscript |
  | `\SI`, `\qty`, `\si`, `\pu` | `\,\mathrm{…}`, e.g. `3{,}3\,\mathrm{k\Omega}` |
  | `\R`, `\N` | `\mathbb{R}`, `\mathbb{N}` |
  | `\ce` | `\mathrm{…}` with sub- and superscripts, e.g. `\mathrm{H_2O}` |
  | `\def`, `\gdef`, `\edef`, `\let`, `\newcommand`, `\renewcommand`, `\providecommand`, `\DeclareMathOperator` | write the expansion out |

  `pandoc/math-denylist.json` holds these entries with the exact hints the lint prints.

- **No custom macros:** no `\newcommand` and no `\def` (SK-MATH-DENIED).
- **No Markdown block markers inside display math:** a line inside `$$ … $$` must not start
  with `=`, `-`, `+`, `*`, `#`, `>` or `1.`; pandoc then reads a heading or list instead of
  math, on the website *and* in the PDF. Keep `=` at the end of the previous line.
- **No space command between two digits** (`10\,000`, `1\,5`; also `\:` `\;` `~` …): both
  engines set a gap, so the number reads as two (SK-MATH-THINSPACE). Write `10000`, `10^4`
  or `1{,}5`.
- **Non-ASCII characters only inside `\text{…}`**; KaTeX strict rejects them elsewhere
  (SK-MATH-KATEX).

**Verified in Phase 1** (`tests/golden/`, pandoc 3.13, Typst 0.15.1, KaTeX 0.16.47):
- 109 corpus formulas render in KaTeX strict and compile through pandoc → Typst without
  warnings, and the rendered PDF was reviewed page by page. `math.typ.snap` pins the Typst
  translation so any drift after a toolchain bump fails `just test`.
- Hard failures (kept in `math-denied.md`, which must keep failing): `\textcolor`, `\label`,
  `\eqref`, `\ref`, `vmatrix`, `Vmatrix`, `\SI`, `\qty`, `\R`, `\N`, `\ce`, `\pu`, `\def`,
  non-ASCII letters outside `\text{}`.
- **Silent mis-conversions** (compile cleanly but render wrong in Typst, so only the lint
  can stop them): `\tag` and `\color` are dropped; bare `matrix`/`array` become alignment
  rows instead of a matrix; `\overset`/`\stackrel` become superscripts; `\xrightarrow` loses
  its label stretch; `\operatorname*` subscripts do not go below; `\left\|…\right\|_2`
  and `\|…\|_2` put the index under the bar; `\mathsf` comes out italic.
- **Fixed in the Typst branch of `math.lua`** (Phase 3), because the source is right and
  only the translation is off:
  - decimal comma: `3{,}3` becomes `3\,3`, which Typst sets as "3, 3"; rewrite
    digit `\,` digit to digit `","` digit;
  - `cases`: Typst puts no gap between value and condition ("0t < 0"); insert `quad` after
    each column separator inside `cases(…)`.

**Other rules:**
- **Figures:** `![Caption, doubles as alt text](fig:<slug>)` alone in its paragraph, with no attributes. The size comes from the figure script. The caption may hold inline math: the page and the PDF render it, and the PDF's alt text reads it as plain text (`lib/alttext.lua`: `$\underline{U}_C$` → U_C).
- **Links:** `[…](ex:<id>)`, `(mc:<id>)`, `(topic:<id>)`, `(exam:<id>)`, and `(src:<doc>#p=12)`, which opens the lecture PDF at that page (`src:<doc>` alone opens the PDF). Every target must exist. `mc:` reaches practice-bank questions only; link an exam with `exam:`. External `https://` and `mailto:` links need descriptive text.
- **Tables:** pipe tables split a row at every `|` before they read math or code, so a table row has no `|` inside inline math (write `\lvert … \rvert`, `\lVert … \rVert`, `\mid`) and only escaped `\|` inside inline code (SK-BLOCK-TABLE).
- **Line breaks:** a line that ends in a letter and a hyphen, followed by a line that starts with a letter, shows as „RC- Tiefpass“; keep the hyphenated word on one line (warning SK-BLOCK-HYPHEN; suspended compounds such as „Ein- und Ausgang“ are not reported).
- **Subtasks:** `**a)**` paragraphs.
- **Code:** fenced, with exactly one language from `python matlab octave c cpp vhdl verilog systemverilog julia text` and no attributes.
- **Forbidden:** raw HTML or any raw block (SK-BLOCK-RAW); H1 in the body, heading attributes, footnotes, and `{…}` attributes on spans, inline code and tables (SK-BLOCK-MARKDOWN), because the HTML writer copies attributes onto the element, so an `onclick` would reach the page; `mcq` is the only element with attributes; bare URLs, autolinks, links whose text is their URL, `www.…`, and links with attributes (SK-REF-LINK); any image that isn't `fig:`.

### 2.4 Summary chapter (`summary/03-rc-filter.md`)

```markdown
---
topic: rc-filter
title: RC-Filter und Bode-Diagramm
objectives:
  - 'Übertragungsfunktion eines RC-Tiefpasses herleiten'
  - 'Grenzfrequenz berechnen und im Bode-Diagramm ablesen'
sources: [{doc: vl-05, pages: '12-30'}]
---

## Übertragungsfunktion

$$
\underline{H}(\mathrm{j}\omega) = \frac{1}{1 + \mathrm{j}\omega RC}
$$

![Bode-Diagramm des RC-Tiefpasses](fig:rc-bode)

::: warning
**Häufiger Fehler**

$\omega_\mathrm{g}$ und $f_\mathrm{g}$ unterscheiden sich um den Faktor $2\pi$ ([VL 5, S. 14](src:vl-05#p=14)).
:::

Übung: [Grenzfrequenz RC-Tiefpass](ex:ex-rc-tp-grenzfrequenz)
```

Every chapter page ends automatically with a three-question "Test yourself" quiz drawn from that topic's MC bank.

### 2.5 Exercise (`exercises/rc-filter/ex-rc-tp-grenzfrequenz.md`)

```markdown
---
id: ex-rc-tp-grenzfrequenz
title: Grenzfrequenz eines RC-Tiefpasses
topic: rc-filter
difficulty: 2                     # 1 worked-example level … 4 exam-hard
kind: compute                     # compute | derive | concept | sketch | code
minutes: 10
source: {doc: uebung-04, page: 2, relation: adapted}    # original | adapted | inspired
answers:                          # the key; the website's answer check and verify.py (Phase 5) both use it
  - {key: fg,  label: '$f_\mathrm{g}$', value: 1591.55, unit: Hz, rtol: 1.0e-3}
  - {key: Hdb, label: '$|\underline{H}(f_\mathrm{g})|$', value: -3.0103, unit: dB, atol: 0.01}
---

Gegeben ist der RC-Tiefpass mit $R = 1\,\mathrm{k\Omega}$ und $C = 100\,\mathrm{nF}$.

![RC-Tiefpass](fig:rc-tp-schaltung)

**a)** Bestimmen Sie die Grenzfrequenz $f_\mathrm{g}$.

**b)** Wie groß ist $|\underline{H}(f_\mathrm{g})|$ in dB?

::: hint
Bei der Grenzfrequenz sind Wirk- und Blindwiderstand betragsmäßig gleich.
:::

::: hint
Setzen Sie $R = \frac{1}{2\pi f_\mathrm{g} C}$ und lösen Sie nach $f_\mathrm{g}$ auf.
:::

::: solution
**a)** $f_\mathrm{g} = \frac{1}{2\pi RC} \approx 1{,}59\,\mathrm{kHz}$

**b)** $20\log_{10}\frac{1}{\sqrt{2}} \approx -3{,}01\,\mathrm{dB}$
:::
```

- Answer `label`, and the rubric text in exam tasks, are plain text plus inline `$…$` math only. They are linted for that and rendered by a 20-line splitter, the same way on the web and in the PDF.
- Symbolic answers are written `{key: H, expr: '1/(1+s*R*C)', symbols: [s, R, C]}`. The website's answer check (`lib/answer.ts`) evaluates input and reference at random positive sample points with complex arithmetic; `verify.py` (Phase 5) adds SymPy simplification.
- The website reads numbers in German or English notation with an SI prefix and unit (`1,59 kHz`) and accepts them within `atol + rtol·|value|` in the answer's unit; `rad/s` and `1/s` count as the same unit.
- The hint-leak lint (warning SK-MATH-HINT-LEAK) flags a number in a hint that matches an `answers` value within its tolerance.

### 2.6 MC bank: the multiple-choice section (`mc/rc-filter.md`)

```markdown
---
topic: rc-filter
title: RC-Filter und Bode-Diagramm
---

:::: {.mcq #mc-rc-filter-003 type="single" difficulty="1" source="uebung-04:2"}
Ein RC-Tiefpass hat $R = 1\,\mathrm{k\Omega}$ und $C = 100\,\mathrm{nF}$. Wie groß ist $f_\mathrm{g}$?

- [x] $1{,}59\,\mathrm{kHz}$

  $f_\mathrm{g} = 1/(2\pi RC)$.

- [ ] $10\,\mathrm{kHz}$

  Das ist $1/(RC)$, also $\omega_\mathrm{g}$ in $\mathrm{s^{-1}}$: Faktor $2\pi$ vergessen.

- [ ] $159\,\mathrm{Hz}$

  Zehnerpotenz falsch: mit $C = 1\,\mathrm{\mu F}$ gerechnet.

- [ ] $62{,}8\,\mathrm{kHz}$

  $2\pi/(RC)$ statt $1/(2\pi RC)$.

::: explanation
Bei $f_\mathrm{g}$ gilt $|\underline{Z}_C| = R$, also $2\pi f_\mathrm{g} RC = 1$.
:::
::::

:::: {.mcq #mc-rc-filter-011 type="multi" difficulty="2" pin-last="true"}
Welche Aussagen gelten für den RC-Tiefpass erster Ordnung?

- [x] Oberhalb von $f_\mathrm{g}$ fällt der Betrag mit $20\,\mathrm{dB}$ pro Dekade.

  Ein Pol erster Ordnung.

- [ ] Bei $f_\mathrm{g}$ beträgt die Phase $-90^\circ$.

  Bei $f_\mathrm{g}$ ist $\arg\underline{H} = -\arctan 1 = -45^\circ$.

- [ ] Keine der Aussagen ist richtig.

  Die erste Aussage ist richtig.

::: explanation
…
:::
::::

:::: {.mcq #mc-rc-filter-020 type="kprim" difficulty="2"}
Beurteilen Sie für den RC-Tiefpass:

- [x] Bei $f = f_\mathrm{g}$ gilt $|\underline{H}| = 1/\sqrt{2}$.

  Definition der Grenzfrequenz.

- [x] Bei $f = f_\mathrm{g}$ beträgt die Phase $-45^\circ$.

  $\arg\underline{H} = -\arctan(1)$.

- [ ] Für $f \gg f_\mathrm{g}$ fällt $|\underline{H}|$ mit $40\,\mathrm{dB}$ pro Dekade.

  Erste Ordnung: $20\,\mathrm{dB}$ pro Dekade.

- [ ] Für $f \to 0$ gilt $|\underline{H}| \to 0$.

  Der Gleichanteil wird durchgelassen: $|\underline{H}| \to 1$.

::: explanation
…
:::
::::
```

**Format.**
- Each list item has exactly two paragraphs:
  - The first is the option text. For Kprim it is a statement, and `[x]` means "true".
  - The second is the required `why`. For a distractor it names the mistake being modelled.
- Attributes:

  | Attribute | Values |
  |---|---|
  | `type` | `single` / `multi` / `kprim` |
  | `difficulty` | 1–4 |
  | `tags` | optional, comma-separated |
  | `source` | optional, `doc:page` |
  | `pin-last` | optional; keeps the last option last after shuffling, only for a "none of these" option |

**How pandoc reads it** (verified in Phase 3 with pandoc 3.13, pinned by `tests/py/test_filters.py`):
- Loose task lists keep their checkboxes. Each option arrives as
  `[Para [Str "☒" | "☐", Space, …option…], Para […why…]]`, so the format above works as
  written and the tight-list fallback from §7 risk 4 is not needed.
- An item without a checkbox ends the task list and pandoc starts a new list after it;
  `mcq.lua` joins consecutive lists and reports "option N is not a task item".
- `:::` and `::::` look the same in the AST. The guard checks fence lengths on the source
  lines whenever pandoc reads a file (always through `studykit.pandoc`); `lint.py` checks
  them too.
- The PDF shuffle is deterministic: the FNV-1a 32-bit hash of the question id seeds
  mulberry32, then Fisher-Yates runs from the last option down (a `pin-last` option is left
  out), and the keys (A)–(F) are assigned after shuffling.

**Lint rules** (`mcq.lua` and the MC stage of `validate.py`, which `lint` runs too):
- `single` has 3–5 options with exactly one `[x]`.
- `multi` has 4–6 options with at least one `[x]` and at least one `[ ]`.
- `kprim` has exactly 4 options.
- Every option has a `why`, and there is exactly one explanation.
- No "all of the above".
- Explanations never refer to options by letter, because options are shuffled.
- *(Phase 5)* Numeric questions require a check script. The verifier writes it after
  authoring, so the Verification stage checks this, not lint.

**Bank-level warnings** (SK-MCQ-BIAS, for banks with at least four single-choice questions):
- the correct option is the strictly longest one in more than half of them
- after the deterministic PDF shuffle, one letter is the correct answer in more than half of them

**Generation targets.**
- `mc_per_topic: auto` gives 10–25 questions per topic, scaled by weight
  (`max(10, ⌈25 · weight⌉)`, at most 25; SK-COV-MC).
- The type mix follows the exam profile. Without one it is 60% single, 25% multi and 15% Kprim.
  Validation only warns when a type of `course.exam.mc.types` is missing from a bank.
- Distractors come from a catalogue of electrical-engineering misconceptions: a forgotten 2π, √2 (amplitude vs. RMS), dB vs. linear, the sign of the phase, series vs. parallel, a wrong power of ten, degrees vs. radians.

**Scoring** (`site/src/lib/scoring.ts`; the Phase 5 `progress.py` must mirror it). An option is
decided right when it is selected and correct or unselected and wrong; a Kprim statement
left open is wrong.

| Type | Score |
|---|---|
| single | 1 or 0 |
| multi, all-or-nothing | 1 only if the selected set equals the correct set |
| multi, partial | max(0, (options decided right − options decided wrong) / n) |
| multi, kprim | the Kprim rule over the n options: all right → 1, one wrong → 0.5, otherwise 0 |
| kprim | 4/4 → 1, 3/4 → 0.5, otherwise 0 |

`course.exam.mc.scoring` (`all-or-nothing` | `partial` | `kprim`) picks the multi-select
rule, in practice and in exams. Practice scores lie in [0, 1]. Only exam mode applies
negative marking, when `course.exam.mc.negative_marking` is true (`examScore`):
- a question left blank scores 0;
- multi with the partial rule scores (decided right − decided wrong) / n, down to −1;
- any other answered question scores its normal score when that is above 0, else −1;
- the MC part as a whole never goes below 0 (`examPartPoints`).

**Check script for a numeric question** (*Phase 5*; `checks/mc-rc-filter-003.py`, written blind by the verifier):

```python
from math import pi
from studykit.check import mc_numeric

R, C = 1e3, 100e-9
mc_numeric(
    correct=1 / (2 * pi * R * C),
    options={"A": 1.59e3, "B": 10e3, "C": 159.0, "D": 62.8e3},  # source order, SI values
    mistakes={"B": 1 / (R * C), "C": 1 / (2 * pi * R * 1e-6), "D": 2 * pi / (R * C)},
    rtol=5e-3,
    min_separation=0.05,
)
```

The runner asserts four things:
1. Exactly the `[x]` options match `correct`.
2. Each distractor reproduces its named mistake.
3. Every distractor differs from the correct value by more than 5%.
4. Each option's text parses to its stated value. If the text can't be parsed, this is a warning.

**Conceptual questions** (*Phase 5*): the verifier answers blind into `checks/<id>.json`:

```json
{"answer": ["A","C"], "confidence": "high", "ambiguous": false, "reason": "…"}
```

The runner compares that answer with the `[x]` marks. If the verifier marks the question ambiguous, it is disputed.

### 2.7 Mock exam (`exams/probeklausur-1/`)

```yaml
# exam.yaml
schema: 1
id: probeklausur-1
title: Probeklausur 1
duration_min: 120
points: 100
pass_points: 50
aids: inherit
modeled_on: [klausur-ws2324, klausur-ss24]
tasks: [01-pk1-t1.md, 02-pk1-t2.md, 03-pk1-t3.md, 04-pk1-t4.md]
mc: {file: mc.md, points_each: 2}        # present only if course.exam.mc.present
```

- Task files use the exercise schema plus `kind: exam-task`, `points`, an `archetype` (which must exist in `analysis/exam-profile.yaml`, SK-REF-MISSING; without a profile the check is skipped with a note), and a `rubric`. The rubric is a list of `{points, criterion}`, and its points must add up to `points` (SK-SCHEMA-RUBRIC).
- Task ids are `<prefix>-tN` with any kebab prefix; task file names are `NN-<task-id>.md`.
- `mc.md` is a normal MC bank, but its questions appear only inside the exam, never in the practice banks.
- **Validation:**
  - task and MC points sum to `points` (SK-STRUCT-POINTS); `pass_points` ≤ `points`
  - with `--release`: points and time within ±10% of the real exam in `course.yaml: exam`
    (SK-COV-EXAM)
  - *(planned)* the archetype mix matches the profile, and an n-gram similarity above 0.6 to
    the extracted past-exam text produces a "too close to source" warning

### 2.8 Cheat sheet (`cheatsheet.md`)

- **Frontmatter:** `title`, `max_pages`, which must be ≤ `course.cheatsheet.max_pages` ≤ 3, and `priority` (topic IDs).
- **Body:** a `##` section per topic containing formulas, small tables, definition/note/warning boxes, and small figures.
- **Not allowed:** exercises and hints.

### 2.9 Study plan (`plan.yaml`)

`studykit plan` (Phase 5) is deterministic. Claude writes only the `goal` and `note` text
afterwards. Until the scheduler exists, `plan.yaml` is written by hand against
`schemas/plan.schema.json`, as in the sample course; the site and validate already read it
(plan refs are checked as SK-REF-SCHEME and SK-REF-MISSING).

```yaml
schema: 1
generated: 2026-10-29
exam_date: 2027-02-15
sessions:
  - id: s-2026-11-02-a
    date: 2026-11-02
    minutes: 90
    kind: learn           # learn | review | mixed | mock-exam | cheatsheet | buffer
    topics: [gleichstrom]
    goal: Knotenpotentialverfahren sicher aufstellen
    tasks:
      - {do: read, ref: 'topic:gleichstrom'}
      - {do: exercises, refs: ['ex:ex-knoten-01', 'ex:ex-masche-02']}
      - {do: mc, topic: gleichstrom, count: 10}
  - {id: s-2027-02-01-a, date: 2027-02-01, minutes: 150, kind: mock-exam, tasks: [{do: exam, ref: 'exam:probeklausur-1'}]}
```

How the scheduler places sessions:
- Learning time per topic is proportional to weight × mean difficulty, multiplied by 1.5 for focus topics, in prerequisite order.
- Reviews follow at +1, +3 and +7 days.
- Mock exams go into the last 14 days, and the last day is for the cheat sheet.
- `--replan` keeps past sessions and puts weak topics from `progress/mastery.json` first.

### 2.10 Verification ledger (`state/verify/<item-id>.json`, Phase 5)

```json
{"item":"ex-rc-tp-grenzfrequenz","content_sha256":"…","check_sha256":"…","method":"script",
 "result":"pass","answers":{"fg":{"claimed":1591.55,"computed":1591.549,"rel_err":3e-7}},
 "verified_at":"2026-10-30T10:12:00Z"}
```

- `result` is one of `pass`, `fixed`, `disputed` or `quarantined`.
- If the content hash no longer matches, the entry is stale and must be verified again.
- Summary chapters and the cheat sheet get formula audits too, in `checks/sum-<topic>.py`.

### 2.11 Progress

**Browser.** All progress is one versioned localStorage document per course, under the key `studykit:v1:<course>`:

```json
{"schema":"studykit-progress/1","course":"get2","exported_at":"2026-11-20T18:03:00Z","items":{
  "mc:mc-rc-filter-003":{"h":"9c01aa12","box":3,"due":"2026-11-24",
     "attempts":[{"t":"…","chosen":["A"],"score":1,"conf":"sure","ms":42000}]},
  "ex:ex-rc-tp-grenzfrequenz":{"h":"3f2a91c0","hints":2,"answer_ok":true,"rating":"partial","box":1,"due":"2026-11-21"},
  "exam:probeklausur-1":{"attempts":[{"started":"…","duration_s":6900,"points":{"pk1-t3":12,"mc":14},"total":71}]},
  "plan:s-2026-11-02-a":{"done":true}}}
```

- The document is the export format; `studykit.model.Progress` validates it and
  `schemas/progress.schema.json` is its schema. `lib/store.ts` owns it: every access is
  wrapped in try/catch, a write that fails is kept in memory so the page still works, and
  a document with a newer schema is read but never written.
- `h` is a content hash computed at build time (the first 8 hex digits of the sha256 of the
  rendered `<sk-mc>`, exercise or exam task). When it changes, the site shows "Content
  changed since your attempt."
- MC entries keep at most 100 attempts. Exercise entries keep no review day: `box` and
  `due` come from the self-assessment (§3.2, Leitner).
- `hints` counts the hints of the attempt the rating belongs to (before the first rating,
  of the attempt under way). Once a rated exercise's due day has come, working on it again
  is a new attempt: its hints are kept in the session key until it is rated, and the
  rating stores them.
- Misconceptions are not stored: an MC item whose last attempt was `sure` with a score
  below 1 is one.
- An export button downloads `studykit-progress-<course>-<date>.json`. Import merges the
  file back in as a union: attempts are combined without duplicates, schedules come from
  the side with the later attempt (for exercises, the later due day), hint counts take the
  maximum, and a correct answer check or a done session stays done. Reading and import
  drop what does not validate, so an export always validates: an attempt needs an ISO 8601
  timestamp (as Python's `datetime.fromisoformat` reads it), and `ms`, `hints` and
  `duration_s` become safe integers. A file that names no course is refused.
- Two more keys are never exported: `studykit:v1:<course>:session` holds runtime state (a
  running exam's start time, MC answers and rubric ticks; `ex:<id>` `{due, hints}` for an
  exercise review that is not rated yet), and `studykit:theme` holds `light`, `dark` or
  `system`.
- The site requests `navigator.storage.persist()`; the progress page says whether the
  browser granted it.

**Figures in the browser** (`lib/stats.ts`, shown by the shell's placeholders and `<sk-progress>`):
- Accuracy of a topic: the mean score of its last 10 MC attempts.
- Mastery: topic accuracies weighted by topic weight over the topics not skipped; a topic
  without attempts counts 0; none until something is answered. The course cards and the
  progress page show it, and it replaces the build-time value from `mastery.json` once this
  browser has answers.
- Reviews due: MC questions the Leitner schedule has due today; the progress page also
  counts exercises due for review.
- Exercise status: `new`, `started` (hints opened or the answer checked, not rated yet),
  `not-yet`, `partial` or `solved`.

**Repo side** (Phase 5):
- `/import-progress` copies an export into `progress/browser/`.
- The examiner appends results through `studykit progress log`.
- `studykit progress report` computes `mastery.json` and `report.md` deterministically, with
  the same accuracy and mastery as `lib/stats.ts`:
  - per-topic accuracy over the last 10 attempts
  - exam-task score fraction
  - examiner results
  - misconceptions (last attempt sure but not fully right)
- The site reads `mastery.json` at build time (the `mastery` collection), so examiner findings show up on the course home page.

### 2.12 Overview (`overview.md`)

The first thing a student sees for a subject: a top-level picture before any detail.

```markdown
---
title: Überblick
---

## Worum geht es?
## Themenkarte

![Themen und ihre Abhängigkeiten](fig:topic-map)

## Wie die Themen zusammenhängen
## Die Klausur auf einen Blick
## So lernst du dieses Fach
## Voraussetzungen
```

- The six H2 sections are required, in this order. Their titles are localised by `i18n`
  (English: Big picture, Topic map, How the topics connect, Exam at a glance, How to study
  this subject, Prerequisites); lint checks them by position and count, not by text.
- `fig:topic-map` is built automatically for every course by `graph.topic_map(course)`
  from `course.yaml` topics and `prereq`: box height encodes weight, focus topics are
  highlighted, skipped topics are greyed out. No figure script is needed.
- "Exam at a glance" is written from `analysis/exam-profile.yaml` (format, duration, points,
  archetypes and their share, MC part, allowed aids).
- Links to topics use `topic:` references; every topic must be linked at least once.
- *(Phase 5)* Authored by `author` with `authoring/parts/overview.md`, first in the author
  wave so other parts can link to it. `/regenerate <course> overview` re-runs it.
- Web: `/c/<c>/` (the Overview tab). PDF *(Phase 4)*: `overview.pdf`, also the first chapter
  of `summary.pdf`.
- A missing `overview.md` is SK-STRUCT-MISSING (a warning, an error with `--release`); the
  six sections are SK-STRUCT-SECTIONS, checked on every run; SK-COV-OVERVIEW (`--release`)
  requires a `topic:` link to every topic that is not skipped.

## 3. Rendering pipelines

### 3.1 Shared front end: pandoc 3.13 with one Lua filter set

**Defaults files.**
- `common.yaml`:
  - `from: commonmark_x-smart-raw_html-raw_attribute-yaml_metadata_block-alerts-emoji`
  - `filters: [pandoc/filters/studykit.lua]`
  - `fail-if-warnings: true`
- `web.yaml`: `to: html5`, `syntax-highlighting: default`. Code tokens come out as classes, and `code.css` colours them for light and dark.
- `typst.yaml`: `to: typst`, `standalone: true`, `template: typst/pandoc-template.typ`, `syntax-highlighting: idiomatic`.
- `json.yaml`: `to: json` and the reader with `+sourcepos`, so findings carry `file:line:col`; used by lint and validate (Phase 5: blind views and verification). The filter only checks and returns the AST unchanged.

**Metadata.** `studykit.pandoc` builds the argv; the filter needs `-M sk-index` (the course's `_build/index.json`), `sk-course`, `sk-lang`, `sk-file` (the course-relative path, which decides the file kind), for Typst `sk-solutions` and `sk-figdir`, and optionally `sk-scope=course|file`. pandoc runs in the repository root on a temporary copy whose frontmatter is blanked.

**Findings.** The filter collects every finding of a document and prints them to stderr as `<sk-file>:<line>:<col> SK-CODE message (fix: …)`, then exits with status 65. A rule that validate checks too has the same code in both (e.g. SK-REF-FIGURE, SK-BLOCK-FENCE, SK-MCQ-KEY); rules only the filter sees have their own codes (SK-BLOCK-RAW, SK-BLOCK-MARKDOWN, SK-REF-LINK, SK-MATH-TYPST). A run without the metadata above, or with an unreadable index or `math-denylist.json`, is SK-PANDOC-FAIL.

**Lua modules.** `studykit.lua` branches on `FORMAT` (`html*`, `typst`, anything else: validation only).

| Module | What it does |
|---|---|
| `guard` | Fails on any paragraph starting with `:::`, unknown classes, blocks in the wrong file kind, nesting other than mcq→explanation (a block inside a list counts), fence lines that are not exactly `::: name`, `:::: {.mcq …}`, `:::` or `::::` (checked on the source lines), hint and solution count and position, code blocks without exactly one allowed language, raw HTML and other raw blocks, H1 in the body, footnotes, and `{…}` attributes on headings, spans, inline code and tables (the HTML writer would copy an `onclick` onto the element). |
| `blocks` | HTML: `<aside class="sk-block sk-{name}" data-block="{name}">` with a `sk-block-title` div; hints are `<details class="sk-hint" data-index="n">`, the solution `<details class="sk-solution">`. Typst: `#sk-box(kind:…, title:…)[…]`. |
| `mcq` | Reads the ☐/☒ task list (option text, why, explanation) and validates it. HTML: `<sk-mc data-id data-type data-difficulty data-topic data-pin-last>` (plus `data-tags`/`data-source` when set) with a `sk-stem` div, `<sk-opt data-key data-correct>` children holding `<div class="sk-opt-text">` and a hidden `sk-why`, and a hidden `sk-explanation`; options stay in source order (the site shuffles, and its loader adds `data-h`). Typst: options (A)–(F) with empty boxes in a seeded shuffle, plus answer-key entries. |
| `math` | Applies the denylist to every Math node. In HTML it emits `<sk-math data-tex="<base64>" data-display="0\|1"></sk-math>`. Base64 avoids entity-escaping problems, and since `guard` rejects raw HTML, authors cannot fake these elements. Also rejects environments outside the allowlist, non-ASCII outside `\text{…}` (SK-MATH-KATEX, so it shows up without KaTeX too) and a space command between two digits (SK-MATH-THINSPACE). Typst and json: each node is converted to Typst on its own, and a conversion warning is SK-MATH-TYPST, so the lint fails on what the PDF would fail on; Typst then gets two fixes from Phase 1 (decimal comma, `cases` gap). |
| `figures` | Checks `fig:` images (alone in the paragraph, no attributes, a caption; SK-REF-FIGURE, SK-REF-IMAGE, SK-REF-MISSING). HTML: a `<figure class="sk-fig" data-slug>` placeholder with a `sk-fig-slot` and the caption. Typst: `#figure(image("/courses/<c>/_build/figures/<slug>.svg", alt: …), caption: …)`; the path is relative to the Typst root, and a figure directory outside it is SK-PANDOC-FAIL. |
| `alttext` | Typst only: the figure's `alt:` text from the caption, with math read as plain text (`\underline{U}_C` → U_C, `\mathrm{k\Omega}` → kΩ). |
| `refs` | Resolves `ex:`, `mc:`, `topic:`, `exam:` and `src:` against a course ID index. HTML: `<a class="sk-ref sk-ref-{scheme}">` with route URLs (`mc:<id>` → `/c/<c>/mc/<topic>/#<id>`, `src:` → `/c/<c>/src/<doc>.pdf#page=<n>`). Typst: an in-document link, otherwise plain text such as „(→ Übung: Titel)“. `http(s)` and `mailto` links pass; bare URLs and links with attributes are SK-REF-LINK, other targets SK-REF-SCHEME. With `-M sk-scope=file` (`lint` and `validate --quick`) targets missing from the index are not reported. |
| `meta` | HTML: appends `<script type="application/json" id="sk-meta">` with headings (level, id, text) and items: the file's own index entry, then each MC question, as `{id, kind, topic, difficulty}` (MC items add `type`; difficulty is null when the index has none). |
| `i18n` | Labels in German and English (Hinweis, Lösung, Aufgabe, Punkte …). |
| `solutions` | Typst `-M sk-solutions=inline\|appendix\|none` (default appendix): hints, solutions and MC keys stay in place, move into an appendix with back-links, or are dropped. |

### 3.2 Website: Astro 7.4.2 static, pandoc loader, custom elements, plain CSS

**Packages** (exact pins; `pnpm-lock.yaml` committed; `"packageManager": "pnpm@11.22.0"`; `site/pnpm-workspace.yaml` sets `minimumReleaseAge: 10080`):

| Kind | Packages |
|---|---|
| dependencies | `astro 7.4.2`, `katex 0.16.47`, `yaml 2.9.1` (resolves Vite's optional peer; no site code imports it) |
| devDependencies | `typescript 6.0.3` (`@astrojs/check` peers ^5 or ^6), `@astrojs/check 0.9.12`, `@playwright/test 1.64.1`, `pagefind 1.5.2` |
| unit tests | `node --test` (Node 24 strips TypeScript types natively) |
| search | `pagefind` (CLI, run after `astro build`; see §3.5) |
| not used | remark/rehype, MDX, Tailwind, a UI framework, Mermaid, `@types/node` |

`package.json` scripts: `dev`, `build` (`astro build && node scripts/pagefind.mjs`), `preview`,
`check` (`astro check`), `test:unit`, `test:elements` and `e2e` (§4.4).

**`astro.config.mjs`:**
- `output: 'static'`
- `server: {host: 'localhost', port: 4321}`; `vite.server.strictPort` and `vite.preview.strictPort` are true (progress is tied to the origin)
- `vite.server.fs.allow: [repoRoot]`
- `devToolbar: {enabled: false}`
- It sets `STUDYKIT_SITE_ROOT` for `src/lib/sys.mjs`: pages are bundled into chunks, so build-time code cannot find the site from its own URL. `sys.mjs` is the only module with `node:` imports.
- The `markdown` section is unused.
- `ASTRO_TELEMETRY_DISABLED=1` is exported from the justfile.

`tsconfig.json` extends `astro/tsconfigs/strict` and includes only `src/` (and Astro's generated types).

**`content.config.ts`:**
- `courses`: `glob({pattern: '*/course.yaml', base})` with `base = STUDYKIT_COURSES_DIR ?? '../courses'` and a minimal Zod schema.
- `docs`: `pandocLoader({base})` (`src/loaders/pandoc.ts`). pandoc runs in Python, through the render bridge `studykit render <course> --known - --json` (`src/studykit/render.py`; `uv run --frozen`, or `.venv/bin/studykit` without uv), so the pandoc argv and the filter metadata exist once. Per course and sync:
  1. The loader sends the digests it already stores. The bridge rewrites `_build/index.json`, picks the overview, summary, exercise, MC-bank, exam-MC, exam-task and cheat-sheet files (rendered to HTML) and each `exam.yaml` (data only), and parses every frontmatter with the restricted PyYAML loader and the pydantic models (SK-YAML and SK-SCHEMA findings).
  2. Files whose digest the loader holds come back as `cached`. The bridge renders the rest with `pandoc -d common -d web` in a thread pool of CPU count. The digest is the sha256 of a format tag, the pandoc version, the `pandoc/` tree plus `render.py` and every studykit module it imports, the index, the frontmatter validation context (topics, `cheatsheet.max_pages`) and the file bytes.
  3. The loader removes the trailing `sk-meta` script and keeps its headings.
  4. It hashes each `<sk-mc>` and each exercise or exam-task fragment as the filter wrote it (first 8 hex digits of sha256) for the content hash `h` (§2.11).
  5. It replaces each `<sk-math>` with `katex.renderToString(tex, {displayMode, throwOnError: true, strict: 'error', trust: false})` (`lib/katex.ts`), and renders the inline math of the frontmatter labels (answer labels, rubric criteria, objectives) into `labels`.
  6. It stores `{id: '<course>/<rel>', data, rendered: {html, metadata: {headings}}}`, with the bridge digest behind a stamp of the loader and KaTeX versions, so a loader or KaTeX change re-renders everything.
  7. In dev the watcher re-syncs a course 150 ms after one of its `.md`/`.yaml` files changes (all courses when its `course.yaml` is gone); only files whose digest changed re-render, all of them when the index changed. Changes under `_build`, `_history`, `state`, `progress`, `checks`, `sources` and `analysis` are ignored.
- `plans` and `mastery`: `glob()` over `*/plan.yaml` and `*/progress/mastery.json` (read loosely until Phase 5 writes it).
- **Errors:** a document's findings (filter, schema, KaTeX in the body or a label) become a red error card at its top with `file:line:col`, the code and the message. With `STUDYKIT_STRICT=1` the load throws instead, and a courses directory without a course fails the build.

**Figures** are swapped in when the page renders. `lib/figures.ts` replaces each `data-slug` placeholder with the current `_build/figures/<slug>.web.svg` from the figure manifest, so the content cache can never serve a stale figure. Colours are `var(--fig-*)`, so the theme toggle also switches figures to dark mode. A missing figure is an error card in dev and fails a strict build.

**Routes** (UI in English; `<html lang>` set to the course language; page routes end in `/`):

| Route | Purpose |
|---|---|
| `/` | Course cards: exam countdown, mastery ring, number of MC reviews due today, next session |
| `/c/<c>/` | **Overview tab** (§2.12) with a compact Today panel on top: exam countdown and format, next session, MC reviews due, the 3 weakest topics; topic chips with weight, focus and skip |
| `/c/<c>/plan/` | Week timeline, session checkboxes, "behind schedule" banner suggesting `/regenerate <c> plan` |
| `/c/<c>/summary/`, `…/<topic>/` | Chapter list in teaching order; reading view (max 70ch, sticky table of contents), objectives, `src:` links, "Test yourself" quiz |
| `/c/<c>/exercises/`, `…/<id>/` | Filters for topic, difficulty and status; hint ladder; answer check; solution; self-grade |
| `/c/<c>/mc/` | **MC hub:** accuracy and due count per topic bank; modes Practice, Test, Mistakes, Due, Mixed |
| `/c/<c>/mc/<topic>/` | Every question of the bank in source order with its id as anchor (the target of `mc:` links), plus a practice quiz over the bank |
| `/c/<c>/mc/<topic>.json` | Static endpoint `{topic, title, questions: [{id, type, difficulty, topic, h, html}]}` with pre-rendered question HTML, loaded by `<sk-quiz>` |
| `/c/<c>/cheatsheet/` | Web view in CSS columns, plus a badge with the page count of the built PDF against `max = min(3, course.cheatsheet.max_pages, frontmatter max_pages)`: "PDF (n/max pages)", with "· over the limit" when exceeded, or "PDF not built yet · limit max pages" until Phase 4 builds it |
| `/c/<c>/exams/`, `…/<id>/` | Mock exam list; exam mode |
| `/c/<c>/progress/` | Mastery ring, topic bars, reviews due, misconceptions, sure/unsure calibration, exam history, export and import |
| `/search/` | Pagefind search (§3.5) |
| `/404.html` | Not found |
| `/c/<c>/pdf/<name>.pdf`, `/c/<c>/src/<doc>.pdf` | *(Phase 4)* Static endpoints serving `_build/pdf` and `sources/raw`. Local only; `dist` is gitignored. Until then `check-links` reports links to them as warnings. |

**Shell.** `layouts/Base.astro` renders `<body data-course data-exam-date data-mc-scoring
data-negative-marking>` (the course's exam rule), the header with search and theme toggle,
the course tabs, and the course info as `<script type="application/json"
data-sk-course-data="<course>">` (`components/CourseData.astro`). Pages render the progress
figures as empty placeholders (`[data-sk-due-count]`, `[data-sk-accuracy]`,
`[data-sk-weakest]`, `[data-sk-mastery]`, `[data-sk-exam-best]`, `[data-sk-status]`,
`[data-next-session]`); `elements/dashboard.ts` fills them from the store with `lib/stats.ts`
and refreshes them when progress changes on the page or in another tab, and when the page
comes back from the back/forward cache. `scripts/site.ts` holds the shell's small
enhancements (search shortcut `/`, countdowns, plan day marks, list filters, table-of-contents
spy, the current tab scrolled into view, `<details>` opened for printing); it never touches
progress. Every page works without JavaScript.

**Language of parts.** UI chrome is English, course text follows `course.lang`. Inside a
course page the shell marks its own text `lang="en"`; the elements mark their UI text
`lang="en"` inside course content, and course text inside their UI with the course language.

**Custom elements.** Plain TypeScript, loaded by the one processed `<script>` of the base
layout (`elements/index.ts`). Data arrives through `data-*` attributes; elements talk through
`sk:*` events.

| Element | Behaviour |
|---|---|
| `<sk-mc>` | Radio buttons (single), checkboxes (multi), or a true/false pair per statement (Kprim), in the `mc.pdf` order with display letters A–F; answers are stored by source key. Outside exams, Sure or Unsure is required before **Check**. Checking shows every option's `why` plus the explanation, records the attempt and emits `sk:answer`; after the solution was shown, "Try again" is practice and not recorded. Keyboard, while focus is in the question: 1–6 choose (Kprim: a key cycles the statement through true and false), S/U set sure or unsure, Enter checks (in Test mode it moves on), N goes to the next question. Attributes: `data-mode` (`practice`, `deferred` for Test, `exam`), `data-scoring` (else the nearest `[data-mc-scoring]`), `data-record`, `data-retry`, `data-history`, `data-shuffle` (each `"false"` to turn it off). |
| `<sk-quiz>` | Modes (details below). Attributes `data-course`, `data-mode`, `data-pools` (the `mc/<topic>.json` URLs), `data-topic-titles`, `data-summary-base`, `data-lang` (the course language of the questions and topic names), `data-n`, `data-intro="false"`, `data-frame="none"`. URL parameters `?n=10&minutes=15&topics=a,b&difficulty=1,2` (or `1-3`) and `mode=` pre-fill the start form; with several quizzes on a page the parameters go to the quiz of `?mode=`. Each question is answered once; the result screen shows score per topic, time, misconceptions (sure but wrong) and links to the topic summaries, and "Retry mistakes" is a practice round that records nothing. |
| `<sk-hints>` | Reveals hints one at a time ("Show hint 2 of 3") and counts the hints of this attempt; when a rated exercise is due again, the new attempt starts with every hint closed. A printed page shows every hint, except in a running exam. |
| `<sk-answer-check>` | One input per answer (`data-answers` `[{key, label, label_html, value, unit, rtol, atol, expr, symbols}]`): numbers in German or English notation with unit and SI prefix, or an expression in the given symbols (`lib/answer.ts`, §2.5). A verdict and the reading of the input per answer, and hints for typical mistakes (2π, √2, power of ten, dB). Stores `answer_ok`. |
| `<sk-reveal>` | "Tried it?" confirmation before the solution opens; skipped once the answer check was used. |
| `<sk-self-assess>` | Solved / Partly / Not yet; schedules the exercise (Leitner, below). Using more than one hint in this attempt caps the rating at "Partly". |
| `<sk-exam>` | Exam mode (details below). |
| `<sk-plan>` | A done checkbox per `li[data-session][data-date]` (into its `[data-sk-plan-slot]`), stored as `plan:<id>`; past sessions not done fill the shell's `[data-sk-behind]` banner. |
| `<sk-progress>` | `data-topics`, `data-exams`, `data-exam-date`: mastery ring, topic bars, MC reviews and exercises due, misconceptions, calibration, exam history; live across tabs. |
| `<sk-theme>` `<sk-export>` | Light/dark/system theme, stored as `studykit:theme` (an inline head script applies it before first paint); export and import of the progress document. |

`<sk-quiz>` modes:
- **Practice:** instant feedback.
- **Test:** N questions with feedback at the end and an optional time limit.
- **Mistakes:** questions whose last attempt was not fully right (score < 1, so a Kprim
  with 3 of 4 counts), misconceptions first.
- **Due:** questions the Leitner schedule says are due (exam clamp included).
- **Mixed:** all banks together, instant feedback.

`<sk-exam>` (`data-exam`, `data-duration-min`, `data-points`, `data-pass-points`, `data-aids`,
`data-mc-scoring`, `data-negative-marking`; the last two fall back to `<body>`'s). Each task
is `section.sk-exam-task#<task-id>` with `data-task`, `data-title`, `data-points`, `data-h`
and `data-rubric` `[{criterion, criterion_html, points}]`; the MC part is
`section.sk-exam-mc#mc-part` with `data-points` and `data-points-each`. Flow:
1. A cover page shows duration, points, pass mark and allowed aids. Start moves focus to the
   first task heading.
2. The start time is kept in the session key, so a reload doesn't reset the timer. It warns on
   `beforeunload`, at 10 minutes left and at 1 minute left. While the exam runs, the head with
   the timer is sticky: the element sets `--sk-exam-head` to its height and the page's
   `scroll-padding-top` just below it, so a jump to a part or a focused control is never
   under it.
3. Hints and solutions stay hidden and `inert` until Submit (after a confirmation dialog) or
   time-up.
4. After that, the rubric appears with checkboxes per task, and the MC part is scored
   automatically with the exam's multi rule and, if set, negative marking (§2.6).
5. The result shows total, pass or fail, a grade estimate and the time per part (all time on
   the exam clock, including time a reload or a closed tab took), and the attempt is saved
   as `exam:<id>` and updated while grading. The grade estimate uses the German scale:
   4.0 at `pass_points`, ten equal steps up to 1.0 at full points, 5.0 below the pass mark,
   none without `pass_points`.
6. The same exam open in a second tab follows a submission, retake or restart made in the
   other tab (storage and pageshow events) and never writes a stale session over it; it also
   takes over the other tab's rubric ticks of the same submission.

**Shared libraries:**
- `lib/store.ts` owns the progress document and the session key (§2.11): versioned schema,
  migrations, try/catch on every access, union-merge import. Only the inline theme script
  of the base layout reads `studykit:theme` itself, before first paint.
- `lib/leitner.ts`:
  - Boxes 0–5 with intervals of 0, 1, 3, 7, 14 and 30 days. A new item starts in box 1.
  - A fully right answer (score 1) moves the item up one box, at most to box 5.
  - Any score below 1 is wrong: it sends the item to box 1, or to box 0 (due again today)
    when the answer was "sure". The misconception is not stored; it follows from the last
    attempt (§2.11).
  - Exercises are scheduled from the self-assessment as "unsure" answers: solved = 1,
    partly = 0.5, not yet = 0.
  - Exam clamp, with limit = `exam_date − 2 days` and window = `[exam_date − 10, limit]`:
    nothing is due during the two rest days; a due day past the limit moves to the window
    start (reviewed before the window) or to the limit (reviewed inside it), so every
    attempted item comes up again in the last 10 days; an item reviewed on or after the
    limit is next due the day after the exam. The clamp applies when scheduling and again on
    every "is it due?" check, so a changed exam date counts at once. Exercise entries keep no
    review day, so their check uses `reviewDayOf(due, box) = due − interval(box)`, which lies
    on the same side of the limit as the real review day.
- `lib/scoring.ts` (§2.6), `lib/shuffle.ts` (FNV-1a and mulberry32, the `mc.pdf` order),
  `lib/answer.ts` (§2.5), `lib/stats.ts` (§2.11).

**CSS:**
- `tokens.css`: `light-dark()` pairs, `[data-theme]`, the figure palette variables `--fig-fg`, `--fig-muted`, `--fig-grid`, `--fig-bg`, `--fig-c1` … `--fig-c6`, and a system font stack. Text colour pairs reach 4.5:1 in both themes (`tests/unit/tokens.test.ts`). KaTeX's own fonts come from the package.
- `base.css`: the shell. `elements.css`: the custom elements.
- `content.css`: `sk-*` blocks and display math with `overflow-x: auto`. The cheat sheet's topic sections flow through the columns; boxes, figures, tables and formulas stay whole. In the cheat sheet, display math wraps between formulas set apart with top-level `\qquad` (`lib/katex.ts` adds `\allowbreak` and groups each formula), otherwise after `=` or `+`.
- `code.css`: skylighting token classes for light and dark.
- `print.css`: A4 `@page`, light colours, no site chrome, no page breaks inside boxes, figures, questions, tables and formulas, a question's label kept with its question. The cheat sheet prints as two columns of `<main>` with the title spanning them. `.no-print` hides the summary's "On this page" box, the "Test yourself" quiz and the MC topic practice card; the elements' controls (`elements.css`) and the exam's Start/Retake buttons and alerts are hidden too. `scripts/site.ts` opens every `<details>` on `beforeprint` and restores them after.
- Colour is never the only signal; feedback uses `aria-live`; `prefers-reduced-motion` is respected.

### 3.3 PDF: pandoc 3.13 → Typst 0.15.1, in two explicit steps

*Phase 4.* What exists: the Typst branch of the filter set (§3.1), `typst/pandoc-template.typ`
and a stub `typst/studykit.typ` with the functions the filter calls. `studykit pdf`,
`studykit cheatsheet fit`, the PDF stage of validate and the PDF routes do not exist yet.

**Steps.**
1. `studykit pdf <c> [doc]` assembles `_build/typ/<doc>.md`:
   - It strips frontmatter and concatenates in course order.
   - It generates headings and an exam cover with a points table.
   - Rubric and answer labels go in as plain text with inline math.
2. `pandoc -d common -d typst --log _build/logs/<doc>.json` writes `_build/typ/<doc>.typ`.
3. `typst compile --root <repo> --ignore-system-fonts --diagnostic-format short --input density=<n> …`, run with `SOURCE_DATE_EPOCH=0`.
   - Only Typst's embedded fonts are used (NewCM10, NewCMMath, DejaVu Sans Mono), so no fonts are vendored and page counts are the same on every machine.
   - Every `warning:` line counts as an error.
4. Page counts come from `len(pypdfium2.PdfDocument(pdf))` and are written to `_build/pdf/manifest.json`, which the site reads.

**Documents per course:**

| File | Contents |
|---|---|
| `summary.pdf` | The summary |
| `exercises.pdf` | Hints and solutions in appendices |
| `exercises-blank.pdf` | Exercises only |
| `mc.pdf` | Options (A)–(F) with empty boxes in a deterministic shuffle seeded by question ID; appendix with answer key, every `why` and the explanation |
| `<exam>.pdf` | Cover page, „Seite x von y“, MC part if present |
| `<exam>-solutions.pdf` | Solutions with rubric |
| `cheatsheet.pdf` | The cheat sheet |
| `plan.pdf` | The study plan |

German hyphenation comes from `set text(lang: "de")`.

**Cheat-sheet fit** (`studykit cheatsheet fit <c>`). The limit is `max = min(3, course.cheatsheet.max_pages, frontmatter.max_pages)`.
1. Compile at densities 0–4 (9, 8.5, 8, 7.5, then 7 pt as the floor, with tighter leading and margins). Stop at the first one with at most `max` pages.
2. If 7 pt still overflows, read `typst eval 'query(<cs-end>).first().location().position()' --in _build/typ/cheatsheet.typ` and the height of each section. Exit with code 3 and JSON such as `{"overflow_pages":0.42,"largest_sections":[…]}`.
3. The `authoring/parts/cheatsheet.md` procedure then condenses, in this order: derivations, duplicate examples, prose, then the lowest-priority (low weight, high mastery) topics. Rebuild after each round, for at most 3 rounds, then ask the user what to drop.
4. More than 3 pages is a hard failure, and the previous valid PDF stays in place.

### 3.4 Figures: `studykit.figures`, Python only, Matplotlib for everything

**Pins:**
- matplotlib 3.11.2, numpy 2.5.4, scipy 1.18.1, sympy 1.14.0 (mpmath 1.3.0), schemdraw 0.23 (Matplotlib backend, no svgmath extra), control 0.10.2.
- No Graphviz, Mermaid, resvg or lxml.
- All of these resolve to binary wheels for Python 3.14 on macOS arm64 and Linux x86_64.

**House style** (`house.mplstyle`) and determinism:
- `svg.fonttype: path`, `svg.hashsalt: studykit`, `savefig.transparent: True`, `metadata={'Date': None, 'Creator': None}`.
- Fonts are Matplotlib's bundled DejaVu Sans for text and `mathtext.fontset: cm` for math, so no fonts are vendored.
- Environment of every figure child: `SOURCE_DATE_EPOCH=0`, `MPL_IGNORE_SYSTEM_FONTS=1`,
  `MPLBACKEND=Agg`, `MPLCONFIGDIR=.cache/mpl-nosys` (Matplotlib keys its font cache by its
  version only, so this cache never holds system fonts), `STUDYKIT_LOCALE` from the course.
  The runner builds the font cache once before the children start in parallel.
- With `locale='de'`: a house decimal-comma formatter and "U in V" axis labels.
- **Palette** of fixed, unique hex values:

  | Role | Hex |
  |---|---|
  | fg | `#1f2328` |
  | muted | `#6e7781` |
  | grid | `#d0d7de` |
  | bg | `#ffffff` (the page, for shapes that hide what is behind them) |
  | c1–c6 (Okabe-Ito) | `#0072b2 #d55e00 #009e73 #cc79a7 #e69f00 #56b4e9` |

  Text is drawn only in fg, muted or c1, the roles with at least 4.5:1 on the page. Labels
  are drawn in fg, and the coloured line or marker next to them is the key; c2–c6 are for
  lines and markers only. `tokens.css` maps every role to `--fig-<role>` with a dark-mode
  value.

**Finalize** (stdlib ElementTree) writes four files per figure:
- `<slug>.svg` with literal colours, for Typst.
- `<slug>.web.svg` with each palette hex rewritten to `var(--fig-<role>, #hex)`, every ID prefixed with the slug, and the prolog and metadata stripped.
- `<slug>.png` (100 dpi), for Claude to review visually.
- `<slug>.facts.json`.

**API.** Every builder returns `Figure(svg, png, facts, alt)` and takes `size='col'|'half'|'full'|'cs'` and `alt=`. The locale comes from the course.
- **Function plots:** `plot.functions([('f','x**2-2'),('g','exp(-x)')], x=(-3,3), mark=('roots','intersections','extrema','inflections'), exact=True)`.
  - Numeric results are the truth: dense sign scan, then `brentq` or `scipy.optimize.elementwise.find_root`, a residual check to reject poles, and touching roots via h′.
  - SymPy `solveset` supplies exact forms for display only, and only when they agree with the numeric roots.
  - Points at one location share a label; labels and the legend are placed clear of
    curves, axes and tick labels; crossed axes show a single 0 at the origin.
- **Control and signals** (defined in `signals.py`, re-exported by `plot`; facts name them
  `signals.*`): `plot.bode(G, w=…, unit='rad/s'|'Hz', asymptotes=True, margins=True)`, `plot.nyquist(G, mark_critical=True)`, `plot.pole_zero(G, discrete=False)`, `plot.step_response(G, annotate=(…))`, `plot.root_locus(G)`, `plot.signals(t, {…}, stem=False)`.
  - `G` is a `control.TransferFunction`, a `(num, den)` pair or a SymPy string in `s` (or `z`
    for `pole_zero`/`root_locus`); dead time is rejected.
  - python-control only computes; the house code draws.
  - `scipy.signal` and brentq independently re-check margins and crossover frequencies; a
    disagreement is an error, not a silent pick.
- **Phasors:** `plot.phasor({'U_R': (5, 0), 'U_L': (3, 90)}, chain=True)`; `reference={'I': (2, 0)}`
  draws the phasor the others refer to at its own scale beside its axis, and `angle_name=`
  names the phase angle (TeX, default `\varphi`).
- **Circuits** (IEC style): `circuit.voltage_divider / rc / rl / rlc / opamp / bridge`, plus house DIN EN 60617 sources, `zaehlpfeil_u`/`zaehlpfeil_i` reference arrows, a filled inductor, and the escape hatch `circuit.drawing()`.
  - Values are strings with units (`'4,7 kΩ'`, `'100 nF'`), SI numbers, or symbols (`'R'`,
    `'2R'`); a wrong unit or SPICE shorthand such as `'4.7k'` is an error. facts list every
    component with its nodes and SI value, every reference arrow with its nodes, and derived
    values (divider ratio, τ, f_c, ω_0, Q, gain).
  - Conventions: voltage arrows point from + to − (DIN 5489), ground is the IEC earth symbol,
    the AC source is a circle with ~, the Wheatstone bridge is drawn as an H, the op-amp is
    the DIN box (`symbol='triangle'` for the US form).
- **Block diagrams:** `block.feedback_loop(forward=[…], feedback='H(s)', signals={…}, disturbance=None, sign='-')`, `block.chain`, `block.parallel` (`schemdraw.dsp`). facts carry the loop, reference, error and disturbance transfer functions, solved with SymPy from the drawn loop.
- **Graphs:** `graph.state_machine(states, transitions, initial, accepting, kind='moore'|'mealy', layout='ring'|'row'|'grid'|coords)` and `graph.flowchart(nodes, edges)`, built on `schemdraw.flow` State, StateEnd, Arc2 and ArcLoop.
- **Topic map:** `graph.topic_map(course_dir, size='full', direction='auto'|'lr'|'tb')`,
  registered in `builtins.py` and built for every course as `topic-map` (§2.12). Topics sit in
  layers by prerequisite depth with few crossings; box height grows with weight, focus topics
  get a c1 frame, skipped ones are muted and dashed.
- **Raw Matplotlib:** `plot.custom()`, a context manager that yields a house-styled axis. It is the only route to raw Matplotlib.
- MC questions can use the same builders for distractor figures, for example four Bode plots. `facts.json` then proves which one is correct.
- Labels go through `labels.place`, which tries candidate spots and keeps the first whose box
  covers no drawn point, axes edge or earlier label (otherwise the nearest free spot with a
  leader line).
- **Gallery:** `tests/fixtures/figures/gallery/` has one script per template; the tests build
  it with the runner and compare every `facts.json` with `tests/golden/figures/`.

**Runner** (`studykit fig build [course] [--only slug]`):
- Each `figures/<slug>.py` defines `build()` and runs in its own subprocess (`python -I`, 60 s timeout), in parallel up to the CPU count.
- Cache key: sha256 of the script, the studykit source tree, `uv.lock`, the style file and the locale.
- **Validation:**
  - exit code 0
  - the SVG parses, with an `svg` root and a `viewBox`
  - no `<script>`, `on*` attributes, `<foreignObject>`, `<text>` or external `href`
  - palette colours only, and text only in fg, muted or c1 (≥ 4.5:1 on the page)
  - at most 400 KB and a non-empty bounding box
  - missing-glyph warnings and mathtext parse errors are fatal, reported with the script path

### 3.5 Search: Pagefind 1.5.2

- The site's `build` script runs `scripts/pagefind.mjs` after `astro build`: it runs
  `pagefind --site dist --force-language <lang>` from `site/` (`pagefind.yml` holds the other
  settings), then copies `dist/pagefind` to `site/public/pagefind/`, so `just dev` serves the
  last built index and search works in dev after one build.
- Only course content is indexed: layouts put `data-pagefind-body` on the content element.
- Filters via `data-pagefind-filter`: `course`, `type` (overview, summary, exercise, mc,
  exam, cheatsheet), `topic`. Metadata: title, course, difficulty.
- `exclude_selectors: [".katex", "sk-mc [data-correct]", "sk-mc .sk-why", "sk-mc .sk-explanation", ".sk-solution", ".sk-hint", ".sk-error-card"]`,
  so search never reveals solutions, hints (a running mock exam keeps them locked) or MC keys.
- Pagefind builds one index per `<html lang>`; `--force-language` is set to the most common
  `<html lang>` of the course pages, so all courses share one index.
- UI: the Pagefind Component UI in a `/search/` route (filter values are shown by name) and a
  header search box (keyboard `/`).

## 4. Toolchain & reliability

### 4.1 Pins (`toolchain.toml` is the single source)

`just doctor` checks pandoc, typst and just exactly, uv, node and pnpm against the minimum
versions in `[system.*]`, Python's major.minor against `.python-version`, and the installed
`astro`, `katex` and `pagefind` against `site/package.json`; a busy port 4321 is only a
warning. `doctor --quick` skips the site packages, the Typst fonts and the port.

| Tool | Version | Source |
|---|---|---|
| pandoc | **3.13** (texmath 0.13.3.3) | `studykit tools install` → `.tools/bin`, sha256-checked, assets `pandoc-3.13-arm64-macOS.zip` and `pandoc-3.13-linux-amd64.tar.gz`. Fallback: one-line change to 3.12.1. |
| typst | **0.15.1** | same installer; `typst-aarch64-apple-darwin.tar.xz` and `typst-x86_64-unknown-linux-musl.tar.xz` |
| just | **1.59.0** | same installer; `just-1.59.0-aarch64-apple-darwin.tar.gz` and `just-1.59.0-x86_64-unknown-linux-musl.tar.gz`, locally and in CI |
| uv / Python | ≥ 0.11.30 / 3.14 | uv-managed: `requires-python = ">=3.14,<3.15"`, `python-preference = "only-managed"`. Falling back to 3.13 is a one-line change. |
| node / pnpm | ≥ 24.17.0 / ≥ 11.22.0 | installed by the user (`corepack enable pnpm`); CI pins 24.17.0 and 11.22.0 |
| Python (`uv.lock`) | figure stack from §3.4, plus pydantic 2.14.1, PyYAML 6.0.3 (pypdfium2 5.14.0 comes with Phase 4); dev: pytest 9.1.1, ruff 0.17.1 | `exclude-newer = "7 days"` |
| npm | from §3.2 | `minimumReleaseAge: 10080` |

Not needed for any core build: Chromium, TeX, Graphviz, Mermaid, rsvg or resvg. Playwright downloads Chromium only for the browser tests (`just e2e` installs it; the element harness needs it too) and in CI.

### 4.2 justfile

```just
set shell := ["bash", "-euo", "pipefail", "-c"]

root := justfile_directory()
export PATH := root / ".tools/bin" + ":" + env("PATH")
export ASTRO_TELEMETRY_DISABLED := "1"
# absolute, so python (run from the repo root) and the site (run from site/) agree on a
# relative value: it is relative to the repo root
export STUDYKIT_COURSES_DIR := absolute_path(env("STUDYKIT_COURSES_DIR", root / "courses"))

sk := "uv run --frozen studykit"
# recipes that run other recipes call this very just with this justfile
just := quote(just_executable()) + " --justfile " + quote(justfile())

default:
    @just --list
setup:                       # idempotent
    uv sync --frozen
    {{sk}} tools install
    pnpm -C site install --frozen-lockfile
    git config core.hooksPath .githooks
    {{sk}} doctor
doctor *flags:               # toolchain.toml versions, site packages, Typst fonts, hooks, courses/ ignored, port 4321 (warning)
    {{sk}} doctor {{flags}}
figures course="":
    {{sk}} fig build {{course}}
dev: (figures "")            # http://localhost:4321 (strictPort)
    pnpm -C site dev
build course="": (figures course) (validate course)
    STUDYKIT_STRICT=1 pnpm -C site build
    {{sk}} check-links site/dist
check-links dist="site/dist":
    {{sk}} check-links {{dist}}
lint +files:
    {{sk}} lint {{files}}
validate course="" *flags:   # flags: --quick, --release, --paths, --json
    {{sk}} validate {{course}} {{flags}}
schema:
    {{sk}} schema export
test:
    uv run --frozen pytest -q
    pnpm -C site run test:unit
    bash .github/scripts/test-hooks.sh
    {{sk}} schema export --check
    {{sk}} golden            # math corpus through KaTeX and pandoc→Typst
[positional-arguments]
e2e *args:                   # needs site/dist with the sample course
    pnpm -C site exec playwright install chromium
    pnpm -C site run e2e "$@"
ci:
    {{just}} doctor
    {{just}} test
    STUDYKIT_COURSES_DIR={{quote(root / "examples")}} {{just}} build sample-course
    STUDYKIT_COURSES_DIR={{quote(root / "examples")}} {{just}} validate sample-course --release
lint-code:
    uv run --frozen ruff check src tests
    uv run --frozen ruff format --check src tests
```

`build` sets `STUDYKIT_STRICT=1` itself and builds the whole site (all courses); its
`course` argument picks what figures and validation cover. Planned recipes: `pdf` and
`cheatsheet` (Phase 4, and `build` then depends on `pdf`), `verify`, `status`, `tutor` and
`examine` (Phase 5 and 6).

### 4.3 Validation (`studykit validate [course] [--paths …] [--quick] [--release] [--json]`)

Every finding has the form `path:line:col SK-CODE message (fix: …)`. A code is the stage family from the table plus a rule (`SK-MCQ-COUNT`, `SK-YAML-ESCAPE`); warnings keep the shape and start the message with `warning:`. Each code is documented in `content-format/errors.md` with a fix recipe and the pipeline step that owns it. Stages run in the order of the table. `--quick` runs Structure, Schema, Fences, MC, Math and the Pandoc backstop (with `sk-scope=file`), for one file in about 1 s; `studykit lint` is `--quick` restricted to the given files and is what the hook runs. `--release` adds Site and Coverage. A stage whose tools are not there yet is skipped with an `info:` note.

| Stage | Checks | Code |
|---|---|---|
| Structure | required files (`overview.md`, `plan.yaml` and an allowed `cheatsheet.md` are warnings until `--release`), known file paths, ID patterns and file names, unique and non-retired IDs, acyclic prerequisites, topics ⊆ course topics, the six overview sections, exam points add up | SK-STRUCT |
| Schema | pydantic validation of YAML and frontmatter; scalar-style lint; control characters; label and rubric fields are text plus inline math only | SK-SCHEMA, SK-YAML |
| Fences | line scan outside code: exact fence forms, allowed placement, depth, blank lines, hint and solution count, code languages; `\|` on pipe-table rows; line-end hyphens (warning) | SK-BLOCK |
| MC | option counts per type, `[x]` invariants, a `why` on every option, one explanation, `pin-last` rule, no "all of the above", no option letters, bank-bias warnings | SK-MCQ |
| Math | denylist and environment allowlist; KaTeX strict via `check-math.mjs` (skipped with a note without `site/node_modules`); inline and display form; block markers; space commands between digits; hint-leak warning | SK-MATH |
| References | `ex: mc: topic: exam: src: fig:` targets, plan refs, exam task files and MC file, `modeled_on` and frontmatter source documents, archetypes, `src:` pages | SK-REF |
| Pandoc | the Lua filter set with the json target, on files the stages above left without errors; also with `--quick`, then at file scope (targets missing from the index are not reported). The filter reports family-plus-rule codes: the code validate uses for a rule both check (e.g. SK-REF-FIGURE), and SK-BLOCK-RAW, SK-BLOCK-MARKDOWN, SK-REF-LINK and SK-MATH-TYPST for rules only it checks; a failure without a finding is SK-PANDOC-FAIL | SK-* |
| Figures | build (cached) plus SVG validation; unreferenced scripts (warning) | SK-FIG |
| Verification | *(Phase 5; skipped)* ledger complete and fresh; disputed and quarantined items listed; numeric MC questions have a check script | SK-VER |
| PDF | *(Phase 4; skipped)* every document compiles with no warnings; cheat sheet ≤ its limit | SK-PDF |
| Site | `--release` only, for whole courses (not with `--paths`), and only when the stages above found no errors: strict `astro build` into a temporary `--outDir` with `STUDYKIT_COURSES_DIR` set to a temporary directory that holds one symlink to the course; Pagefind with `--force-language`; `pnpm -C site check` without `STUDYKIT_STRICT`; `check-links` over the course's own pages, reported as `dist/<page>` | SK-SITE |
| Coverage | `--release` only: the overview links every topic; each topic has a summary, at least `targets.exercises_per_topic` (4 with `auto`) exercises over two or more difficulties, and at least `targets.mc_per_topic` MC questions (with `auto`: 10–25 by weight); a bank lacking a type of `course.exam.mc.types` (warning); at least `targets.mock_exams` mock exams, each within ±10% of the points and time in `course.yaml: exam` | SK-COV |

### 4.4 Tests

`just test` runs the first five suites; CI runs the browser suites after it (§4.5).

- **pytest** (`tests/py/`):
  - control margins compared with `scipy.signal` and closed forms; repeated roots, poles
    and right-half-plane counts of the control templates
  - every figure template renders and validates, with a `facts.json` snapshot (never SVG bytes); the palette, its readable text colours and the site's figure tokens agree
  - lint fixtures (`tests/fixtures/bad/<SK-CODE>/`): each forbidden construct produces its code and its replacement hint; every emitted code is documented in `errors.md`, and every documented code is emitted
  - the filter set over `tests/fixtures/pandoc/` and the golden `blocks.md` and `mcq.md` corpora through html5, typst (compiled) and json
  - YAML loading, the schemas, validate's stages, the render bridge, the Site stage, `check-links`, `doctor` and `tools`
  - *(planned)* key points of function plots (`cos x = x`, touching roots, poles) beyond the
    gallery snapshot; *(Phase 5/6)* `mc_numeric`, the scheduler, `status`, and ingest of a
    generated two-page PDF
- **node --test** (`site/tests/unit/`): scoring for every type and mode, shuffle determinism with `pin-last` (against values printed by Python), Leitner and the exam clamp, store migration and merge, the answer check (`lib/answer.ts`), the progress figures (`lib/stats.ts`), and text colour pairs of `tokens.css` at 4.5:1 or more in both themes.
- **Git hooks and guard** (`.github/scripts/test-hooks.sh`): `commit-msg`, `pre-commit` and `guard.sh` in throwaway repositories.
- **Schema drift:** `studykit schema export --check`.
- **Golden corpus** (`studykit golden`): `tests/golden/math.md`, EE and math formulas including decimal comma, `\underline`, `\mathrm{k\Omega}`, `cases`, `aligned` and determinants, through KaTeX strict and pandoc → Typst with zero warnings; `math.typ.snap` pins the Typst translation; every construct in `math-denied.md` must still fail an engine.
- **Element harness** (`pnpm -C site run test:elements`, `site/tests/elements/`): Playwright against static fixture pages that mirror the shell's markup, served by `server.mjs`, which compiles `src/lib` and `src/elements` with the pinned TypeScript. Covers `<sk-mc>`, `<sk-quiz>`, the exercise elements, `<sk-exam>`, `<sk-progress>` and the dashboard placeholders; `screenshots.spec.ts` writes every element in light and dark for review by eye.
- **Playwright e2e** (`just e2e`, `site/tests/e2e/`) against the built sample course in `site/dist`, served by `astro preview` (`SK_E2E_PORT` moves it off 4321):
  - `pages`: the build has the sample course's pages, unknown paths get the 404 page, and every page loads its scripts and assets without errors
  - `mc`: one MC question of each type is answered, scored and recorded, and the progress survives a reload
  - `quiz`: Practice, Test (`?n=`, `?minutes=`), Mistakes, Due and Mixed
  - `exercise`: hint ladder, answer check, "Tried it?", the hint cap on the self-assessment
  - `exam`: start the mock exam, reload, the timer keeps running; submit, solutions and rubrics appear, the MC part is scored with the exam's rule
  - `progress`: export and import round trip
  - `overview`: plan checkboxes and the shell's progress placeholders
  - `shell`: the theme persists without a flash, search finds German course content and never shows hints, a malformed `#fragment` breaks no shell script
  - `lang`: every text resolves to the language it is written in (quiz questions and topic names in the course language, the elements' own text in English)
  - `layout`: the cheat sheet fills its columns and cuts no formula, the current course tab is visible on a phone, no sideways scrolling at 320 px, past and done plan sessions keep their contrast
  - `print`: an exercise prints its hints and solution (without counting the hints as used); summary, MC topic and exam pages print without their quizzes and buttons

Both Playwright configs stop their web server on SIGTERM as well as SIGINT.

### 4.5 GitHub Actions

- **`ci.yml`** (push, PR, and a weekly scheduled run) on `ubuntu-24.04`, with every action pinned by commit SHA:
  1. checkout, `setup-uv` (uv 0.11.30), `pnpm/action-setup` (pnpm 11.22.0), `setup-node` (Node 24.17.0, pnpm cache), and a cache of the pinned tool downloads keyed by `toolchain.toml`
  2. `uv run --frozen studykit tools install`, which fetches the pinned pandoc, typst and just binaries by hash; later steps call `.tools/bin/just`
  3. `just setup`, `just lint-code`, then `playwright install --with-deps chromium`
  4. `just ci`
  5. the element harness (`pnpm -C site run test:elements`, if Chromium installed) and `just e2e` (if `just ci` passed); both run even after an earlier failure, so one failure does not hide the other
  6. on failure only: upload `site/dist` and the Playwright reports and results (`site/node_modules/.cache/sk-e2e/`, `sk-elements/results/`), kept 14 days. Uploading the sample-course PDFs comes with Phase 4.
- **`guard.yml`** (push, PR; full history) runs `bash .github/scripts/guard.sh commits|courses|pdfs`:
  - `commits`: every non-merge commit in the range passes `.githooks/commit-msg` (a Conventional Commit, no `Co-Authored-By`). The range is base..head for a pull request and before..HEAD for a push. When the before commit is missing (a new branch, or a force push), a branch is checked as `origin/<default>..HEAD`; creating the default branch checks its whole history; a rewrite of the default branch fails and has to be checked by hand; a range git cannot list fails the check.
  - `courses`: `git ls-files courses` returns only `courses/README.md`.
  - `pdfs`: no tracked `*.pdf`, in any letter case, outside `tests/fixtures/`.

`commit-msg` rejects a `Co-Authored-By` trailer on every commit; subjects git writes itself
(`Merge …`, `Revert "…"`, `fixup!`, `squash!`, `amend!`) are exempt only from the Conventional
Commit format. `pre-commit` matches the staged paths by pathspec, so file names with non-ASCII
characters or quotes are caught too.

## 5. Claude Code layer

*Phase 5 and 6.* What exists: `.claude/settings.json` with `attribution` only, empty
`.claude/agents/` and `.claude/skills/`, and `studykit lint --hook`, the command the
PostToolUse hook below runs. The commands this section names besides `lint`, `validate`,
`ls` and `fig build` (`calc`, `blind`, `verify`, `plan`, `progress`, `ingest`, `status`, `hook`)
are planned.

### 5.1 Project configuration

**`.claude/settings.json`:**
- `"attribution": {"commit": "", "pr": ""}`. The docs confirm that an empty string hides the trailer, and the `commit-msg` hook enforces it anyway.
- `permissions.allow` covers what background subagents need, because their permission prompts surface in the main session:
  - `Bash(just *)`, `Bash(uv run --frozen studykit *)`, `Bash(uv run --frozen python courses/*)`
  - `Read(courses/**)`, `Write(courses/**)`, `Edit(courses/**)`
- `permissions.deny`: `Bash(git add -f *)`, `Bash(git add --force *)`. There is no deny on `.claude/**`, so Claude can build Phase 5.
- **Hooks:**
  - `PostToolUse`, matcher `Write|Edit`: `uv run --frozen --project "${CLAUDE_PROJECT_DIR}" studykit lint --hook`. It reads `tool_input.file_path` from stdin and ignores anything outside `courses/**` and `examples/**`. On findings it exits 2 with them on stderr, so Claude fixes them immediately.
  - `PreToolUse`, matcher `Bash`, with `"if": "Bash(git *)"`: `studykit hook pre-git` blocks `git add` and `git commit` that touch course paths.
- **No `memory:` field on any agent.** Course-specific state lives in `courses/<c>/progress` and `state`, and `.claude/agent-memory*/` is gitignored as a safety net.

**`CLAUDE.md`:**
- Never commit `courses/`.
- Conventional Commits, one logical change each, no Co-Authored-By.
- Skills and UI are in English; generated content follows `course.lang`.
- Figures are code. Never compute numbers in your head; use Python.
- Run `studykit validate` before finishing.
- Find course files with `studykit ls`, because Grep and Glob may skip gitignored paths.

### 5.2 Skills

**User commands** (`disable-model-invocation: true`; they run in the main thread, so they can use AskUserQuestion):

| Skill | Arguments | Purpose and output |
|---|---|---|
| `/register-new-subject` | `<folder> [course-id]` | Full pipeline (§5.4). Produces `courses/<id>/`, a green `validate --release`, the PDFs, and a report. |
| `/regenerate` | `<course> <overview\|plan\|summary\|exercises\|mc\|figures\|exams\|cheatsheet\|all> [--topic t] [--add n] [--replace] [note]` | Copies the files it replaces into `_history/`. Re-runs the step and everything downstream of it (author → verify → validate → PDF). Keeps the IDs of items that survive. Asks before `--replace`. |
| `/add-material` | `<course> <file\|folder>` | Incremental ingest, topic-map diff, then suggests which parts to regenerate. |
| `/verify` | `<course> [id\|topic\|all]` | Blind re-verification with the dispute loop. |
| `/tutor` | `<course> [topic\|ex-id]` | Socratic tutoring persona. |
| `/examine` | `<course> [diagnostic\|topic <t>\|mc\|weak\|misconceptions\|exam <id>\|oral]` | Strict examiner persona. |
| `/import-progress` | `<course> [file]` | Validates and copies a browser export (by default, after confirmation, the newest `~/Downloads/studykit-progress-<course>-*.json`). Runs `progress report` and offers a replan. |
| `/study-status` | `<course>` | Days left, plan adherence, weak topics, next sessions, due reviews. |

**Internal skills** (`user-invocable: false`, each under 500 lines):

| Skill | Contents |
|---|---|
| `content-format` | Schemas, the dialect from §2.3, copy-ready templates, `errors.md` (SK-codes and fixes), links to the sample course |
| `authoring` | Shared quality rules, plus `parts/{overview,summary,exercises,mc,exam,cheatsheet,plan}.md`. The agent reads the part it needs by path, so not every part is preloaded. `parts/mc.md` holds the misconception catalogue, the type-mix rules, "one concept per stem", options of similar length, and the requirement that every distractor's `why` names its mistake. |
| `figures` | API reference, gallery, and the rule "render → look at the PNG → fix" with an overlap, clipping and anchor checklist |
| `ingest` | Chunk digest procedure, notes template, exam-profile template |
| `verify-protocol` | Blind procedure, check-script recipes (MNA, phasors, Laplace, margins), the two-method rule |

The persona text for `tutor` and `examiner` lives in the `/tutor` and `/examine` skills. The agents of the same name preload them, so there is one source.

### 5.3 Agents (`.claude/agents/*.md`)

No agent has the `Agent` tool, so nothing spawns further agents.

| Agent | Model / effort | Tools | Preloaded skills | Writes |
|---|---|---|---|---|
| `ingester` | sonnet / medium, maxTurns 40 | Read, Write, Glob, Bash | ingest, content-format | `sources/notes/<chunk>.md`; transcriptions of scanned pages into `sources/text/` |
| `exam-analyst` | opus / high, maxTurns 50 | Read, Write, Glob, Grep, Bash | ingest | `analysis/exam-profile.yaml` (archetypes, frequencies, points, minutes per point, MC share, types, scoring, negative marking, topic weights, confidence) and `notation.yaml` (j vs. i, ε(t) vs. σ(t), underlined phasors) |
| `author` | opus / high, maxTurns 80 | Read, Write, Edit, Glob, Grep, Bash | content-format, authoring, figures | One (topic, part) per call: summary, exercises, MC bank, mock exam or cheat sheet, plus figure scripts. Must end with `studykit validate --paths <own files>` green and return compact JSON. |
| `verifier` | opus / high, maxTurns 50 | Read, Write, Bash | verify-protocol, content-format | `checks/**` only |
| `tutor` | opus | Read, Grep, Glob, Bash | tutor | nothing; started via `just tutor` (main thread) |
| `examiner` | opus | Read, Grep, Glob, Bash, AskUserQuestion | examine | `progress/examiner.jsonl` via `studykit progress log`; started via `just examine` (main thread) |

**Verifier blindness** is enforced by an agent-scoped `PreToolUse` hook, `studykit hook verifier-guard`:
- It denies Read, Grep and Glob on `exercises/`, `mc/` and `exams/`.
- It denies Bash commands that mention those paths, except `studykit` and `python checks/…`.
- The verifier works only from `studykit blind <c> <id>`, which writes `_build/blind/<id>.md`: the statement with no solution, answers or `[x]` marks, and MC options in source order labelled A–E.

**Verifier protocol:**
1. Compute in Python.
2. Write `checks/<id>.py` or `checks/<id>.json`.
3. Run `studykit verify`, which compares against the answer key and writes the ledger.
4. If they disagree, confirm with a second method (for example nodal vs. mesh analysis, or symbolic vs. numeric simulation) before recording a dispute.
5. Disputes go to an author fix agent together with the verifier's numbers, for at most 2 rounds. Whatever is still disputed becomes **quarantined**: hidden from the site and the PDFs, and listed in the report.

**Examiner MC in the terminal** uses AskUserQuestion:
- single with ≤ 4 options: one question
- multi with ≤ 4 options: `multiSelect`
- Kprim: four True/False questions in one call
- larger questions: shown as text, answered by letter

The examiner asks for confidence before revealing anything, never reveals an answer before the user commits, and grades calculations with the rubric using `studykit calc`.

### 5.4 `/register-new-subject <folder> [course-id]`

The state is derived from outputs by `studykit status <c> --json` (manifest hashes plus file presence plus ledger). There is no separate state file. Running the command again resumes at the first unfinished step. Success is judged from files and gates, never from an agent's own report.

0. **Preflight:**
   - `just doctor --quick`
   - propose a course ID from the folder name; if it already exists, offer to resume
   - `studykit ingest scan <folder> --dry-run --json` builds an inventory: PDFs, pages, text-layer share, guessed kind from filename and cover page, duplicates (sha256), and unsupported files (pptx/docx get "export as PDF")
1. **Ask, round 1** (one AskUserQuestion call with 4 questions, after showing the inventory table):
   - Exam date: "Unknown yet", "the date found in the materials", or free text via Other.
   - Exam format: written / written + MC part / MC only / oral.
   - Cheat sheet: not allowed / 1 / 2 / 3 pages.
   - Hours per week.

   A second call covers uncertain document kinds (multi-select "these are past exams or solutions") and confirms the detected output language.
2. **Scaffold** (Python): copy sources to `sources/raw` (the user's folder is only read), write `manifest.yaml` and a draft `course.yaml`, and gate on schema validation.
3. **Extract** (Python): pypdfium2 page text into `sources/text`. A page is flagged *visual* if it has fewer than 200 characters, garbled glyphs or large image areas. Chunks are at most 20 pages, matching the Read tool's PDF page limit, and never cross a document boundary. Past exams are kept whole.
4. **Read** (parallel, at most 6 at a time):
   - one `ingester` per chunk, reading the text first and calling `Read(pdf, pages=…)` only for flagged pages
   - `exam-analyst` runs alongside over all exams and solutions; with no past exams it writes a low-confidence profile from the round-1 answers
   - Gate: the notes schema holds, every chunk has notes, formulas pass the math lint
5. **Synthesize** (main thread):
   - merge note digests into 6–15 topics with prerequisites and weights (exam point shares, falling back to lecture coverage)
   - write `outline.md`
   - fill in `course.yaml` topics
6. **Ask, round 2:**
   - Show a numbered topic table (weight, sources, past-exam frequency). The user replies in one line, for example `focus 3,5; skip 9; merge 6+7; ok`.
   - Then AskUserQuestion: number of mock exams (1/2/3), scope (full / core first: summary + MC + plan), and go/no-go with a cost and time estimate.
7. **Author wave** (at most 6 parallel): first one `author` for `overview.md` (§2.12), then one `author` per (topic, part) for summary, exercises and MC bank, following `notation.yaml`. The hook lints every write. Gate: `validate --quick` over the new files.
8. **Figures:** `just figures <c>`. Failures, and PNGs with problems, go back to the owning author (at most 2 rounds).
9. **Verify wave** (at most 6 parallel): one `verifier` per topic, with the dispute loop described in §5.3.
10. **Mock exams:** `author` with `parts/exam.md` (at most 3 in parallel), including `mc.md` when `exam.mc.present`, then verification. Gate: points, time and archetypes match the profile.
11. **Cheat sheet:** `author` with `parts/cheatsheet.md`, the fit loop, then the verifier's formula audit. Gate: page count ≤ the limit.
12. **Plan:** `studykit plan` (deterministic), then the main thread writes the session goals.
13. **Publish:** `just pdf <c>`, `just build <c>`, `studykit validate <c> --release`. Failures are routed by SK-code to the owning agent, for at most 3 rounds. `status` is set to `ready` only when everything is green.
14. **Report:**
    - counts per part (exercises by difficulty, MC by type, exams, figures)
    - share verified, fixed and quarantined, with reasons
    - cheat-sheet pages and font size
    - next steps: `just dev` → `http://localhost:4321/c/<id>/`, `/examine <id> diagnostic` (15 MC questions to seed the Leitner boxes and the plan), `/tutor`

**Rebuild dependencies** used by `/regenerate`:

```
sources → notes → {topics, exam-profile} → plan
topics + exam-profile → overview
topics → summary → cheatsheet
topics → exercises
topics → mc
exam-profile + exercises → exams
any content → figures → verify → pdf
```

## 6. Implementation phases

These follow your order (toolchain → figures → website → PDF → agents/skills → /register-new-subject), with a small guardrails phase first. Every commit is a Conventional Commit, one logical change, with no Co-Authored-By trailer.

**Status:** Phases 0–3 are complete; Phase 4 is next. Sections of this document that describe
later phases mark the parts that do not exist yet.

**Phase 0: guardrails.** Done when the hooks reject a bad message and staged course data, and the guard workflow is green.
- `chore: ignore course data, build outputs and local tool dirs`
- `chore: add MIT license and editorconfig`
- `chore(git): add commit-msg hook for conventional commits without co-author trailers`
- `chore(git): add pre-commit hook rejecting staged course content`
- `chore(claude): hide commit and pr attribution in project settings`
- `ci: add commit message and course content guard workflow`

**Phase 1: toolchain.** Done when `just setup && just doctor && just test` is green locally and in CI, and the golden math corpus passes through KaTeX and pandoc 3.13→Typst 0.15.1. This first run settles the vmatrix and decimal-comma questions and pandoc's handling of loose task lists.
- `build(py): add uv project for studykit on python 3.14`
- `build(site): add pnpm site package with release-age cooldown`
- `build: add toolchain manifest with checksummed pandoc and typst assets`
- `feat(cli): install pinned pandoc and typst into .tools`
- `feat(cli): add doctor command for exact tool versions`
- `build: add justfile with setup, doctor and test recipes`
- `test: add golden math corpus through katex and pandoc to typst`
- `ci: run setup, doctor and tests on ubuntu`
- `docs: document setup and toolchain in readme`

**Phase 2: figures.** Done when every template renders in the sample course, the facts snapshots pass, and the PNGs have been reviewed.
- `feat(figures): add house style, palette and figure object`
- `feat(figures): add svg finalizer with palette tokens and id prefixes`
- `feat(figures): add svg validator`
- `feat(figures): add bracketing finder for roots, intersections and extrema`
- `feat(figures): add function plot template`
- `feat(figures): add bode, nyquist, pole-zero, step and root locus templates`
- `feat(figures): add phasor and signal templates`
- `feat(figures): add iec circuit templates with din sources and reference arrows`
- `feat(figures): add block diagram, state machine and flowchart templates`
- `feat(figures): add topic map template generated from course topics`
- `feat(figures): add cached parallel subprocess runner`
- `test(figures): snapshot facts for every template`
- `feat(examples): add sample course figure scripts`

**Phase 3: content format and website, including the MC section.** Done when:
- `just dev` shows the sample course with every tab
- MC Practice, Test, Mistakes, Due and Mixed modes work for single, multi and Kprim
- exam mode works
- strict build, unit tests and e2e are green

Commits:
- `feat(schema): add pydantic models for course, items, plan and progress`
- `build(schema): export json schemas and check drift`
- `feat(lint): enforce yaml scalar style and control characters`
- `feat(pandoc): add shared defaults and guard filter`
- `feat(pandoc): render container blocks for html`
- `feat(pandoc): parse and validate multiple-choice questions`
- `feat(pandoc): add math denylist with replacement hints`
- `feat(pandoc): resolve figure, item and source references`
- `feat(cli): add lint and validate commands with error codes`
- `feat(examples): add sample course content`
- `build(site): scaffold static astro site`
- `feat(site): load course documents through pandoc with build-time katex`
- `feat(site): inline themed figures at render time`
- `feat(site): add layout, theme toggle and course cards`
- `feat(site): add course overview tab with topic map and today panel`
- `feat(site): add summary, plan and cheat sheet tabs`
- `feat(site): add versioned progress store with export and import`
- `feat(site): add exercise view with hint ladder, answer check and self-assessment`
- `feat(site): add multiple-choice element with single, multi and kprim scoring`
- `feat(site): add quiz modes with leitner review and exam clamp`
- `feat(site): add mock exam mode with timer and rubric grading`
- `feat(site): add pagefind search with course, type and topic filters`
- `style(site): add print stylesheet`
- `test(site): cover scoring, shuffle, leitner and store migration`
- `test(site): add playwright smoke tests for quiz and exam flows`
- `ci: build and validate sample course site`

**Phase 4: PDF.** Done when every sample PDF builds with zero warnings, `mc.pdf` has its answer key, and the cheat sheet fits within its limit.
- `feat(pdf): add typst house library and pandoc template`
- `feat(pandoc): emit typst boxes with solution appendix`
- `feat(pandoc): emit multiple-choice options and answer key for typst`
- `feat(cli): build summary, exercise, mc, exam and plan pdfs`
- `feat(cli): fit cheat sheet with density levels and page limit`
- `feat(site): serve built pdfs and source documents`
- `test(pdf): assert page counts and zero warnings`
- `ci: build and upload sample course pdfs`

**Phase 5: agents and skills.** Done when, on the sample course:
- the verifier catches a seeded wrong number and a seeded wrong MC key
- the hook catches a broken fence
- `/regenerate sample-course mc --topic rc-filter --add 3`, `/tutor`, `/examine mc`, `/import-progress` and `/study-status` all work

Commits:
- `feat(verify): add check api, runner and per-item ledger`
- `feat(verify): add blind item views`
- `feat(cli): add sympy calc command`
- `feat(claude): add permissions and lint hooks`
- `feat(claude): add content-format, authoring and figures skills`
- `feat(claude): add author agent`
- `feat(claude): add verifier agent with blind guard hook`
- `feat(claude): add verify and regenerate commands`
- `feat(progress): add import, examiner log and mastery report`
- `feat(plan): add deterministic study plan scheduler`
- `feat(claude): add tutor and examiner skills and agents`
- `feat(claude): add import-progress and study-status commands`
- `test(claude): lint skill and agent frontmatter and referenced files`

**Phase 6: `/register-new-subject`.** Done when an end-to-end run on `examples/sample-materials`, including the rasterised scan, produces a course with a green `--release`, and an interrupted run resumes correctly.
- `feat(ingest): add inventory, source copy and manifest`
- `feat(ingest): extract page text and plan chunks`
- `feat(claude): add ingester and exam-analyst agents`
- `feat(cli): add output-derived pipeline status`
- `feat(claude): add register-new-subject command`
- `feat(claude): add add-material command`
- `test(ingest): run scan, extract and status on synthetic materials`
- `docs: add walkthrough for registering and studying a subject`

**Phase 7 (optional):** Graphviz layouts for large graphs, mitex as a fallback for flagged formulas, FSRS, packaging as a plugin.

## 7. Top risks and mitigations

| # | Risk | Mitigation |
|---|---|---|
| 1 | KaTeX (web) and texmath (PDF) disagree on math. This is the only remaining two-engine split. | One written subset; `math.lua` denylist with replacements; KaTeX strict plus `--fail-if-warnings`; lint hook on every write; golden corpus in CI, re-run on every pandoc or Typst bump |
| 2 | The custom pandoc loader is our own code: dev hot reload, speed, error mapping | About 200 lines with digest caching and parallelism; error cards in dev; `+sourcepos` in lint; e2e test; fallback is the research's remark path with name-only fences |
| 3 | LLM arithmetic errors, or wrong MC keys and distractors | Blind verifier enforced by a hook; check scripts; `mc_numeric` with named mistakes and a separation check; two-method rule; content-hash ledger; quarantine instead of shipping |
| 4 | Pandoc may not detect `[x]` in *loose* task-list items (option paragraph plus `why` paragraph) | Covered by the Phase 1 golden corpus. Fallback: a tight list with the `why` as an indented `::: why`-free sub-list item that `mcq.lua` reads |
| 5 | Cheat sheet over 3 pages, or different page counts on different machines | Embedded Typst fonts only with `--ignore-system-fonts`; exact Typst pin; density presets with a 7 pt floor; overflow measured with `typst eval`; capped condense rounds; hard failure that keeps the last valid PDF |
| 6 | Figures valid but visually wrong | Templates hide placement; mandatory PNG review; facts JSON is the numeric source; `plot.custom()` is the only raw route |
| 7 | Course material leaks into the public repo | Gitignore; pre-commit hook; Claude `pre-git` hook and deny rules; CI guard; no agent memory; self-written sample course |
| 8 | Toolchain drift (pandoc 3.13 is 3 days old; Typst 0.x breaking changes; Astro 7 Markdown churn) | sha256-pinned binaries shared by local and CI; lockfiles with 7-day cooldowns; `doctor`; Astro's Markdown pipeline not used at all; one-line fallback to pandoc 3.12.1 |
| 9 | Lost browser progress (origin or port change, Safari eviction) or edits invalidating it | Fixed `localhost:4321` with strictPort; `storage.persist()`; export, import and merge; content hashes per item; `/import-progress` keeps copies |
| 10 | Claude Code's Grep and Glob may skip the gitignored `courses/` | `studykit ls --json` and explicit paths in every procedure; Read is unaffected; checked in Phase 5 |
| 11 | Cost and time of a full ingest and generation run on large courses | Text-first reading with vision only for flagged pages; 20-page chunks; sonnet for ingestion; caps of 6 agents; estimate and core-first mode; resumable status |
| 12 | Mock exams copy past exams too closely | Modelled at archetype level; n-gram similarity warning; new values and circuits required |
| 13 | YAML pitfalls (backslash escapes, YAML 1.1 vs 1.2) | Scalar-style lint from parser events; restricted PyYAML loader; `yaml` 1.2 on the Node side; no LaTeX in `course.yaml` |
