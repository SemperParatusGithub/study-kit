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
- `json.yaml`: used by lint, blind views and verification. The lint run adds `+sourcepos`, so Lua errors carry `file:line`.

**Lua modules.** `studykit.lua` branches on `FORMAT`.

| Module | What it does |
|---|---|
| `guard` | Fails on any paragraph starting with `:::`, unknown classes, nesting deeper than mcq→explanation, fence-length errors, and raw HTML. |
| `blocks` | HTML: `<aside class="sk-block sk-{name}" data-block="{name}">` with a `sk-block-title` div; hints are `<details class="sk-hint" data-index="n">`, the solution `<details class="sk-solution">`. Typst: `#sk-box(kind:…, title:…)[…]`. |
| `mcq` | Reads the ☐/☒ task list (option text, why, explanation) and validates it. HTML: `<sk-mc data-id data-type data-difficulty data-topic data-pin-last>` (plus `data-tags`/`data-source` when set) with a `sk-stem` div, `<sk-opt data-key data-correct>` children holding the option text and a hidden `sk-why`, and a hidden `sk-explanation`. Typst: options (A)–(E) with empty boxes in a seeded shuffle, plus answer-key entries. |
| `math` | Applies the denylist to every Math node. In HTML it emits `<sk-math data-tex="<base64>" data-display="0\|1"></sk-math>`. Base64 avoids entity-escaping problems, and since `guard` rejects raw HTML, authors cannot fake these elements. Typst: two fixes from Phase 1 (decimal comma, `cases` gap). The json lint run also converts to Typst, so the lint fails on what the PDF would fail on. |
| `figures` | HTML: a `<figure class="sk-fig" data-slug>` placeholder with a `sk-fig-slot` and the caption. Typst: `#figure(image("/courses/<c>/_build/figures/<slug>.svg", alt: …), caption: …)`; the path is relative to the Typst root, and a figure directory outside it is a finding. |
| `refs` | Resolves `ex:`, `mc:`, `topic:`, `exam:` and `src:` against a course ID index. HTML: `<a class="sk-ref sk-ref-{scheme}">` with route URLs. Typst: an in-document link, otherwise plain text such as „(→ Übung: Titel)“. With `-M sk-scope=file` (the quick lint of one file) targets missing from the index are not reported. |
| `meta` | HTML: appends `<script type="application/json" id="sk-meta">` with headings (level, id, text) and items: the file's own index entry, then each MC question, as `{id, kind, topic, difficulty}` (MC items add `type`; difficulty is null when the index has none). |
| `i18n` | Labels in German and English (Hinweis, Lösung, Aufgabe, Punkte …). |
| `solutions` | Typst `-M sk-solutions=inline\|appendix\|none` (default appendix): hints, solutions and MC keys stay in place, move into an appendix with back-links, or are dropped. |

### 3.2 Website: Astro 7.4.2 static, pandoc loader, custom elements, plain CSS

**Packages** (exact pins; `pnpm-lock.yaml` committed; `"packageManager": "pnpm@11.22.0"`; `site/pnpm-workspace.yaml` sets `minimumReleaseAge: 10080`):

| Kind | Packages |
|---|---|
| dependencies | `astro 7.4.2`, `katex 0.16.47`, `yaml 2.9.1` |
| devDependencies | `typescript 6.0.3` (`@astrojs/check` peers ^5 or ^6), `@astrojs/check 0.9.12`, `@playwright/test 1.64.1` |
| unit tests | `node --test` (Node 24 strips TypeScript types natively) |
| search | `pagefind 1.5.2` (CLI, run after `astro build`; see §3.5) |
| not used | remark/rehype, MDX, Tailwind, a UI framework, Mermaid |

**`astro.config.mjs`:**
- `output: 'static'`
- `server: {host: 'localhost', port: 4321}`, with `preview` on the same port
- `vite.server.strictPort: true` (progress is tied to the origin)
- `vite.server.fs.allow: [repoRoot]`
- The `markdown` section is unused.
- `ASTRO_TELEMETRY_DISABLED=1` is exported from the justfile.

**`content.config.ts`:**
- `courses`: `glob({pattern: '*/course.yaml', base: process.env.STUDYKIT_COURSES_DIR ?? '../courses'})`, with a minimal Zod schema.
- `docs`: `pandocLoader({base})`. It works as follows:
  1. Discovers summary, exercise, exam-task, MC-bank and cheat-sheet files.
  2. Splits the frontmatter, parses it with `yaml` (YAML 1.2 core schema) and runs minimal Zod checks.
  3. Runs pandoc with `-d common -d web` on the body, with concurrency equal to the CPU count.
  4. Extracts and removes `sk-meta`.
  5. Replaces each `<sk-math>` with `katex.renderToString(tex, {displayMode, throwOnError: true, strict: 'error', trust: false})`.
  6. Stores `{id: '<course>/<relpath>', data, rendered: {html, metadata: {headings}}}`. The digest is sha256 of the file bytes, the filter tree and the pandoc version, so unchanged files are skipped.
  7. In dev, `watcher.add(base)` re-renders the changed file.
- `plans` and `mastery`: `glob()` over `*/plan.yaml` and `*/progress/mastery.json`.
- **Errors:** in dev, a red error card shows `file:line` and the message. With `STUDYKIT_STRICT=1`, the build throws.

**Figures** are swapped in when the page renders. `lib/figures.ts` replaces each `data-slug` placeholder with the current `_build/figures/<slug>.web.svg` from the figure manifest, so the content cache can never serve a stale figure. Colours are `var(--fig-*)`, so the theme toggle also switches figures to dark mode.

**Routes** (UI in English; `<html lang>` set to the course language):

| Route | Purpose |
|---|---|
| `/` | Course cards: exam countdown, mastery ring, number of reviews due today, next session |
| `/c/<c>/` | **Overview tab** (§2.12) with a compact Today panel on top: exam countdown, today's session, due reviews, weakest 3 topics, "continue" |
| `/c/<c>/plan` | Week timeline, session checkboxes, "behind schedule" banner suggesting `/regenerate <c> plan` |
| `/c/<c>/summary/<topic>` | Reading view (max 70ch, sticky table of contents), objectives, `src:` links, "Test yourself" quiz |
| `/c/<c>/exercises/`, `…/<id>` | Filters for topic, difficulty and status; hint ladder; answer check; solution; self-grade |
| `/c/<c>/mc/` | **MC hub:** accuracy per topic, due count; modes Practice, Test, Mistakes, Due, Mixed |
| `/c/<c>/mc/<topic>.json` | Static endpoint with pre-rendered question HTML, loaded on demand for mixed or due pools |
| `/c/<c>/cheatsheet` | Web view in CSS columns, plus a "PDF (n/3 pages)" badge |
| `/c/<c>/exams/`, `…/<id>` | Exam mode |
| `/c/<c>/progress` | Topic bars, sure/unsure calibration, exam history, export and import |
| `/c/<c>/pdf/<name>.pdf`, `/c/<c>/src/<doc>.pdf` | Static endpoints serving `_build/pdf` and `sources/raw`. Local only; `dist` is gitignored. |

**Custom elements.** Plain TypeScript in processed `<script>` tags. Data arrives through `data-*` attributes.

| Element | Behaviour |
|---|---|
| `<sk-mc>` | Radio buttons, checkboxes, or Kprim true/false pairs. A sure/unsure toggle is required before **Check**. After checking it shows every option's `why` plus the explanation, then emits `sk:answer`. Keyboard: 1–6, Enter, N. |
| `<sk-quiz>` | Modes (details below). Seeded mulberry32 + Fisher-Yates shuffle keeps `pin-last` options in place. URL parameters: `?n=10&minutes=15&topics=…&difficulty=…`. The result screen shows score per topic, time, misconceptions, and links to the matching summary sections. |
| `<sk-hints>` | Reveals hints one at a time ("Hint 2 of 3") and counts them. |
| `<sk-answer-check>` | Numeric input with decimal comma, unit and tolerance taken from `answers`. It appears before the solution can be revealed. |
| `<sk-reveal>` | "Tried it?" confirmation before the solution opens. |
| `<sk-self-assess>` | Solved / Partly / Not yet. Using more than one hint caps the rating at "Partly". |
| `<sk-exam>` | Exam mode (details below). |
| `<sk-plan>` `<sk-progress>` `<sk-theme>` `<sk-export>` | Plan checkboxes; progress rings and bars; light/dark/system theme (an inline head script prevents a flash of the wrong theme); export and import. |

`<sk-quiz>` modes:
- **Practice:** instant feedback.
- **Test:** N questions with feedback at the end and an optional timer.
- **Mistakes:** questions answered wrong the last time.
- **Due:** questions the Leitner schedule says are due.
- **Mixed:** all banks together.

`<sk-exam>` flow:
1. A cover page shows aids, points and duration.
2. The timer stores its start time, so a reload doesn't reset it. It warns on `beforeunload`, at 10 minutes left and at 1 minute left.
3. Solutions stay `inert` until Submit or time-up.
4. After that, the rubric appears with checkboxes per task, and the MC part is scored automatically with the real exam's rule.
5. The result shows total, grade estimate and time per task, and the attempt is saved.

**Shared libraries:**
- `lib/store.ts` is the only code that touches localStorage. It has a versioned schema, migrations, try/catch on every access, and union-merge import.
- `lib/leitner.ts`:
  - Boxes 0–5 with intervals of 0, 1, 3, 7, 14 and 30 days.
  - A wrong answer sends the item to box 1.
  - A "sure" answer that is wrong sends it to box 0 and flags it as a misconception.
  - Exam clamp: no item is due after `exam_date − 2 days`, and every attempted item comes up again in the last 10 days.

**CSS:**
- `tokens.css`: `light-dark()`, `[data-theme]`, the figure palette variables `--fig-fg`, `--fig-muted`, `--fig-grid`, `--fig-c1` … `--fig-c6`, and a system font stack. KaTeX's own fonts come from the package.
- `content.css`: `sk-*` blocks and display math with `overflow-x: auto`.
- `code.css`: skylighting token classes for light and dark.
- `print.css`: A4 `@page`, no page breaks inside boxes, `<details>` opened on `beforeprint`.
- Colour is never the only signal; feedback uses `aria-live`; `prefers-reduced-motion` is respected.

### 3.3 PDF: pandoc 3.13 → Typst 0.15.1, in two explicit steps

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
| `mc.pdf` | Options (A)–(E) with empty boxes in a deterministic shuffle seeded by question ID; appendix with answer key, every `why` and the explanation |
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
- Environment: `SOURCE_DATE_EPOCH=0`, `MPL_IGNORE_SYSTEM_FONTS=1`, `MPLBACKEND=Agg`, `MPLCONFIGDIR=.cache/mpl`.
- With `locale='de'`: a house decimal-comma formatter and "U in V" axis labels.
- **Palette** of fixed, unique hex values:

  | Role | Hex |
  |---|---|
  | fg | `#1f2328` |
  | muted | `#6e7781` |
  | grid | `#d0d7de` |
  | c1–c6 (Okabe-Ito) | `#0072b2 #d55e00 #009e73 #cc79a7 #e69f00 #56b4e9` |

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
- **Phasors:** `plot.phasor({'U_R': (5, 0), 'U_L': (3, 90)}, chain=True)`.
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
  - palette colours only
  - at most 400 KB and a non-empty bounding box
  - missing-glyph warnings and mathtext parse errors are fatal, reported with the script path

### 3.5 Search: Pagefind 1.5.2

- `just build` runs `pagefind --site site/dist` after `astro build`; `just dev` serves the
  last built index (copied to `site/public/pagefind/`), so search works in dev after one build.
- Only course content is indexed: layouts put `data-pagefind-body` on the content element.
- Filters via `data-pagefind-filter`: `course`, `type` (overview, summary, exercise, mc,
  exam, cheatsheet), `topic`. Metadata: title, course, difficulty.
- `exclude_selectors: [".katex", "sk-mc [data-correct]", ".sk-solution"]`, so search never
  reveals solutions or MC keys.
- Pagefind builds one index per `<html lang>`; `force_language` is set to one value so all
  courses share one index.
- UI: the Pagefind Component UI in a `/search` route and a header search box (keyboard `/`).

## 4. Toolchain & reliability

### 4.1 Pins (`toolchain.toml` is the single source; `just doctor` asserts them exactly)

| Tool | Version | Source |
|---|---|---|
| pandoc | **3.13** (texmath 0.13.3.3) | `studykit tools install` → `.tools/bin`, sha256-checked, assets `pandoc-3.13-arm64-macOS.zip` and `pandoc-3.13-linux-amd64.tar.gz`. Fallback: one-line change to 3.12.1. |
| typst | **0.15.1** | same installer; `typst-aarch64-apple-darwin.tar.xz` and `typst-x86_64-unknown-linux-musl.tar.xz` |
| just | 1.59.0 | Homebrew; in CI a SHA-pinned setup action |
| uv / Python | 0.11.30 / 3.14.6 | uv-managed: `requires-python = ">=3.14,<3.15"`, `python-preference = "only-managed"`. Falling back to 3.13 is a one-line change. |
| node / pnpm | 24.17 / 11.22.0 | already installed (Astro needs Node ≥ 22.23.4) |
| Python (`uv.lock`) | figure stack from §3.4, plus pydantic 2.14.1, PyYAML 6.0.3, pypdfium2 5.14.0; dev: pytest 9.1.1, ruff 0.17.1 | `exclude-newer = "7 days"` |
| npm | from §3.2 | `minimumReleaseAge: 10080` |

Not needed for any core build: Chromium, TeX, Graphviz, Mermaid, rsvg or resvg. Playwright downloads its browser only for `just e2e` and in CI.

### 4.2 justfile

```just
set shell := ["bash", "-euo", "pipefail", "-c"]
root := justfile_directory()
export PATH := root / ".tools/bin" + ":" + env("PATH")
export ASTRO_TELEMETRY_DISABLED := "1"
export STUDYKIT_COURSES_DIR := env("STUDYKIT_COURSES_DIR", root / "courses")
sk := "uv run --frozen studykit"

default:
    @just --list
setup:                       # idempotent
    uv sync --frozen
    {{sk}} tools install
    pnpm -C site install --frozen-lockfile
    git config core.hooksPath .githooks
    {{sk}} doctor
doctor:                      # exact versions, embedded Typst fonts, courses/ ignored, hooks active, port 4321 free
    {{sk}} doctor
dev: (figures "")            # http://localhost:4321 (strictPort)
    pnpm -C site dev
figures course="":
    {{sk}} fig build {{course}}
pdf course="" doc="": (figures course)
    {{sk}} pdf {{course}} {{doc}}
cheatsheet course:
    {{sk}} cheatsheet fit {{course}}
lint +files:
    {{sk}} lint {{files}}
validate course="" *flags:
    {{sk}} validate {{course}} {{flags}}
verify course="" *ids:
    {{sk}} verify {{course}} {{ids}}
status course:
    {{sk}} status {{course}}
build course="": (validate course) (pdf course)
    STUDYKIT_STRICT=1 pnpm -C site build
    {{sk}} check-links site/dist
schema:
    {{sk}} schema export
test:
    uv run --frozen pytest -q
    node --test site/tests/unit/
    {{sk}} golden            # math, block and mcq corpus through KaTeX and pandoc→Typst
e2e:
    pnpm -C site exec playwright test
tutor course:
    claude --agent tutor "{{course}}"
examine course mode="mixed":
    claude --agent examiner "{{course}} {{mode}}"
ci:
    just doctor test
    {{sk}} schema export --check
    STUDYKIT_COURSES_DIR={{root}}/examples STUDYKIT_STRICT=1 just build sample-course
    STUDYKIT_COURSES_DIR={{root}}/examples just validate sample-course --release
```

### 4.3 Validation (`studykit validate [course] [--paths …] [--quick] [--release] [--json]`)

Every finding has the form `path:line:col SK-CODE message (fix: …)`. A code is the stage family from the table plus a rule (`SK-MCQ-COUNT`, `SK-YAML-ESCAPE`); warnings keep the shape and start the message with `warning:`. Each code is documented in `content-format/errors.md` with a fix recipe and the pipeline step that owns it. `--quick` covers the stages up to and including Math plus the Pandoc backstop, for one file in about 1 s, and is used by the hook.

| Stage | Checks | Code |
|---|---|---|
| Structure | required files, ID patterns, unique and non-retired IDs, acyclic prerequisites, topics ⊆ course topics | SK-STRUCT |
| Schema | pydantic validation of YAML and frontmatter; scalar-style lint; control characters; label and rubric fields are text plus inline math only | SK-SCHEMA, SK-YAML |
| Fences | line scan outside code: exact fence forms, allowed placement, depth, blank lines | SK-BLOCK |
| MC | option counts per type, `[x]` invariants, a `why` on every option, one explanation, `pin-last` rule, no "all of the above", bank-bias warnings | SK-MCQ |
| Math | denylist; KaTeX strict via `check-math.mjs`; pandoc→Typst with zero warnings; hint-leak rule | SK-MATH |
| References | `ex: mc: topic: exam: src: fig:` targets, plan refs, exam task files and archetypes | SK-REF |
| Pandoc | the Lua filter set with the json target, on files the stages above left without errors: catches what only the filter sees (raw HTML, fixed-up Typst that fails) under the filter's family codes; file scope with `--quick` | SK-* |
| Figures | build plus SVG validation, facts present, unreferenced scripts (warning) | SK-FIG |
| Verification | ledger complete and fresh; disputed and quarantined items listed | SK-VER |
| PDF | every document compiles with no warnings; cheat sheet ≤ its limit | SK-PDF |
| Site | strict `astro build`, `astro check`, internal link and anchor check over `dist/` | SK-SITE |
| Coverage | each topic has a summary, ≥ 4 exercises across difficulties, ≥ 10 MC questions with the target type mix; exam points and time within the profile | SK-COV |

### 4.4 Tests

- **pytest:**
  - key points: `cos x = x`, touching roots, poles
  - control margins compared with `scipy.signal` and closed forms
  - every figure template renders and validates, with a `facts.json` snapshot (never SVG bytes)
  - lint fixtures: each forbidden construct produces its code and its replacement hint
  - `mc_numeric`, the scheduler and Leitner clamp, `status`, and ingest of a generated two-page PDF
- **Golden corpus** (compiled in CI through both KaTeX and pandoc→Typst):
  - `tests/golden/math.md`: about 120 EE and math formulas, including decimal comma, `\underline`, `\mathrm{k\Omega}`, `cases`, `aligned` and determinants
  - `blocks.md` and `mcq.md`: every container form and all three MC types
- **node --test:** scoring for every type and mode, shuffle determinism with `pin-last`, Leitner exam clamp, store migration and merge.
- **Playwright** (`e2e`):
  1. Answer one MC question of each type and check the score.
  2. Reload and check that progress persisted.
  3. Start an exam, reload, and check that the timer kept running.
  4. Submit and check that solutions and the rubric appear.

### 4.5 GitHub Actions

- **`ci.yml`** (push, PR, and a weekly scheduled run) on `ubuntu-24.04`, with every action pinned by commit SHA:
  1. setup-uv, `pnpm/action-setup`, `setup-node@24`, setup-just 1.59.0
  2. `just setup`, which fetches the same pinned pandoc and typst binaries by hash
  3. `just ci`, then `just e2e`
  4. Upload the sample-course PDFs and `site/dist` as artifacts
- **`guard.yml`:**
  - every commit in the range is a Conventional Commit with no `Co-Authored-By`
  - `git ls-files courses` returns only `courses/README.md`
  - no PDFs are tracked outside `tests/fixtures`

## 5. Claude Code layer

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
