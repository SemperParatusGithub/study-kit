# study-kit architecture

This is the reference specification for study-kit. It was produced by a research and
judge-panel design pass (4 research agents, 3 design lenses, 1 judge) on 2026-10-29 and
then amended with the user's decisions. When code and this document disagree, fix one of
them in the same change.

## 0. Decisions

| Area | Decision |
|---|---|
| License | MIT |
| Unverified items | Quarantined: hidden on the site and in PDFs, listed in the report. As built, an item is quarantined when it is still disputed or unverified after two author fix rounds (§2.10, §5.3); an item no verifier has checked yet stays visible, and `validate --release` warns about it |
| MC defaults (no past exams) | 10–25 questions per topic by weight; 60% single, 25% multi, 15% Kprim; multi all-or-nothing; no negative marking. Past exams override. |
| Search | Pagefind in v1 (§3.5) |
| Course data | `courses/` inside the repo, gitignored; never committed |
| Language | Skills, agents, UI and code in English; generated content follows `course.lang` |
| Commits | Conventional Commits, one logical change each, never a Co-Authored-By trailer |

## 1. Repository layout

Everything below exists; the optional Phase 7 (§6) would add to it.

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
├── docs/architecture.md            # this specification
├── docs/walkthrough.md             # registering a subject and studying it, step by step
├── docs/content-format/errors.md   # every SK code with its fix and owner (§4.3)
├── src/studykit/
│   ├── cli.py                      # argparse (stdlib); --json on doctor, ls, index, lint, validate, render, check-links, pdf, cheatsheet fit,
│   │                               # calc, verify, plan, status, progress import|log|report, ingest and pipeline
│   ├── tools.py                    # `tools install`: pandoc, typst and just → .tools/bin, sha256-checked
│   ├── doctor.py                   # `doctor`: tool versions, site packages, Typst fonts, git hooks, courses/ ignored, port 4321
│   ├── model.py                    # pydantic models: the single schema source
│   ├── yamlio.py                   # restricted SafeLoader (no YAML-1.1 yes/no/on/off, no sexagesimal) + scalar-style lint
│   ├── content.py                  # discovery, frontmatter split, fence-line and math scanners, MC parser
│   ├── index.py                    # `index`: _build/index.json (ids, topics, exams, sources, figures)
│   ├── findings.py                 # Finding (path:line:col SK-CODE message (fix: …)) and its parser
│   ├── pandoc.py                   # run pandoc with the shared defaults and filter metadata (targets: html | typst | json)
│   ├── lint.py  validate.py        # per-file lint, also the PostToolUse hook `lint --hook` (§5.1) / full validation, findings as SK-codes
│   ├── render.py                   # `render`: the site loader's bridge to pandoc (§3.2)
│   ├── sitecheck.py                # the Site stage of `validate --release` (§4.3)
│   ├── checklinks.py               # `check-links`: internal links and anchors of the built site
│   ├── golden.py                   # `golden`: the golden math corpus through KaTeX and pandoc → Typst
│   ├── figures/                    # house.mplstyle palette.py core.py keypoints.py plot.py signals.py
│   │                               # circuit.py block.py graph.py labels.py builtins.py
│   │                               # finalize.py validate.py child.py runner.py
│   ├── check.py  verify.py  blind.py   # check-script API; `verify`: runner, ledger, quarantine (§2.10); `blind`: blind views (§5.3)
│   ├── hook.py                     # `hook verifier-guard|pre-git`: Claude Code PreToolUse hooks (§5.1, §5.3)
│   ├── pdf.py                      # `pdf`: assemble → pandoc → typst per document, digest cache, _build/pdf/manifest.json (§3.3)
│   ├── cheatsheet.py               # `cheatsheet fit`: density loop 0–4, overflow measured with `typst eval` (§3.3)
│   ├── ingest.py                   # `ingest scan|init|extract|add|round2`: inventory, source copy, manifest, page text, chunk plan (§5.4)
│   ├── pipeline.py                 # `pipeline status|report`: the output-derived state of /register-new-subject (§5.4)
│   ├── plan.py                     # `plan`: deterministic study-plan scheduler (§2.9)
│   ├── progress.py                 # `progress import|log|report`: browser export, examiner log, mastery (§2.11)
│   ├── status.py                   # `status`: the study status of /study-status (§2.11)
│   └── calc.py                     # `calc "<expr>"`: safe SymPy calculator with j, phasor helpers and units, for authors, verifier, tutor and examiner (§5.3)
├── pandoc/
│   ├── defaults/common.yaml web.yaml typst.yaml json.yaml
│   ├── filters/studykit.lua + lib/{guard,blocks,mcq,math,figures,alttext,refs,meta,i18n,solutions,document}.lua
│   └── math-denylist.json          # denied math constructs and their replacements (§2.3), read by math.lua and lint
├── typst/
│   ├── studykit.typ                # house library: page setup, boxes, MC, appendix and key, exam cover, plan, cheat-sheet densities
│   └── pandoc-template.typ         # ~15 lines; imports the house library and calls sk-doc
├── site/                           # Astro (kept out of the repo root so Vite never watches .venv)
│   ├── package.json  pnpm-workspace.yaml  pnpm-lock.yaml  astro.config.mjs  tsconfig.json
│   ├── pagefind.yml  playwright.config.ts
│   ├── src/content.config.ts
│   ├── src/loaders/pandoc.ts       # custom content loader over `studykit render`
│   ├── src/lib/{katex,figures,courses,pdf,store,scoring,shuffle,leitner,answer,stats,plan,format,html,findings,types}.ts
│   ├── src/lib/sys.mjs             # the only module with node: imports (the site has no @types/node)
│   ├── src/elements/*.ts           # custom elements (§3.2), dashboard.ts (fills the shell's placeholders), util.ts, index.ts
│   ├── src/layouts/  src/pages/  src/components/  src/scripts/site.ts
│   ├── src/pages/c/[course]/{pdf/[name],src/[doc]}.pdf.ts   # built PDFs and lecture sources (§3.2)
│   ├── src/styles/{tokens,base,content,elements,code,print}.css
│   ├── scripts/check-math.mjs      # KaTeX strict check, called by the Math stage (lint, validate) and `golden`
│   ├── scripts/pagefind.mjs        # search index after `astro build` (§3.5)
│   └── tests/unit/*.test.ts  tests/e2e/*.spec.ts  tests/elements/ (harness with its own Playwright config and tsconfig.json)
├── schemas/*.schema.json           # generated from pydantic; committed; drift-checked by `just test`
├── examples/
│   ├── sample-course/              # self-written German mini course `sample-course` using every feature (CI fixture)
│   └── sample-materials/           # self-written Typst sources (op-amp circuits) for fake slides, script, exercise sheet, past exam
│                                   # and one rasterised "scan"; `just sample-materials` builds the PDFs into its gitignored _build/
├── tests/py/                       # pytest (§4.4); test_claude.py checks the .claude/ layer; materials.py makes lecture PDFs at test time
├── tests/golden/{math.md,math-denied.md,math.typ.snap,blocks.md,mcq.md,figures/}
├── tests/fixtures/{bad/<SK-CODE>/,courses/mini/,pandoc/{ok,bad}/,figures/gallery/,progress/}
├── .claude/
│   ├── settings.json               # attribution, permissions, the lint and pre-git hooks (§5.1)
│   ├── agents/                     # ingester.md exam-analyst.md author.md verifier.md tutor.md examiner.md (§5.3)
│   └── skills/                     # §5.2: <name>/SKILL.md per skill
│       ├── register-new-subject/  add-material/   # user commands that build and extend a course (§5.4)
│       ├── regenerate/  verify/  tutor/  examine/  import-progress/  study-status/   # user commands
│       ├── ingest/                 # SKILL.md, exam-analysis.md, templates/ (notes, exam profile with and without past exams, notation, outline)
│       ├── content-format/         # SKILL.md, templates/ (course.yaml, overview, summary, exercises, MC bank, exam/, cheat sheet, plan, exam profile, figure)
│       ├── authoring/              # SKILL.md, parts/{overview,summary,exercises,mc,exam,cheatsheet,plan}.md
│       ├── figures/                # SKILL.md, reference.md (the studykit.figures API)
│       └── verify-protocol/        # SKILL.md, recipes.md (check scripts: MNA, phasors, Laplace, margins, MC)
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
├── plan.yaml                       # written by `studykit plan` (§2.9); Claude writes only each session's goal and note
├── figures/<slug>.py
├── checks/<item-id>.py | <item-id>.json    # verifier output; <item-id>.<tag>.py|json a second method
├── sources/                        # the lecture material and what was read from it (§5.4)
│   ├── manifest.yaml               # `studykit ingest`: documents (id, kind, sha256, pages, origin), skipped files, the ask-round answers
│   ├── raw/<doc>.pdf               # `ingest init|add`: copies of the user's PDFs; the user's folder is only read
│   ├── text/<doc>/index.json  p0001.txt   # `ingest extract`: page text and per-page flags (visual, scanned, why)
│   ├── text/<doc>/p0001.vision.md  # the ingester's transcription of a scanned page
│   ├── chunks.yaml                 # `ingest extract`: chunks `<doc>-cNN` of at most 20 pages with flagged and scanned pages
│   ├── notes/<chunk>.md            # the ingester's digest of one chunk (frontmatter `ChunkNotes`)
│   └── outline.md                  # the synthesis step: topics, their sources and every chunk id
├── analysis/exam-profile.yaml  notation.yaml   # the exam-analyst: archetypes, MC rules, topic weights; j vs. i, phasors, decimal sign
├── state/verify/<item-id>.json     # ledger, one file per item (no locking); report.md
├── state/pipeline/report.md        # `studykit pipeline report` (step 14), with the fingerprint that marks it current
├── progress/state.json  browser/*.json  examiner.jsonl  mastery.json  report.md   # §2.11, written by `studykit progress`
├── _history/<timestamp>/…          # copies saved by /regenerate before overwriting (UTC timestamp, same relative paths)
└── _build/{index.json,figures,typ,pdf,blind,logs}   # typ: assembled .md/.typ and digests; pdf: PDFs and manifest.json; logs: pandoc logs
```

Discovery (`content.py`) knows the content kinds above (course, overview, summary, exercise,
mc, exam, exam task, exam MC, cheat sheet, plan, figure scripts, exam profile, notation,
manifest, chunk plan, outline, chunk notes). It never enters `_build`, `_history`, `state`,
`progress`, `checks`, `sources/raw` and `sources/text` (so page texts and transcriptions are
neither validated nor linted); any other file in the course is SK-STRUCT-PATH. Chunk notes are Markdown like the content files (the Fences, Math and
References stages check them) but are never rendered, so the Pandoc stage skips them.

**Schemas.** The pydantic models in `model.py` are the single source. `just schema` exports them to `schemas/*.schema.json`, which editors use through `# yaml-language-server: $schema=…`; `just test` fails when the committed files are stale (`schema export --check`). The ingest files have models too (§5.4): `sources/manifest.yaml` (`SourceManifest`: per document id, title, file in `sources/raw/`, origin in the user's folder, sha256, bytes, pages, kind, where the kind came from, text-layer share, added and updated days; the skipped files; the ask-round answers), `sources/chunks.yaml` (`ChunkPlan`), the frontmatter of `sources/notes/<chunk>.md` (`ChunkNotes`), `analysis/exam-profile.yaml` (`ExamProfile`; archetype, MC-type and topic-weight shares add up to 1, SK-SCHEMA-SHARES) and `analysis/notation.yaml` (`Notation`). The References stage checks that they agree (SK-REF-CHUNK, SK-REF-MISSING); validate reads the profile's archetype ids and the manifest's document ids and page counts. The site declares only a minimal `astro/zod` schema for the fields it renders, so a site that no longer matches the data fails the strict build of the sample course.

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
cheatsheet: {allowed: true, max_pages: 2}   # validator caps at 3; the PDF's page limit (§3.3); allowed: false → no cheatsheet.pdf
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
                                # (`ingest init` writes a draft with one placeholder topic `draft`, which a ready course may not keep: SK-STRUCT-DRAFT)
```

### 2.3 Markdown conventions: one dialect, one parser

**Reader:** `commonmark_x-smart-raw_html-raw_attribute-yaml_metadata_block-alerts-emoji`.
- `studykit.pandoc` blanks the frontmatter (line numbers stay right) before pandoc reads a
  file; the site renders through `studykit render`, so the site and the tools build the
  pandoc argv in one place.
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
answers:                          # the key; the website's answer check and verify.py both use it
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
- Symbolic answers are written `{key: H, expr: '1/(1+s*R*C)', symbols: [s, R, C]}`. The website's answer check (`lib/answer.ts`) evaluates input and reference at random positive sample points with complex arithmetic; `verify.py` compares with SymPy simplification, then at sample points.
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

- [ ] Bei $f_\mathrm{g}$ ist der Betrag auf die Hälfte abgefallen.

  Er ist auf $1/\sqrt{2} \approx 0{,}707$ abgefallen, also $-3\,\mathrm{dB}$; die Hälfte wären $-6\,\mathrm{dB}$.

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

**In the PDF** (`mcq.lua` emits `#sk-mcq`; `typst/studykit.typ` sets it):
- Questions are numbered through the document. Below the stem, an italic line names the
  type in the course language („Genau eine Antwort ist richtig.“, „Eine oder mehrere
  Antworten sind richtig.“, „Beurteilen Sie jede Aussage: richtig oder falsch.“).
- single and multi: one row per option with an empty box, its key (A)–(F) and the text.
  Kprim: a table of the statements with two boxes per row, under „richtig“ and „falsch“.
- The order is the deterministic shuffle above, which `<sk-mc>` uses too (`lib/shuffle.ts`),
  so a letter means the same option on the site and on paper.
- Where the key goes follows the document's solution mode (§3.1 `solutions`). `mc.pdf`
  collects it in an appendix „Lösungsschlüssel“: first a two-column table of number,
  answer and question id (Kprim: „richtig: A, C“; each number links to its question), then
  one entry per question with the correct keys (Kprim: the true and the false ones), every
  option marked ✓ or ✗ (Kprim: richtig or falsch) with its `why`, the explanation and a
  link back „↑ zur Frage“. An exam's MC part has no key; the exam's solutions PDF shows each
  question's key inline below it.

**Lint rules** (`mcq.lua` and the MC stage of `validate.py`, which `lint` runs too):
- `single` has 3–5 options with exactly one `[x]`.
- `multi` has 4–6 options with at least one `[x]` and at least one `[ ]`.
- `kprim` has exactly 4 options.
- Every option has a `why`, and there is exactly one explanation.
- No "all of the above".
- Explanations never refer to options by letter, because options are shuffled.
- Numeric questions require a check script. The verifier writes it after authoring, so
  the Verification stage checks this, not lint (SK-VER-CHECK with `--release`).

**Bank-level warnings** (SK-MCQ-BIAS, for banks with at least four single-choice questions):
- the correct option is the strictly longest one in more than half of them
- after the deterministic PDF shuffle, one letter is the correct answer in more than half of them

**Generation targets.**
- `mc_per_topic: auto` gives 10–25 questions per topic, scaled by weight
  (`max(10, ⌈25 · weight⌉)`, at most 25; SK-COV-MC).
- The type mix follows the exam profile. Without one it is 60% single, 25% multi and 15% Kprim.
  Validation only warns when a bank lacks a type of `course.exam.mc.types` that the
  profile's `mc.type_mix` gives a share (every such type without a profile mix).
- Distractors come from a catalogue of electrical-engineering misconceptions in
  `authoring/parts/mc.md` (§5.2): a forgotten 2π, √2 (amplitude vs. RMS), dB vs. linear, the
  sign of the phase, series vs. parallel, a wrong power of ten, degrees vs. radians, and more.

**Scoring** (`site/src/lib/scoring.ts`; `progress.mc_score` mirrors the practice score for
examiner results, §2.11). An option is
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

**Check script for a numeric question** (`checks/mc-rc-filter-003.py`, written blind by the verifier from `studykit blind`, whose options are in source order A–F):

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

A failure of 1–3 disputes the question; a failure of 4 means the check misread an option,
so the item stays unverified until the check is fixed. A question whose every option states
a number needs this check: a letter answer to it (`mc_answer` or a JSON answer) is a check
error.

**Conceptual questions**: the verifier answers blind into `checks/<id>.json` (or a script ending with `mc_answer(...)`; Kprim takes `{"A": true, …}` or the list of true statements):

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
- PDF: `<exam>.pdf` to write on (cover, tasks, MC part, no solutions) and
  `<exam>-solutions.pdf` (solutions with rubric) (§3.3).

### 2.8 Cheat sheet (`cheatsheet.md`)

- **Frontmatter:** `title`, `max_pages`, which must be ≤ `course.cheatsheet.max_pages` ≤ 3, and `priority` (topic IDs).
- **Body:** a `##` section per topic containing formulas, small tables, definition/note/warning boxes, and small figures.
- **Not allowed:** exercises and hints.
- **PDF:** `cheatsheet.pdf` in two columns, set at the first density (9 down to 7 pt) that
  fits `min(3, course.cheatsheet.max_pages, max_pages)` pages (§3.3).

### 2.9 Study plan (`plan.yaml`)

`studykit plan <course> [--from YYYY-MM-DD] [--dry-run] [--json]` (`plan.py`) is
deterministic: the same course, content, progress, old plan and first day give the same
`plan.yaml` byte for byte. Claude writes only the `goal` and `note` text afterwards
(`authoring/parts/plan.md`, run by `/regenerate <c> plan` and `/import-progress`); the
output lists the sessions without a goal (`goals_missing` in `--json`, which also has the
weekly split, the learning sessions per topic, the mock exam dates, `kept` and the whole
plan). The written plan is read back and checked like validate checks it (schema,
references) before it replaces the old one; `--dry-run` writes nothing. Its findings are
SK-PLAN codes at `course.yaml` (`content-format/errors.md`), or the codes of an old
`plan.yaml` or `progress/` file that does not read; an error (exit code 1) writes no plan.
Quarantined items (§2.10) are left out, as on the site. The sample course's `plan.yaml` is
still the hand-written one from Phase 3. Validate checks plan refs (SK-REF-SCHEME,
SK-REF-MISSING) and that no session lies on or after the exam (SK-STRUCT-PLAN, a warning
when `exam_date` differs from `course.yaml`).

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
- Days run from `--from` (default today, never before `study.start`) to the day before the
  exam, outside `study.blocked`. `study.hours_per_week` is the weekly budget, split into
  n = round(budget / 120 min) sessions (1–6) on fixed weekdays, each budget / n minutes
  rounded down to 15; the day before the exam always has a session:

  | n | Weekdays |
  |---|---|
  | 1 | Sat |
  | 2 | Mon, Thu |
  | 3 | Mon, Wed, Sat |
  | 4 | Mon, Tue, Thu, Sat |
  | 5 | Mon to Fri |
  | 6 | Mon to Sat |

- No calendar week (Monday to Sunday) exceeds the budget: in a week with a mock exam, a done
  session or the extra last day the other sessions get shorter, down to 45 minutes, and
  below that one is dropped, the latest of the first kind present in this order: buffer,
  practice, final MC round, mock-exam review. Mock exams are never dropped.
- The last day is for the cheat sheet (a review of every topic when none is allowed). Mock
  exams (`targets.mock_exams`, at most those the course has and that were not taken) take
  the exam's duration + 30 minutes and are spread over the last 14 days, the last at least
  4 days before the exam; the next session reviews each. The session before the last day
  is a final MC round over every topic; the last session before the final 14 days is a
  buffer when at least four sessions lie before them.
- Learning takes 60 % of the sessions before the final 14 days, at least one per topic and
  never more than a topic has exercises: topics in prerequisite order (teaching order among
  free ones), shared in proportion to weight × mean exercise difficulty, × 1.5 for focus
  topics, skipped topics left out. A topic's first session reads its summary; its exercises
  follow from easy to hard, each session with MC practice of the topic (10 questions, 5 in
  the session that reads the summary, at most the bank's size). The final MC round has 10
  of every topic.
- Reviews follow at +1, +3 and +7 days after a topic's last learning session (in the first
  session on or after that day): the review joins a learning session, or a free session
  becomes a review session.
- The remaining sessions practise learned topics (two exercises, unsolved and harder first,
  MC practice, a review of a second topic) in a smooth weighted round robin by the same
  shares × (1 + 3 · (1 − accuracy)), with the accuracy of `lib/stats.ts` over the progress
  in `progress/` (browser state plus examiner answers), so weak topics come first and most
  often.
- Replanning keeps every session `progress/` marks done and plans the rest from the first
  day; past sessions that are not done are dropped. A topic whose learning sessions are all
  done is not learned again; exercises solved or in a done session leave its learning
  sessions. A new session keeps the old `goal` and `note` of its id when kind, topics and
  tasks are unchanged.
- An unknown exam date plans 12 weeks and writes `exam_date: null` (SK-PLAN-DATE warning);
  SK-PLAN-STUDY and SK-PLAN-BUDGET report a missing or too small budget
  (`content-format/errors.md`).

`plan.pdf` lists the sessions week by week („Woche n · dates“), one row each with a box to
tick, date, minutes, kind, goal, topics and tasks (§3.3).

### 2.10 Verification ledger (`state/verify/<item-id>.json`)

`studykit verify <course> [id|topic|exam|all]` (`verify.py`) runs each item's check
(`checks/<id>.py` with the project's Python in the course directory, no shell, `--timeout`
seconds, default 120; or `checks/<id>.json`), compares it with the key and writes one
ledger file per exercise, exam task and MC question (`model.VerifyEntry`,
`schemas/verify.schema.json`). An item without a check is listed as `no-check` and keeps
its entry. A run exits with 1 when a check mismatched, errored or its item is quarantined
(`--confirm` when the second method errored), with 2 on a usage error (an unknown id, a
second method without a fresh entry).

```
studykit verify <course> [target] [--status | --confirm FILE [--method …] | --dispute --note … [--computed key=value …]
                                   | --quarantine --note … | --clear] [--report] [--show-key] [--timeout s] [--json]
```

```json
{"schema": 1, "item": "ex-rc-tp-grenzfrequenz", "kind": "exercise",
 "path": "exercises/rc-filter/ex-rc-tp-grenzfrequenz.md", "content_sha256": "…",
 "status": "verified", "method": "script", "check": "checks/ex-rc-tp-grenzfrequenz.py",
 "check_sha256": "…", "rounds": 0,
 "results": [{"key": "fg", "expected": 1591.55, "computed": 1591.549, "unit": "Hz",
              "abs_err": 0.001, "rel_err": 6.3e-7, "tol": 1.59, "ok": true}],
 "checked_at": "2026-10-30T10:12:00Z", "verified_at": "2026-10-30T10:12:00Z"}
```

- A check script ends with one `studykit.check` call (`check.py`), which prints the JSON
  line the runner reads from the end of its output: `answers(**values)` (numbers in the
  key's unit, `quantity(x, "kHz")` in another unit of the same kind, SymPy expressions for
  symbolic keys), `mc_answer(letters)`, `mc_numeric(…)` (§2.6) or `review(agree, reason)`
  for an item without keys (on an item with keys, `review` is a check error).
  `verify-protocol/recipes.md` (§5.2) has worked recipes.
- Exercises and exam tasks compare every `answers` key: numbers within `atol + rtol·|value|`
  (SI prefixes convert; `rad/s` and `1/s` count as the same unit), expressions by SymPy
  simplification, then at sample points. MC questions compare the set of correct letters
  (single, multi), each statement (Kprim) or the `mc_numeric` assertions; a blind answer
  marked `ambiguous` is a dispute, and a `confidence` other than `high` is a warning. A
  `review` that disagrees is a dispute; whether its reason matches the solution is judged
  by `/verify` (§5.3).
- `status`: `unverified` (no check, a check that did not run to a result, or two methods
  that disagree), `verified` (with earlier disputes it counts as fixed), `disputed`, or
  `quarantined`. `method` is `script`, `blind` (a JSON answer) or `manual` (set by hand).
- `content_sha256` is the sha256 of the item's source: the whole file of an exercise or exam
  task, the fenced block of an MC question. If it no longer matches, the entry is stale
  (SK-VER-STALE) and the next run checks the new version.
- `disputes` records each disagreement with the verifier's numbers and the key, per version
  of the item; `rounds` counts the author fix rounds (versions disputed after the first).
  The dispute after the second fix round quarantines the item. `--confirm
  checks/<id>.<tag>.py` (or `.json`; another file than the first check, on an entry that is
  not stale) records a second method in `confirmations`: one that reproduces a dispute
  confirms it, one that sides with the key (or contradicts a verified result) sends the
  item back to unverified. `--dispute --note … --computed key=value` (a confirmed dispute)
  and `--quarantine --note …` record either by hand; `--clear` deletes entries (also
  `stale` and `orphans`). Ledger files are written by `studykit verify` only.
- `--status` runs nothing and lists every selected item with `status`, `outcome`
  (`no-ledger`, `stale` or the status), `stale`, `rounds`, `results`, `problems`, `note`,
  `confirmed` (a second method reproduced the last dispute of this version) and the
  `confirmations` of this version; every result has the counts per status (plus `fixed`,
  `stale` and `no_check`) and the quarantined items.
- Quarantined items are hidden from the site and the PDFs (§0): the course index lists them
  under `quarantined`, the render bridge skips their exercise and exam-task files, the filter
  drops their MC questions from HTML and Typst and turns links to them into plain text, and
  an exam loses their tasks and points (its pass mark keeps its share). `plan`, `progress
  report` and `status` read the course the same way, so their stats, plans and mock-exam
  verdicts match the site. A check that passes again shows the item again. `verify --report`
  writes `state/verify/report.md` with the counts and every item that is not verified
  (quarantined, disputed, stale, unverified), each with its reason.
- The text output never shows the key (the verifier reads it), nor does `--confirm`'s;
  `--json` and `--show-key` do, so the verifier's guard hook denies both (§5.3).
- Summary chapters and the cheat sheet get formula audits too, in `checks/sum-<topic>.py`
  *(planned; validate already accepts these files)*.

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

**Repo side** (`progress.py`; `progress.py` mirrors `lib/leitner.ts`, the merge of
`lib/store.ts` and `lib/stats.ts`, and `tests/py/test_progress.py` runs the site's own
TypeScript on the shared cases in `tests/fixtures/progress/` and compares every value):
- `studykit progress import <course> <file> [--dry-run] [--json]` (what `/import-progress`
  runs) validates an export against `model.Progress` and the site's timestamp form, refuses
  a file of another course, without a course or with another schema (SK-PROGRESS codes),
  merges it into `progress/state.json` with the site's union merge, keeps the file in
  `progress/browser/` (once) and reports what changed: new entries, MC attempts, ratings,
  mock exam attempts, sessions newly done.
- The examiner appends results through `studykit progress log <course> --json-line '{…}'`
  (repeatable, or JSON lines on stdin) to `progress/examiner.jsonl`, one
  `model.ExaminerResult` per line (`schemas/examiner.schema.json`): mode, kind (`mc`,
  `exercise`, `exam-task`, `oral`), topic, item, score 0–1, for MC `chosen` and `conf`,
  optional `points`/`max_points` and a one-line `finding`. Items and topics are checked
  against the course; an MC result's score is the site's score of `chosen` (computed when
  left out, refused when it differs); a batch is written all or nothing.
- `studykit progress report <course> [--today D] [--json]` writes `mastery.json`
  (`model.Mastery`, `schemas/mastery.schema.json`) and `report.md` deterministically. The
  examiner's MC answers count as attempts (folded in with the same Leitner step), then the
  figures are those of `lib/stats.ts`:
  - `overall`: mastery as defined above; `topics.<id>.mastery`: the topic accuracy over the
    last 10 attempts (null without answers)
  - due reviews (MC and exercises, with ids), misconceptions (last attempt sure but not fully
    right), exercise status per exercise and per topic
  - exam-task score fraction per topic from each mock exam's last attempt, mock exam results
    (best, last, passed)
  - examiner results per topic (mean of the last 10) and the last 20 findings
- `studykit status <course> [--today D] [--json]` (`status.py`, what `/study-status`
  prints): days left, plan adherence (done sessions, and past sessions not done as the
  site's banner counts them), the next three sessions, the three weakest answered topics and
  the topics not practised yet (they count 0 in the mastery), reviews
  due, the last mock exam and hints for the next step. It is the student's status; where
  `/register-new-subject` stands is `studykit pipeline status` (§5.4).
- The site reads `mastery.json` at build time (`lib/courses.ts`, straight from the course directory: `overall`, else the mean of `topics.<id>.mastery`), so examiner results show up on the course home page until the browser has answers of its own.

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
- Written by the `author` agent with `authoring/parts/overview.md` (§5.2):
  `/regenerate <course> overview` re-runs it, and `/regenerate <course> all` (like the
  author wave of `/register-new-subject`, §5.4 step 7) writes it first so the other parts
  can link to it. It links only
  what exists, so the exercises and mock exams get their links when the course is
  published (§5.4 step 13) or at the end of `/regenerate <course> all`.
- Web: `/c/<c>/` (the Overview tab). PDF: `overview.pdf`, also the first chapter of
  `summary.pdf`.
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
- `json.yaml`: `to: json` and the reader with `+sourcepos`, so findings carry `file:line:col`; used by lint and validate. The filter only checks and returns the AST unchanged.

**Metadata.** `studykit.pandoc` builds the argv; the filter needs `-M sk-index` (the course's `_build/index.json`), `sk-course`, `sk-lang`, `sk-file` (the course-relative path, which decides the file kind), for Typst `sk-solutions` and `sk-figdir`, and optionally `sk-scope=course|file`; `studykit pdf` adds `sk-doc=<kind>` for an assembled document (`document` below). pandoc runs in the repository root on a temporary copy whose frontmatter is blanked.

**Findings.** The filter collects every finding of a document and prints them to stderr as `<sk-file>:<line>:<col> SK-CODE message (fix: …)`, then exits with status 65. A rule that validate checks too has the same code in both (e.g. SK-REF-FIGURE, SK-BLOCK-FENCE, SK-MCQ-KEY); rules only the filter sees have their own codes (SK-BLOCK-RAW, SK-BLOCK-MARKDOWN, SK-REF-LINK, SK-MATH-TYPST). A run without the metadata above, or with an unreadable index or `math-denylist.json`, is SK-PANDOC-FAIL.

**Lua modules.** `studykit.lua` branches on `FORMAT` (`html*`, `typst`, anything else: validation only).

| Module | What it does |
|---|---|
| `guard` | Fails on any paragraph starting with `:::`, unknown classes, blocks in the wrong file kind, nesting other than mcq→explanation (a block inside a list counts), fence lines that are not exactly `::: name`, `:::: {.mcq …}`, `:::` or `::::` (checked on the source lines), hint and solution count and position, code blocks without exactly one allowed language, raw HTML and other raw blocks, H1 in the body, footnotes, and `{…}` attributes on headings, spans, inline code and tables (the HTML writer would copy an `onclick` onto the element). |
| `blocks` | HTML: `<aside class="sk-block sk-{name}" data-block="{name}">` with a `sk-block-title` div; hints are `<details class="sk-hint" data-index="n">`, the solution `<details class="sk-solution">`. Typst: `#sk-box(kind:…, title:…)[…]`. |
| `mcq` | Reads the ☐/☒ task list (option text, why, explanation) and validates it. HTML: `<sk-mc data-id data-type data-difficulty data-topic data-pin-last>` (plus `data-tags`/`data-source` when set) with a `sk-stem` div, `<sk-opt data-key data-correct>` children holding `<div class="sk-opt-text">` and a hidden `sk-why`, and a hidden `sk-explanation`; options stay in source order (the site shuffles, and its loader adds `data-h`). Typst: `#sk-mcq` with options (A)–(F) in the seeded shuffle and a number that runs through the document; the key goes where the solution mode puts it (§2.6). |
| `math` | Applies the denylist to every Math node. In HTML it emits `<sk-math data-tex="<base64>" data-display="0\|1"></sk-math>`. Base64 avoids entity-escaping problems, and since `guard` rejects raw HTML, authors cannot fake these elements. Also rejects environments outside the allowlist, non-ASCII outside `\text{…}` (SK-MATH-KATEX, so it shows up without KaTeX too) and a space command between two digits (SK-MATH-THINSPACE). Typst and json: each node is converted to Typst on its own, and a conversion warning is SK-MATH-TYPST, so the lint fails on what the PDF would fail on; Typst then gets two fixes from Phase 1 (decimal comma, `cases` gap), and a display that sets formulas apart with top-level `\qquad` becomes `#sk-formulas(…)`, one equation per formula, wrapping between them. |
| `figures` | Checks `fig:` images (alone in the paragraph, no attributes, a caption; SK-REF-FIGURE, SK-REF-IMAGE, SK-REF-MISSING). HTML: a `<figure class="sk-fig" data-slug>` placeholder with a `sk-fig-slot` and the caption. Typst: `#figure(image("/courses/<c>/_build/figures/<slug>.svg", alt: …), caption: …)`; the path is relative to the Typst root, and a figure directory outside it is SK-PANDOC-FAIL. |
| `alttext` | Typst only: the figure's `alt:` text from the caption, with math read as plain text (`\underline{U}_C` → U_C, `\mathrm{k\Omega}` → kΩ). |
| `refs` | Resolves `ex:`, `mc:`, `topic:`, `exam:` and `src:` against a course ID index. HTML: `<a class="sk-ref sk-ref-{scheme}">` with route URLs (`mc:<id>` → `/c/<c>/mc/<topic>/#<id>`, `src:` → `/c/<c>/src/<doc>.pdf#page=<n>`). Typst: a link when the target is in the same document (an exercise or exam task, a question, a summary chapter for `topic:`), otherwise the text plus „(→ Übung: Titel)“, or the text alone when it is the target's title. `http(s)` and `mailto` links pass; bare URLs and links with attributes are SK-REF-LINK, other targets SK-REF-SCHEME. With `-M sk-scope=file` (`lint` and `validate --quick`) targets missing from the index are not reported. |
| `meta` | HTML: appends `<script type="application/json" id="sk-meta">` with headings (level, id, text) and items: the file's own index entry, then each MC question, as `{id, kind, topic, difficulty}` (MC items add `type`; difficulty is null when the index has none). |
| `i18n` | Labels in German and English (Hinweis, Lösung, Aufgabe, Punkte …). |
| `solutions` | Typst `-M sk-solutions=inline\|appendix\|none` (default appendix; in an assembled document each part sets its own mode for hints and for solutions, and MC keys follow the solution's): hints, solutions and MC keys stay in place, move into an appendix, or are dropped. The appendix has up to three sections: „Hinweise“ (one entry per exercise with all its hints), „Lösungen“ (each solution with the results generated for it) and „Lösungsschlüssel“ (§2.6); each entry links back to its item. |
| `document` | Typst with `sk-doc` only: an assembled PDF document (§3.3). Its top level holds generated blocks (headings, `sk-gen` JSON for the document info, exam cover and plan, `sk-meta`, `sk-objectives`, `sk-rubric`, `sk-answers`, `sk-unit`), and each course file sits in a `:::::: {.sk-part file= lines= first=}` that is checked and rendered as that file, so a finding names the course file and its own line. The cheat sheet ends with `<cs-end>`, which the fit measures. |

### 3.2 Website: Astro 7.4.2 static, pandoc loader, custom elements, plain CSS

**Packages** (exact pins; `pnpm-lock.yaml` committed; `"packageManager": "pnpm@11.22.0"`; `site/pnpm-workspace.yaml` sets `minimumReleaseAge: 10080`):

| Kind | Packages |
|---|---|
| dependencies | `astro 7.4.2`, `katex 0.16.47`, `yaml 2.9.1` (the version Astro's YAML loader uses for `course.yaml` and `plan.yaml`, and Vite's optional peer; `lib/pdf.ts` imports it to read `sources/manifest.yaml`) |
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
  6. It stores `{id: '<course>/<rel>', data, rendered: {html, metadata: {headings}}}`, with the bridge digest behind a stamp of the loader version, the KaTeX version and a hash of the loader's own sources (`loaders/pandoc.ts`, `lib/katex.ts`, `lib/html.ts`, `lib/findings.ts`), so a change to any of them re-renders everything.
  7. In dev the watcher re-syncs a course 150 ms after one of its `.md`/`.yaml` files changes (all courses when its `course.yaml` is gone); only files whose digest changed re-render, all of them when the index changed. Changes under `_build`, `_history`, `state`, `progress`, `checks`, `sources` and `analysis` are ignored.
- `plans`: `glob()` over `*/plan.yaml`. `progress/mastery.json` (`studykit progress report`, §2.11) is not a collection: `lib/courses.ts` reads it per course with `readJson` (in dev on every render), so a course without one adds no warning.
- **Errors:** a document's findings (filter, schema, KaTeX in the body or a label) become a red error card at its top with `file:line:col`, the code and the message. With `STUDYKIT_STRICT=1` the load throws instead, and a courses directory without a course fails the build.

**Quarantined items** (§2.10) never reach the site; the loader only sees what the render
bridge returns. The bridge reads the ids from the index (`quarantined`) and skips their
exercise and exam-task files (listed under `skipped`), the filter drops their MC questions
(so they are in no bank page, `mc/<topic>.json`, `sk-meta` item list or exam) and turns
links to them into plain text, and each exam's data loses their tasks and points, its pass
mark keeping its share (`verify.exam_without`). Lists, quizzes, counts and the shell's
course info therefore never see them. The index is part of every digest, so a change in
quarantine re-renders the course on the next sync; the dev watcher ignores `state/`, so in
`just dev` that is the next edit of a course file or a restart.

**Figures** are swapped in when the page renders. `lib/figures.ts` replaces each `data-slug` placeholder with the current `_build/figures/<slug>.web.svg` from the figure manifest, so the content cache can never serve a stale figure. Colours are `var(--fig-*)`, so the theme toggle also switches figures to dark mode. A missing figure is an error card in dev and fails a strict build.

**Routes** (UI in English; `<html lang>` set to the course language; page routes end in `/`):

| Route | Purpose |
|---|---|
| `/` | Course cards: exam countdown, mastery ring (the build-time mastery below until this browser has answers), number of MC reviews due today, next session |
| `/c/<c>/` | **Overview tab** (§2.12) with a compact Today panel on top: exam countdown and format, next session, MC reviews due, the 3 weakest topics; topic chips with weight, focus and skip |
| `/c/<c>/plan/` | Week timeline, session checkboxes, "behind schedule" banner suggesting `/regenerate <c> plan` |
| `/c/<c>/summary/`, `…/<topic>/` | Chapter list in teaching order; reading view (max 70ch, sticky table of contents), objectives, `src:` links, "Test yourself" quiz |
| `/c/<c>/exercises/`, `…/<id>/` | Filters for topic, difficulty and status; hint ladder; answer check; solution; self-grade |
| `/c/<c>/mc/` | **MC hub:** accuracy and due count per topic bank; modes Practice, Test, Mistakes, Due, Mixed |
| `/c/<c>/mc/<topic>/` | Every question of the bank in source order with its id as anchor (the target of `mc:` links), plus a practice quiz over the bank |
| `/c/<c>/mc/<topic>.json` | Static endpoint `{topic, title, questions: [{id, type, difficulty, topic, h, html}]}` with pre-rendered question HTML, loaded by `<sk-quiz>` |
| `/c/<c>/cheatsheet/` | Web view in CSS columns, plus a "PDF · size" link and a badge with the page count of the built PDF against the manifest's `max_pages` (`min(3, course.cheatsheet.max_pages, frontmatter max_pages)`): "n / max pages", with "· over the limit" when exceeded, and the density's font size as its tooltip; "PDF not built yet · limit max pages" without a manifest entry |
| `/c/<c>/exams/`, `…/<id>/` | Mock exam list; exam mode |
| `/c/<c>/progress/` | Mastery ring, topic bars, reviews due, misconceptions, sure/unsure calibration, exam history, export and import (the export is what `/import-progress` reads); the last mastery report's value when `mastery.json` exists |
| `/search/` | Pagefind search (§3.5) |
| `/404.html` | Not found |
| `/c/<c>/pdf/<file>` | Static endpoint serving `_build/pdf/<file>` byte for byte, inline as `application/pdf`, for every document in `_build/pdf/manifest.json` (`lib/pdf.ts`). A document that is not built, or whose entry or file is broken (a build warning), has no route and no link. Local only; `dist` is gitignored. |
| `/c/<c>/src/<doc>.pdf` | The lecture PDF `sources/raw/<file>` of each document in `sources/manifest.yaml` (`documents` or `docs`, a list or a mapping; the file is the entry's `file` or `path` inside `sources/raw/`, else `<id>.pdf`), served the same way; `src:` links open it at `#page=<n>`. A link to a document the site does not serve, under `/src/` or `/pdf/`, is a `check-links` warning (an error with `--strict-documents`). |

**PDF links** (`components/PdfLink.astro`, `PdfLinks.astro`). Each link reads "PDF · 14 pages · 353 kB" with the manifest's page count and size (SI units), downloads as `<course>-<file>`, is English UI text kept out of Pagefind, and is hidden in print; a page whose documents are not built shows no link. Overview and summary list ("PDF"), each chapter ("Summary PDF", the whole summary), exercise list ("PDF with solutions", "PDF without solutions"), MC hub ("PDF with answer key"), plan ("PDF") and cheat sheet (the size only; the badge has the pages) link their PDF. The exam list links "Exam PDF" and puts the solutions PDF in a collapsed "Solutions PDF, for after the exam" section, which `elements/dashboard.ts` hides while that exam runs (`[data-sk-exam-locked]`: started, not submitted, time left); on the exam page `<sk-exam>` shows the solutions link only after submitting or time-up and hides it again on a retake. In dev both manifests are re-read on every render, so PDFs built while the server runs appear without a restart. The frontmatter sources of chapters and exercises link to `/c/<c>/src/<doc>.pdf#page=<first page>` when the site serves that document.

**Shell.** `layouts/Base.astro` renders `<body data-course data-exam-date data-mc-scoring
data-negative-marking>` (the course's exam rule), the header with search and theme toggle,
the course tabs, and the course info as `<script type="application/json"
data-sk-course-data="<course>">` (`components/CourseData.astro`). Pages render the progress
figures as empty placeholders (`[data-sk-due-count]`, `[data-sk-accuracy]`,
`[data-sk-weakest]`, `[data-sk-mastery]`, `[data-sk-exam-best]`, `[data-sk-exam-locked]`, `[data-sk-status]`,
`[data-next-session]`); `elements/dashboard.ts` fills them from the store with `lib/stats.ts`
and refreshes them when progress changes on the page or in another tab, and when the page
comes back from the back/forward cache. `scripts/site.ts` holds the shell's small
enhancements (search shortcut `/`, countdowns, plan day marks, list filters, table-of-contents
spy, the current tab scrolled into view, `<details>` opened for printing); it never touches
progress. Without JavaScript the content stays readable (hints and solutions are plain
`<details>`); quizzes, answer checks and progress need it.

**Build-time mastery.** `MasteryRing.astro` renders the overall mastery of
`progress/mastery.json` (its `overall`, else the mean of `topics.<id>.mastery`;
`overallMastery` in `lib/courses.ts`) into `data-value`, so the examiner's results and an
imported export show before the browser has answers. `dashboard.ts` keeps that value and
replaces it with the mastery of this browser's answers as soon as there are any; without
either the ring shows "—".

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
- `print.css`: A4 `@page`, light colours, no site chrome, no page breaks inside boxes, figures, questions, tables and formulas, a question's label kept with its question. The cheat sheet prints as two columns of `<main>` with the title spanning them. `.no-print` hides the summary's "On this page" box, the "Test yourself" quiz and the MC topic practice card; the elements' controls (`elements.css`) and the exam's Start/Retake buttons and alerts are hidden too, and so are the PDF links. `scripts/site.ts` opens every `<details>` on `beforeprint` and restores them after.
- Colour is never the only signal; feedback uses `aria-live`; `prefers-reduced-motion` is respected.

### 3.3 PDF: pandoc 3.13 → Typst 0.15.1, in two explicit steps

`studykit pdf [course] [doc …] [--force] [--no-figures] [--jobs n] [--json]`
(`src/studykit/pdf.py`) builds the documents of one course, or of every course when none
is given (`just pdf`; `just build` runs it before the site). It first builds the course's
figures (cached; `--no-figures` skips that), then the documents in a thread pool (`--jobs`,
default the CPU count). Typst reads files only below `--root`, the repository, so a course
outside it cannot be built. The site reads the result through `_build/pdf/manifest.json`
(§3.2).

**Steps per document.**
1. Assemble `_build/typ/<doc>.md` (`Assembler` in `pdf.py`):
   - Each course file's body, frontmatter stripped, goes into a part
     `:::::: {.sk-part file=… lines=… first=…}` in course order, so the filter checks and
     renders it as that file and reports findings at the course file and its own line
     (`lib/document.lua`, §3.1).
   - Generated blocks around the parts: headings and numbers, the document info, the exam
     cover and the plan as `sk-gen` JSON, and meta lines, objectives, rubrics and answer
     labels as plain text with inline math. Generated text is escaped, so a title is never
     read as Markdown.
2. `pandoc -d common -d typst -M sk-doc=<kind> -M sk-solutions=<mode> --log _build/logs/<doc>.json`
   (through `studykit.pandoc`) writes `_build/typ/<doc>.typ`.
3. `typst compile --root <repo> --ignore-system-fonts --diagnostic-format short` into
   `_build/pdf/.<doc>.partial.pdf`, which replaces `<doc>.pdf` only when the document
   succeeded. The cheat sheet adds `--input density=<n>` (fit, below).
   - Only Typst's embedded fonts are used (New Computer Modern, New Computer Modern Math,
     DejaVu Sans Mono), so no fonts are vendored and page counts are the same on every
     machine.
   - Every Typst `warning:` line and every warning in the pandoc log fails the document.
4. The page count is `len(pypdfium2.PdfDocument(pdf))`; it goes into the manifest.

**Determinism.** Typst runs with `SOURCE_DATE_EPOCH=0` and without the caller's `TYPST_*`
environment variables (no fonts or packages from the machine); the house library sets no
document date; the toolchain is pinned exactly (§4.1). A forced rebuild writes the same
bytes.

**Cache.** A document is rebuilt only when the digest of its inputs changed, or with
`--force`: the pandoc and Typst versions, the `pandoc/` and `typst/` trees and studykit's
Python sources (figures excluded), `_build/index.json`, the kind, the solution mode, the
cheat sheet's limit, the assembled Markdown and the SVG of every figure it shows. A
successful build stores the digest in `_build/typ/<doc>.digest` (the cheat sheet's density
on a second line, so a cached run still reports it).

**Quarantine.** Quarantined items (§2.10) are left out of every PDF: the assembler skips
their exercises in `exercises.pdf` and `exercises-blank.pdf`, an exam's PDFs lose their
tasks and MC questions with their points (the cover's points, pass mark and points table
follow `verify.exam_without`, §3.2), the filter drops their questions from `mc.pdf` and the
exams, whose question counts leave them out, and links to them become plain text.
`_build/index.json`, which lists them, is part of every document's digest, so quarantining
or releasing an item rebuilds the documents.

**Failure.** A document fails on a filter finding, a pandoc or Typst error or warning,
course files that do not assemble into it (a missing exam task file), or a cheat sheet over
its limit. Its errors are printed, its previous PDF stays on disk, and it leaves the
manifest. A figure that fails to build is a note; a document that shows it then fails to
compile. The exit code is 1 when a document failed, 2 for a document id the course does
not have. `--json` prints `{course, manifest, docs: [<manifest entry> + status
(built|cached|failed), errors, overflow?], notes}`, a list of these without a course.

**Manifest** (`_build/pdf/manifest.json`, the contract with the site, `lib/pdf.ts`):

```json
{"schema": "studykit-pdf/1", "course": "<course id>", "docs": [
  {"id": "overview", "kind": "overview", "file": "overview.pdf", "title": "Überblick", "pages": 2, "bytes": 67239},
  {"id": "<exam>", "kind": "exam", "file": "<exam>.pdf", "exam": "<exam id>", "title": "…", "pages": 7, "bytes": 150378},
  {"id": "cheatsheet", "kind": "cheatsheet", "file": "cheatsheet.pdf", "title": "…", "pages": 1, "bytes": 73511, "max_pages": 2, "density": 0}]}
```

- Kinds: `overview`, `summary`, `exercises`, `exercises-blank`, `mc`, `exam`,
  `exam-solutions` (both with `exam`), `cheatsheet` (with `max_pages` and `density`) and
  `plan`. Entries come in that order, exams sorted by id, each exam before its solutions.
- `pages` is the pypdfium2 page count, `bytes` the file size.
- It lists what this run built or found up to date. A document that is not built (its
  sources do not exist, or `cheatsheet.allowed` is false) is absent; one that fails leaves
  it; one whose sources are gone leaves it and its PDF is deleted. When only some
  documents are built (`doc …`, or validate with `--paths`), the others keep their entries
  while their PDFs exist.
- The site checks every entry (schema, course, kind, a plain `.pdf` file name that
  exists, a page count, the exam id) and serves only those that pass.

**Documents per course** (text in `course.lang`; „…“ below is German):

| File | Contents |
|---|---|
| `overview.pdf` | The overview (§2.12) |
| `summary.pdf` | Contents, the overview as the first chapter, then one chapter per topic in teaching order, each on a new page with its sources and objectives |
| `exercises.pdf` | Contents; the exercises grouped by topic, numbered n.m, sorted by difficulty and title, each with difficulty, minutes and kind; appendices „Hinweise“ (all hints of an exercise in one entry) and „Lösungen“ (with the results from `answers`), each entry linked back to its exercise |
| `exercises-blank.pdf` | The same exercises without hints, solutions and results |
| `mc.pdf` | The banks in topic order with their question counts; questions as in §2.6, the appendix „Lösungsschlüssel“ with the key table and every question's key, `why`s and explanation |
| `<exam>.pdf` | Cover (name and Matrikelnummer fields; date, time, points and pass mark, aids; notes, with the MC scoring and negative-marking rule when there is an MC part; points table with an empty column for the result), each task on a new page with its points, the MC part; no hints or solutions |
| `<exam>-solutions.pdf` | „<title> – Lösungen“: each task with its solution, rubric table and results; the MC part with each key inline |
| `cheatsheet.pdf` | Two columns, set at the fitted density; its lines use `top-edge: "bounds"` so tall inline math keeps clear of the line above |
| `plan.pdf` | Exam date, number of sessions and hours, the plan's date, then the sessions by week (§2.9) |

Footers: exams, their solutions and the cheat sheet carry „Seite x von y“, the other
documents course · title and the page number. Hyphenation follows `set text(lang:
course.lang)`.

**Cheat-sheet fit** (`studykit cheatsheet fit <c> [--force] [--no-figures] [--json]`,
`src/studykit/cheatsheet.py`). `studykit pdf` builds `cheatsheet.pdf` through the same fit.
The limit is `max = min(3, course.cheatsheet.max_pages, frontmatter max_pages)`.
1. Compile at densities 0–4 (9, 8.5, 8, 7.5, then 7 pt as the floor, with tighter leading,
   spacing, margins and column gutter) and keep the first with at most `max` pages; the
   manifest records that density.
2. If 7 pt still overflows, `typst eval` over `_build/typ/cheatsheet.typ` reads the page
   geometry (`<cs-page>`), where `<cs-end>` sits and where each `##` heading starts. Exit
   code 3 with JSON such as `{"overflow_pages":0.42,"largest_sections":[{"title","line","height_pages"}…],"pages":2,"max_pages":1,"density":4,"used_pages":1.42,"kept":"…/cheatsheet.pdf"}`
   (plus `course`, `file`, `status`, `fits`); `line` is the heading's line in
   `cheatsheet.md`. A section's height runs from its heading to the next in the column flow,
   so it is an estimate. The cheat sheet leaves the manifest and the previous valid PDF stays
   in place. Exit code 0 means it fits, 1 that it did not build, 2 that the course has no
   cheat sheet.
3. The `author` agent's `authoring/parts/cheatsheet.md` procedure (§5.2) then condenses,
   in this order: derivations and intermediate steps, duplicate examples and formulas,
   prose (to keywords, merged boxes), and only then content of the lowest-priority topics
   (lowest weight first, among those the highest mastery from `progress/mastery.json`),
   starting with the largest sections the JSON names and cutting about 20 % more than
   `overflow_pages`. It rebuilds after each round, for at most 3 rounds; if the sheet still
   overflows it returns `fits: false` with the candidates to drop, so the user decides.
4. More than 3 pages is never allowed (the schema caps both settings at 3).

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
  version only, so this cache never holds system fonts), `STUDYKIT_LOCALE` from
  `course.lang` and `STUDYKIT_DECIMAL` (`comma` or `point`) from `analysis/notation.yaml`'s
  `decimal`, else a comma for German courses; both are part of each figure's cache key.
  The runner builds the font cache once before the children start in parallel.
- With `locale='de'`: "U in V" axis labels; with a decimal comma: a house decimal-comma
  formatter for ticks, values and labels.
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
| Python (`uv.lock`) | figure stack from §3.4, plus pydantic 2.14.1, PyYAML 6.0.3, pypdfium2 5.14.0 (PDF page counts and text checks); dev: pytest 9.1.1, ruff 0.17.1 | `exclude-newer = "7 days"` |
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
sample-materials *args:      # examples/sample-materials → its gitignored _build/materials (§5.4)
    uv run --frozen python examples/sample-materials/build.py {{args}}
[positional-arguments]
ingest *args:                # scan | init | extract | add | round2 (§5.4)
    {{sk}} ingest "$@"
[positional-arguments]
pipeline course *flags:      # the pipeline status of /register-new-subject (§5.4); --json
    {{sk}} pipeline status "$@"
figures course="":
    {{sk}} fig build {{course}}
dev: (figures "")            # http://localhost:4321 (strictPort)
    pnpm -C site dev
build course="": (figures course) (validate course) (pdf course)
    STUDYKIT_STRICT=1 pnpm -C site build
    {{sk}} check-links site/dist
pdf course="":               # <course>/_build/pdf with manifest.json (all courses without one)
    {{sk}} pdf {{course}}
cheatsheet course:           # exits 3 with the overflow when even 7 pt is too long
    {{sk}} cheatsheet fit {{course}}
[positional-arguments]
verify course target="all" *flags:   # the ledger (§2.10); flags go to `studykit verify`
    {{sk}} verify "$@"
[positional-arguments]
status course *flags:        # the study status (§2.11); --today, --json
    {{sk}} status "$@"
[positional-arguments]
tutor course *args:          # Claude Code with the tutor agent as main thread (§5.3)
    claude --agent tutor "/tutor $*"
[positional-arguments]
examine course *args:        # [diagnostic|topic <t>|mc|weak|misconceptions|exam <id>|oral]
    claude --agent examiner "/examine $*"
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

`build` runs in this order: figures; `validate`, whose PDF stage already builds the PDFs;
`pdf`, which finds them up to date and fails the recipe if a document failed; the strict
site build, which copies every PDF its manifest lists into `site/dist`; `check-links`. It
sets `STUDYKIT_STRICT=1` itself and builds the whole site (all courses); its `course`
argument picks what figures, validation and PDFs cover. `cheatsheet` is the fit on its own
(exit code 3 with the overflow, §3.3). `verify`, `status`, `ingest` and `pipeline` pass
their arguments to the CLI unchanged (`[positional-arguments]`, so a `--note` with spaces survives). `tutor` and
`examine` need the `claude` CLI: they start Claude Code with the `tutor` or `examiner`
agent as the main thread and its command as the first message (`just tutor get2 rc-filter`
runs `/tutor get2 rc-filter`), so the persona talks with the student directly and the
examiner can ask through AskUserQuestion (§5.2, §5.3).

### 4.3 Validation (`studykit validate [course] [--paths …] [--quick] [--release] [--json]`)

Every finding has the form `path:line:col SK-CODE message (fix: …)`. A code is the stage family from the table plus a rule (`SK-MCQ-COUNT`, `SK-YAML-ESCAPE`); warnings keep the shape and start the message with `warning:`. Each code is documented in `content-format/errors.md` with a fix recipe and the pipeline step that owns it. Stages run in the order of the table. `--quick` runs Structure, Schema, Fences, MC, Math and the Pandoc backstop (with `sk-scope=file`), for one file in about 1 s; `studykit lint` is `--quick` restricted to the given files and is what the hook runs. `--release` adds Site and Coverage. `--paths` takes files or directories, relative to the working directory or to the course (`--paths mc/rc-filter.md`); a path that is no file of the course is a usage error (exit 2). A stage whose tools are not there yet is skipped with an `info:` note.

| Stage | Checks | Code |
|---|---|---|
| Structure | required files (`overview.md`, `plan.yaml` and an allowed `cheatsheet.md` are warnings until `--release`), known file paths, ID patterns and file names, unique and non-retired IDs, acyclic prerequisites, topics ⊆ course topics, the six overview sections, exam points add up, a ready course without the placeholder topic `draft` | SK-STRUCT |
| Schema | pydantic validation of YAML and frontmatter (the ingest files too); scalar-style lint; control characters; label and rubric fields are text plus inline math only; the exam profile's shares add up to 1 | SK-SCHEMA, SK-YAML |
| Fences | line scan outside code: exact fence forms, allowed placement, depth, blank lines, hint and solution count, code languages; `\|` on pipe-table rows; line-end hyphens (warning) | SK-BLOCK |
| MC | option counts per type, `[x]` invariants, a `why` on every option, one explanation, `pin-last` rule, no "all of the above", no option letters, bank-bias warnings | SK-MCQ |
| Math | denylist and environment allowlist; KaTeX strict via `check-math.mjs` (skipped with a note without `site/node_modules`); inline and display form; block markers; space commands between digits; hint-leak warning | SK-MATH |
| References | `ex: mc: topic: exam: src: fig:` targets, plan refs, exam task files and MC file, `modeled_on` and frontmatter source documents, archetypes, `src:` pages; chunk notes against `sources/chunks.yaml` and the chunk plan against the manifest, the profile's exams and topics | SK-REF |
| Pandoc | the Lua filter set with the json target, on files the stages above left without errors; also with `--quick`, then at file scope (targets missing from the index are not reported). The filter reports family-plus-rule codes: the code validate uses for a rule both check (e.g. SK-REF-FIGURE), and SK-BLOCK-RAW, SK-BLOCK-MARKDOWN, SK-REF-LINK and SK-MATH-TYPST for rules only it checks; a failure without a finding is SK-PANDOC-FAIL | SK-* |
| Figures | build (cached) plus SVG validation; unreferenced scripts (warning) | SK-FIG |
| Verification | reads the ledger (§2.10) and runs no checks (`studykit verify` does): a broken entry (SK-VER-LEDGER, error), a disputed item (SK-VER-DISPUTED, warning, error with `--release`), quarantined and stale items (SK-VER-QUARANTINED, SK-VER-STALE, warnings), and on a whole course (not with `--paths`) ledgers and check files of unknown ids (SK-VER-ORPHAN, warning; `<id>.<tag>.*` and `sum-*` are not orphans); with `--release` every unverified item (SK-VER-UNVERIFIED) and every numeric MC question without `checks/<id>.py` (SK-VER-CHECK), both warnings. The note counts verified, disputed, quarantined and stale items | SK-VER |
| PDF | every full validate, not `--quick` or `lint`: builds the course's PDFs into `_build/pdf` as `studykit pdf` does, manifest included, but without building figures (the Figures stage did); cached, so only documents whose inputs changed rebuild; with `--paths` only the documents made from those files. Every document compiles with no Typst or pandoc warning, and the cheat sheet fits its limit; a filter finding in a document keeps its own code; the note reports how many PDFs are ready and the cheat sheet's pages and density. A Typst diagnostic is reported at the file and line of the course item (exercise, question, task, chapter) it points into, else at the file that defines the document, else `course.yaml`; an overflow at the cheat sheet's `max_pages`. Skipped with a note when PDF building is turned off (`Config.pdf`, for tests), pandoc or typst is missing, the course is outside the repository, or an earlier stage found errors | SK-PDF-COMPILE, SK-PDF-WARNING, SK-PDF-CHEATSHEET, SK-PDF-BUILD |
| Site | `--release` only, for whole courses (not with `--paths`), and only when the stages above found no errors: strict `astro build` into a temporary `--outDir` with `STUDYKIT_COURSES_DIR` set to a temporary directory that holds one symlink to the course; Pagefind with `--force-language`; `pnpm -C site check` without `STUDYKIT_STRICT`; `check-links` over the course's own pages, reported as `dist/<page>` | SK-SITE |
| Coverage | `--release` only: the overview links every topic; each topic has a summary, at least `targets.exercises_per_topic` (4 with `auto`) exercises over two or more difficulties, and at least `targets.mc_per_topic` MC questions (with `auto`: 10–25 by weight); a bank lacking a type the exam uses (warning: a type with a share in the profile's `mc.type_mix`, else every type, limited to `course.exam.mc.types`); at least `targets.mock_exams` mock exams, each within ±10% of the points and time in `course.yaml: exam` | SK-COV |

Three families are not stages: `studykit progress` reports SK-PROGRESS (an export, the merged
state or an examiner result that does not validate), `studykit plan` SK-PLAN (§2.9,
§2.11) and `studykit ingest scan|init|add` SK-INGEST (§5.4: a folder without PDFs, office
files and images, duplicates, unreadable PDFs, a draft `course.yaml` that would not
validate); each writes nothing while one is an error. The lint hook (`studykit lint --hook`,
§5.1) shows errors and warnings of the quick stages on every Write or Edit of a course file.

### 4.4 Tests

`just test` runs the first five suites; CI runs the browser suites after it (§4.5).

- **pytest** (`tests/py/`):
  - control margins compared with `scipy.signal` and closed forms; repeated roots, poles
    and right-half-plane counts of the control templates
  - every figure template renders and validates, with a `facts.json` snapshot (never SVG bytes); the palette, its readable text colours and the site's figure tokens agree
  - lint fixtures (`tests/fixtures/bad/<SK-CODE>/`): each forbidden construct produces its code and its replacement hint; every emitted code is documented in `errors.md`, and every documented code is emitted
  - the filter set over `tests/fixtures/pandoc/` and the golden `blocks.md` and `mcq.md` corpora through html5, typst (compiled) and json; assembled PDF documents (metadata, appendix placement, findings at the course file and line, unknown generated blocks), `\qquad` formula rows and link text that is its target's title
  - YAML loading, the schemas, validate's stages, the render bridge, the Site stage, `check-links`, `doctor` and `tools`
  - `studykit pdf` on the sample course (`test_pdf.py`): every document builds without warnings, the manifest follows the contract with pypdfium2 page counts, a second run is cached, generated text is escaped, `mc.pdf` has an answer key for every question in the order validate and the site use, the exam has „Seite x von y“ and its points table but no solutions, the solutions PDF has every rubric, `exercises.pdf` has every solution and the blank sheet none, a failed compile keeps the previous PDF and leaves the manifest, a filter finding names the course file and line, unknown documents are refused, no course builds every course; `cheatsheet fit` (`test_cheatsheet.py`: the limit, the density loop, positions through the columns, the overflow JSON with section lines, exit code 3 keeping the previous PDF, the 3-page failure); validate's PDF stage (`test_validate_pdf.py`: built once and reused, `--paths`, the overflow at `max_pages`, a missing figure at the file that shows it, the skip reasons, where problems are reported)
  - *(planned)* key points of function plots (`cos x = x`, touching roots, poles) beyond the
    gallery snapshot
  - the ingest side (`test_ingest.py`, `test_pipeline.py`) on material generated at test
    time (`tests/py/materials.py`: hand-written text PDFs, a Pillow "scan" without a text
    layer, a duplicate, a `.pptx`, a photo): kinds from file name, cover and page shape,
    document ids, chunk ranges, the inventory leaves the folder untouched, init writes a
    manifest and a draft `course.yaml` that validate and is idempotent, extract's page text,
    flags and chunk plan (kept on a second run), add copies only what is new or changed
    and replans a changed document, round 2, the validate checks of notes and the exam
    profile; `pipeline status` reports the right resume point for a course at each step
    (an interrupted reading wave, changed material, a damaged extract, the core scope)
    and on a copy of the sample course, and `pipeline report` proves step 14 until the
    content changes; `examples/sample-materials` builds and scans as expected (kinds
    from the file names, the circuit slides and the scan as visual pages, the exam date on
    the last slide)
  - verification on copies of the sample course: `calc` (exact, complex, units, a parser
    that rejects Python), blind views without keys, solutions or marks (`test_blind.py`),
    the runner and ledger (`test_verify.py`: a correct item verifies, a seeded wrong number
    and a seeded wrong MC key are disputed, `mc_numeric`'s four assertions, an edit makes the
    entry stale, two failed fix rounds quarantine, second methods, check failures), the
    Verification stage (`test_validate_verify.py`), quarantine on the render bridge and in
    `exercises.pdf`, `mc.pdf` and the exam (`test_quarantine.py`), and both hooks on sample
    hook events (`test_hook.py`)
  - the student's side: `progress import|log|report` (`test_progress.py`: the merge, the
    Leitner steps and the `lib/stats.ts` figures against the site's own TypeScript on
    `tests/fixtures/progress/`, local days, refused exports, the examiner log's MC scoring
    and all-or-nothing batches, `mastery.json`), the scheduler (`test_plan.py`: the sample
    course, budget and weekday constraints for any budget, spaced repeats, mock exams,
    focus, skip, an unknown exam date, replanning that keeps done sessions and goals, weak
    topics first, quarantined items left out, the written plan passes validate) and
    `status` (`test_status.py`: the same figures as the report)
  - the Claude Code layer (`test_claude.py`): the skills and agents of §5.2 and §5.3 exist
    with valid frontmatter (internal skills hidden and under 500 lines, user commands only
    when typed, the agents' model, effort, turns, tools and preloaded skills, only the
    verifier with a hook); every file, repository path, `studykit` command and flag, `just`
    recipe and SK code that a skill or an agent names exists (in `CLAUDE.md` too: paths,
    commands and recipes), and each command's `allowed-tools` cover the shell commands it
    writes out; the check-script
    recipes run and pass the verifier guard; every content-format template passes lint in a
    copy of the sample course, and the ingest templates (notes, both exam profiles,
    notation) validate in a draft course; `/register-new-subject` has the steps 0–14 of
    `pipeline status` in order, with a gate on each step's status from step 2 on, and asks rounds 1 and 2 as §5.4
    says; both ingest commands cap agents at 6, read `pipeline status`, judge by files and never
    touch the user's folder; `/add-material` quotes the rebuild dependencies of §5.4
    verbatim; `settings.json` has the attribution, permissions and hooks
    of §5.1, and the hook commands run as Claude Code runs them (the lint hook catches a
    broken fence from any directory, pre-git denies a forced add, the guard keeps the
    verifier blind)
- **node --test** (`site/tests/unit/`): the PDF and source manifests the site reads (`lib/pdf.ts`, with small test PDFs from `make-pdf.mjs`), scoring for every type and mode, shuffle determinism with `pin-last` (against values printed by Python), Leitner and the exam clamp, store migration and merge, the answer check (`lib/answer.ts`), the progress figures (`lib/stats.ts`), and text colour pairs of `tokens.css` at 4.5:1 or more in both themes.
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
  - `pdf`: the pipeline built every sample-course document; `dist` holds exactly the manifest's PDFs, byte for byte and served inline; each page links its PDF with the manifest's page count and size, pages without one link none; the solutions PDF is collapsed on the exam index, hidden there and on the exam page while the exam runs, and shown after submitting; the cheat-sheet badge reads the manifest; downloads keep the course name; printing hides the links; source documents are served byte for byte as `sources/manifest.yaml` lists them; search never returns a PDF

Both Playwright configs stop their web server on SIGTERM as well as SIGINT.

### 4.5 GitHub Actions

- **`ci.yml`** (push, PR, and a weekly scheduled run) on `ubuntu-24.04`, with every action pinned by commit SHA:
  1. checkout, `setup-uv` (uv 0.11.30), `pnpm/action-setup` (pnpm 11.22.0), `setup-node` (Node 24.17.0, pnpm cache), and a cache of the pinned tool downloads keyed by `toolchain.toml`
  2. `uv run --frozen studykit tools install`, which fetches the pinned pandoc, typst and just binaries by hash; later steps call `.tools/bin/just`
  3. `just setup`, `just lint-code`, then `playwright install --with-deps chromium`
  4. `just ci`, whose `build` validates and builds the sample course's PDFs
  5. on every run that is not cancelled: `just pdf sample-course` (cached after `just ci`, a build of its own when `just ci` stopped earlier) and an upload of `examples/sample-course/_build/pdf/` (the PDFs and `manifest.json`) as the artifact `sample-course-pdfs`, kept 14 days
  6. the element harness (`pnpm -C site run test:elements`, if Chromium installed) and `just e2e` (if `just ci` passed); both run even after an earlier failure, so one failure does not hide the other
  7. on failure only: upload `site/dist` and the Playwright reports and results (`site/node_modules/.cache/sk-e2e/`, `sk-elements/results/`), kept 14 days
- **`guard.yml`** (push, PR; full history) runs `bash .github/scripts/guard.sh commits|courses|pdfs`:
  - `commits`: every non-merge commit in the range passes `.githooks/commit-msg` (a Conventional Commit, no `Co-Authored-By`). The range is base..head for a pull request and before..HEAD for a push. When the before commit is missing (a new branch, or a force push), a branch is checked as `origin/<default>..HEAD`; creating the default branch checks its whole history; a rewrite of the default branch fails and has to be checked by hand; a range git cannot list fails the check.
  - `courses`: `git ls-files courses` returns only `courses/README.md`.
  - `pdfs`: no tracked `*.pdf`, in any letter case, outside `tests/fixtures/`.

`commit-msg` rejects a `Co-Authored-By` trailer on every commit; subjects git writes itself
(`Merge …`, `Revert "…"`, `fixup!`, `squash!`, `amend!`) are exempt only from the Conventional
Commit format. `pre-commit` matches the staged paths by pathspec, so file names with non-ASCII
characters or quotes are caught too.

## 5. Claude Code layer

Phase 5 built this layer; Phase 6 added the ingest side. What exists:
- `.claude/settings.json` with attribution, permissions and hooks, and `CLAUDE.md` (§5.1);
- the user commands `/register-new-subject`, `/add-material`, `/regenerate`, `/verify`,
  `/tutor`, `/examine`, `/import-progress` and `/study-status`, and the internal skills
  `ingest`, `content-format`, `authoring`, `figures` and `verify-protocol` (§5.2);
- the agents `ingester`, `exam-analyst`, `author`, `verifier`, `tutor` and `examiner` (§5.3);
- the commands they run: `ls`, `index`, `lint` (and `lint --hook`), `validate`, `fig build`,
  `cheatsheet fit`, `pdf`, `calc`, `blind`, `verify`, `hook verifier-guard|pre-git`,
  `plan`, `progress import|log|report`, `status`, `ingest scan|init|extract|add|round2`
  and `pipeline status|report`, and the recipes `just verify`, `just status`,
  `just tutor`, `just examine`, `just ingest`, `just pipeline` and
  `just sample-materials` (§4.2).

`tests/py/test_claude.py` keeps the layer in line with this section and the CLI (§4.4).

Every procedure finds course files with `studykit ls <c>` and ids with
`studykit index <c> --json` and reads them by explicit path, because Grep and Glob may skip the gitignored `courses/`
(§7 risk 10), and computes every number with `studykit calc` or Python. Skills and agents
call the CLI as `uv run --frozen studykit …`.

### 5.1 Project configuration

**`.claude/settings.json`:**
- `"attribution": {"commit": "", "pr": ""}`. The docs confirm that an empty string hides the
  trailer, and the `commit-msg` hook enforces it anyway.
- `permissions.allow` covers what background subagents need, because their permission
  prompts surface in the main session:
  - `Bash(just *)`, `Bash(uv run --frozen studykit *)`, `Bash(uv run --frozen python courses/*)`
  - `Read(/courses/**)`, `Edit(/courses/**)`: project-relative paths; Claude Code checks
    every tool that writes files against Edit rules, so there is no `Write(…)` rule.
- `permissions.deny`: `Bash(git add -f *)`, `Bash(git add --force *)`. There is no deny on
  `.claude/**`, so Claude can change its own skills and agents.
- A command's `allowed-tools` pre-approves what it runs while it is active: every command
  except `/tutor` and `/examine` has `Bash(uv run --frozen studykit *)`; `/regenerate` and
  `/add-material` add `Bash(date -u *)`, `Bash(mkdir -p *)` and `Bash(cp -p *)` for
  `_history/`, `/register-new-subject` adds `Bash(just *)`, and `/import-progress` adds
  `Bash(ls *)` to find the export.
- **The user's materials folder needs no rule.** It can be anywhere, and a `Read(//…)` rule
  broad enough to cover it would open the whole disk, so there is none. Only
  `studykit ingest scan|init|add` reads the folder (Bash, allowed above); `init` and `add`
  copy the PDFs into `sources/raw/`, and every agent reads those copies under
  `courses/` (`Read(/courses/**)`, `Edit(/courses/**)` for notes, transcriptions and
  `analysis/`). The commands never Read or list the folder themselves. A course outside
  the project (`STUDYKIT_COURSES_DIR`) prompts for its reads and writes, as before.
- **Hooks** (each runs `uv run --frozen --project "${CLAUDE_PROJECT_DIR}" studykit …`, so it
  works from any working directory):
  - `PostToolUse`, matcher `Write|Edit`: `studykit lint --hook` (status message
    "studykit lint"). It reads the event on stdin and lints `tool_input.file_path` when it
    is a `.md`, `.yaml` or `.yml` file of a course (a `course.yaml` above it) under
    `courses/`, `examples/` or `$STUDYKIT_COURSES_DIR`. On errors or warnings it exits 2 with the findings and a
    pointer to `content-format/errors.md` on stderr, so Claude fixes them at once; anything
    else exits 0 without output.
  - `PreToolUse`, matcher `Bash`, with `"if": "Bash(git *)"`: `studykit hook pre-git`
    checks every simple command of the line (`&&`, `;`, `|`, following `git -C <dir>`). It
    denies `git add` or `git stage` with `-f`/`--force` (also inside a flag cluster) or a
    path under `courses/` (pathspecs such as `:/courses` too; `courses/README.md` is
    allowed), and `git commit` with a course path, `--no-verify` or `-n`, or course files
    already staged. It prints the documented deny JSON
    (`hookSpecificOutput.permissionDecision: "deny"` with a reason) and exits 0; input it
    cannot read never blocks.
  - The verifier's guard is a hook of that agent only (§5.3).
- **No `memory:` field on any agent.** Course-specific state lives in `courses/<c>/progress`
  and `state`, and `.claude/agent-memory*/` is gitignored as a safety net.

**`CLAUDE.md`** holds the rules for every session, and `test_claude.py` checks that it
states them:
- hard rules: never commit `courses/` (never `git add -f`), nor PDFs outside
  `tests/fixtures/`; Conventional Commits, one logical change each, no Co-Authored-By or
  other AI attribution; a branch per phase, push and merge only when asked; code, skills,
  agents and UI in English, generated content in `course.lang`;
- how to work: the entry points (`just`, `uv run --frozen studykit`, `pnpm -C site`);
  figures are code; never compute numbers in your head (Python or `studykit calc`); run
  `studykit validate` before finishing; look at the pages after changing how PDFs look;
  find course files with `studykit ls`; exact pins;
- the Claude Code layer: the commands, agents and hooks, the files only the CLI writes
  (`state/verify/`, `progress/`, `plan.yaml` but its goals and notes), the ingest commands
  with who writes which ingest file (the user's folder only through `studykit ingest`),
  and `test_claude.py` after any change to a skill or an agent.

### 5.2 Skills

**User commands** (`disable-model-invocation: true`, so only the user starts them, by
typing them in a Claude Code session in the repository; no forked context, so they run in
the main thread and can use AskUserQuestion and start agents). `just tutor` and
`just examine` open `/tutor` and `/examine` with their agent as the main thread (§4.2).

| Skill | Arguments | Purpose and output |
|---|---|---|
| `/register-new-subject` | `<folder> [course-id]` | Full pipeline (§5.4): inventory, two rounds of questions, ingest, ingesters per chunk and the exam analysis, topic synthesis, the author, figure and verifier waves, mock exams, cheat sheet, plan and publish. Resumes at the first step `studykit pipeline status` does not show as done. Produces `courses/<id>/`, a green `validate --release`, the PDFs, the built site and `state/pipeline/report.md`. |
| `/regenerate` | `<course> <overview\|plan\|summary\|exercises\|mc\|figures\|exams\|cheatsheet\|all> [--topic t] [--add n] [--replace] [note]` | Re-runs one authoring step and everything downstream of it. Copies every content file the run may overwrite (downstream ones too) to `_history/<UTC timestamp>/` and asks before `--replace` or `all`. Without a mode it improves the part in place; `--add n` adds n items, `--replace` rewrites the part. Items that survive keep their ids; removed ids go into `retired_ids`. Authors: one per topic for summary, exercises and mc (at most 6 in parallel), one per mock exam (at most 3), one for the overview or the cheat sheet (then its fit loop); figures and the plan it runs itself. Downstream: the cheat sheet after a summary, `/verify` of the added and changed items, `studykit plan` after exercises or exams, then `validate` (errors routed to the owning author, at most 3 rounds) and `pdf`. Reports what was added, changed and removed, the verification counts, validate, the PDFs and the `_history/` directory. |
| `/add-material` | `<course> <file\|folder>` | Incremental ingest (`ingest add`, ingesters for the new chunks, the exam analysis again when exams changed), a topic-map diff applied after confirmation (old outline, profile and `course.yaml` saved to `_history/`), then the `/regenerate` runs the rebuild dependencies call for, suggested, not run. |
| `/verify` | `<course> [id\|topic\|exam\|all]` | Blind re-verification with the dispute loop (§5.3); ends with `state/verify/report.md`, a validate run and a table of verified, fixed, disputed, quarantined and unverified items with reasons. |
| `/tutor` | `<course> [topic\|ex-id]` | Socratic tutoring persona (below). Writes nothing. |
| `/examine` | `<course> [diagnostic\|topic <t>\|mc\|weak\|misconceptions\|exam <id>\|oral]` | Strict examiner persona (below), `mc` without a mode. Logs every graded item. |
| `/import-progress` | `<course> [file]` | Takes the given browser export, or the newest `~/Downloads/studykit-progress-<course>-*.json`, shown with its date and size and read only after confirmation. Previews with `progress import --dry-run` (SK-PROGRESS findings stop it), imports, runs `progress report` and `status`, and offers a replan when sessions are behind or the weakest topics changed (`studykit plan`, the missing goals, `validate --paths plan.yaml`, `pdf <c> plan`). |
| `/study-status` | `<course>` | `studykit status` unchanged in a code block, then at most four lines: plan adherence, the weakest topic and the reviews due, and one next step (the next session, `/import-progress`, `/examine <c> mc`, `/tutor <c> <topic>`, `/regenerate <c> plan`, or a mock exam in the last three weeks). Read-only. |

**`/tutor`** prepares quietly from `studykit status <c> --json` and
`studykit index <c> --json` (never using a quarantined id), the topic's summary chapter, the exercise with its hints
and solution, the student's misconceptions (`progress/mastery.json`) and the `why` lines
of the topic's MC bank. It takes the given exercise, an unsolved exercise of the given
topic (easy to hard), or offers the weakest topic and that of the next session. It talks
in the student's language, asks one question per message along the exercise's hint ladder
(principle → set-up → key intermediate result), exposes a wrong step with a question
(units, a limit case, a sign, an estimate), gives the exercise's next hint in its own
words after two stuck attempts, and shows the full solution only when the student asks
after trying. Every number, the student's and its own, is checked with `studykit calc`
against the key's tolerance. It closes with what the student can do now, the misconception
that came up and one next step, and logs nothing.

**`/examine`** reads `studykit status <c> --json`, `studykit progress report <c> --json` and
`studykit index <c> --json` (no quarantined ids), picks the items of its mode and reads their keys,
`why`s, explanations, answers and rubrics without showing any of them:

| Mode | Items |
|---|---|
| `diagnostic` | 15 MC questions over the topics not skipped, by weight (at least 2 each), mixed types and difficulties; seeds the Leitner boxes and the plan |
| `topic <t>` | 8 MC questions of the topic, then one unsolved exercise of difficulty 2–3 |
| `mc` | 10 MC questions: due reviews first, then the weakest topics, then unanswered ones |
| `weak` | the 3 weakest topics, 4 MC questions each, then one exercise of the weakest |
| `misconceptions` | every misconception question again, each followed by another one on the same concept |
| `exam <id>` | the mock exam under time: its tasks, then its MC part without feedback; quarantined tasks and questions are left out and the pass mark keeps its share |
| `oral` | 5–8 open questions over the weakest and the focus topics, one follow-up each, judged 0 to 1 in quarters against the summary |

Exercises and exam tasks are graded key by key with `studykit calc`
(`|x − value| ≤ atol + rtol·|value|`, `--units` to convert; a symbolic answer is right
when its difference to the key is exactly 0), exam tasks by their rubric (a criterion's
points, half of them with a stated reason, or none). Every graded item is logged with `studykit progress log`
(`mode`, `kind`, `topic`, `item`, for MC `chosen` in source letters and `conf`, optional
`points` and `max_points`, a `finding` naming the mistake); the command computes an MC
score from `chosen` and refuses one that differs (§2.11). The session closes with
`progress report`, the score per topic, the misconceptions found, the reviews due and one
next step.

**Internal skills** (`user-invocable: false`, each under 500 lines; agents preload them
through `skills:`):

| Skill | Contents |
|---|---|
| `content-format` | The format in brief (layout, ids, YAML rules, frontmatter per kind, the dialect of §2.3), how to find and check files (`ls`, `index`, the lint hook, `validate --paths`), copy-ready `templates/` for every file kind (each passes lint in a copy of the sample course), and the SK codes with a pointer to `errors.md` |
| `authoring` | Shared quality rules for every part, id handling, the finishing steps (look at the figure PNGs, `validate --paths`), the compact result JSON, and the fix round after a dispute (re-derive independently, then `fixed` or `key-correct` with the step the verifier got wrong). `parts/{overview,summary,exercises,mc,exam,cheatsheet,plan}.md` hold each part's procedure; the agent reads the part it needs by path, so not every part is preloaded. `parts/mc.md` holds the misconception catalogue, the type-mix rules, "one concept per stem", options of similar length, and the requirement that every distractor's `why` names its mistake; `parts/cheatsheet.md` the condense loop (§3.3); `parts/plan.md` the goals after `studykit plan`. |
| `figures` | Which template for which figure, how to write `figures/<slug>.py`, the rule "render → look at the PNG → fix" with an overlap, clipping and anchor checklist, and the validator's rules; `reference.md` is the API reference |
| `ingest` | Chunk digest procedure (page text first, `Read(pdf, pages=…)` only for flagged pages, scanned pages transcribed into `sources/text/`), the notes rules and `templates/notes.md`, `exam-analysis.md` (the exam-analyst's procedure) with `templates/exam-profile.yaml`, `exam-profile-no-exams.yaml` and `notation.yaml`, `templates/outline.md` for the synthesis step, and the gates |
| `verify-protocol` | Blindness, the procedure for one item, the two-method rule and the dispute, fix and quarantine loop; `recipes.md` has check scripts that run as written: nodal analysis with a mesh-current second method, phasors, a Laplace step response with a simulated second method, stability margins with brentq, numeric MC with `mc_numeric`, conceptual MC and review |

The persona text for `tutor` and `examiner` lives only in the `/tutor` and `/examine`
skills. A skill with `disable-model-invocation: true` cannot be preloaded, so the agents of
the same name preload nothing: `just tutor` and `just examine` start them with the command
as the first message, and an agent whose first message is something else reads the skill
file by path and follows it.

### 5.3 Agents (`.claude/agents/*.md`)

No agent has the `Agent` tool, so nothing spawns further agents: the commands of §5.2 and
the `just` recipes start them. No agent has memory, and only the verifier has a hook.

| Agent | Model / effort | Tools | Preloaded skills | Writes |
|---|---|---|---|---|
| `ingester` | sonnet / medium, maxTurns 40 | Read, Write, Glob, Bash | ingest, content-format | `sources/notes/<chunk>.md`; transcriptions of scanned pages into `sources/text/` |
| `exam-analyst` | opus / high, maxTurns 50 | Read, Write, Glob, Grep, Bash | ingest | `analysis/exam-profile.yaml` (archetypes, frequencies, points, minutes per point, MC share, types, scoring, negative marking, topic weights, confidence) and `notation.yaml` (j vs. i, ε(t) vs. σ(t), underlined phasors) |
| `author` | opus / high, maxTurns 80 | Read, Write, Edit, Glob, Grep, Bash | content-format, authoring, figures | One part per call: the overview, one topic's summary, exercises or MC bank, a mock exam or the cheat sheet, plus its figure scripts; mode new, `add <n>`, `replace` or `fix <id>`. Never `course.yaml`, `checks/`, `state/`, `progress/`, `_build/`, `_history/` or git. Must end with `studykit validate --paths <own files>` free of errors and return the compact JSON (`{"error": …}` when the assignment is impossible). |
| `verifier` | opus / high, maxTurns 50 | Read, Write, Bash | verify-protocol, content-format | `checks/**` only, one item per call |
| `tutor` | opus | Read, Grep, Glob, Bash | none (§5.2) | nothing, not even through Bash; started via `just tutor` (main thread) |
| `examiner` | opus | Read, Grep, Glob, Bash, AskUserQuestion | none (§5.2) | `progress/examiner.jsonl` only through `studykit progress log`, and the report through `studykit progress report`; started via `just examine` (main thread) |

**Verifier blindness** is enforced by an agent-scoped `PreToolUse` hook in `verifier.md`
(matcher `Read|Write|Edit|MultiEdit|NotebookEdit|Grep|Glob|Bash`),
`studykit hook verifier-guard`:
- It denies Read, Grep and Glob on `exercises/`, `mc/` and `exams/`, and on what else holds
  keys or solutions: `state/`, `_history/`, `_build/` except `blind/` and the figure images,
  figure facts, the built site and `.cache/`; Grep and Glob over a tree that contains a
  course, and Glob patterns or Grep globs that name those paths.
- It denies Bash commands that mention those paths (command substitution included), except
  `studykit` and `python checks/…`; of `studykit` only `blind`, `calc`, `verify` (without
  `--json` and `--show-key`), `ls`, `lint`, `validate`, `fig`, `index` and `doctor` are
  allowed, with or without a path.
- It denies Write, Edit, MultiEdit and NotebookEdit outside a course's `checks/`, and check
  code that names those paths.
- The verifier works only from `studykit blind <c> <id>`, which writes `_build/blind/<id>.md`:
  the statement with no solution, hints, rubric, answer values or `[x]` marks, the answer
  keys to compute (key, label, unit or symbols), and MC options in source order labelled A–F
  without their `why` or the explanation; figures point at their PNG, course links keep
  their text only.

**Verifier protocol** (the `verify-protocol` skill):
1. `studykit blind <c> <id>`, then read the view and the figure PNGs it lists.
2. Compute in Python (`studykit calc` for quick values).
3. Write `checks/<id>.py` (or `checks/<id>.json` for a conceptual MC question), ending
   with one `studykit.check` call.
4. Run `studykit verify <c> <id>`, which compares against the answer key and writes the
   ledger.
5. If it is disputed, confirm with an independent second method (nodal vs. mesh analysis,
   symbolic vs. numeric, closed form vs. simulation) in `checks/<id>.<tag>.py` (an MC
   answer: `checks/<id>.recheck.json`) and `studykit verify <c> <id> --confirm …`. If the
   second method sides with the key, fix the first check and run verify again.
6. Return a compact JSON with the status the verify output showed.

**Dispute loop** (`/verify`, the orchestrator; it may read keys, the verifiers never get one):
1. `studykit verify <c> <target>` re-runs every existing check, then `--status --json`
   picks the items for a verifier: the named item always, otherwise every unverified item
   and every disputed one that no second method confirmed.
2. A verifier wave, at most 6 at a time, whose prompt holds only the course directory and
   the id. The ledger is the truth, not an agent's report; an item without a working check
   gets one more attempt, then stays unverified. The orchestrator compares a `review`
   check's reason with the solution itself and records a disagreement with `--dispute`.
3. Each disputed item goes to an `author` fix round with the verifier's values from
   `--status --show-key --json` and whether a second method confirmed them (at most 6 in
   parallel, never two items of one file). `fixed`: verify runs the same check on the new
   version. `key-correct`: a fresh verifier checks its method with a second one; if both
   still disagree with the key, the user decides with AskUserQuestion between quarantine
   and leaving the item disputed.
4. At most 2 author rounds: the dispute after the second fix round quarantines the item by
   itself; an item still not verified after two rounds is quarantined by hand
   (`--quarantine --note`). Quarantined items are hidden from the site and the PDFs and
   listed in the report.
5. `verify --report`, then `validate`, which rebuilds the PDFs without quarantined items.

**Examiner MC in the terminal** uses AskUserQuestion (1–4 questions of 2–4 choices per
call, headers of at most 12 characters). The options are shuffled and labelled anew (a
`pin-last` option stays last), with math as plain Unicode text:
- single with ≤ 4 options: one question
- multi with ≤ 4 options: `multiSelect`
- Kprim: four true/false questions in one call
- 5 or 6 options: shown as text, answered by letter
- the confidence question joins the same call when there is room, else a second call
  (always for Kprim)

The examiner asks for confidence before revealing anything, logs the answer in source
letters before it reveals the result, never reveals an answer before the user commits, and
grades calculations with the rubric using `studykit calc`.

### 5.4 `/register-new-subject <folder> [course-id]`

`.claude/skills/register-new-subject/SKILL.md` implements the steps below on top of
`studykit ingest` and `studykit pipeline`, with the `ingester` and `exam-analyst` agents
and the `ingest` skill. It reuses what Phase 5 built: the `author` and `verifier` agents,
the dispute loop of `/verify`, `studykit plan`, `validate` and `pdf`. `docs/walkthrough.md`
follows a run on `examples/sample-materials`.

The state is derived from outputs by `studykit pipeline status <course> [--json]`
(manifest hashes plus file presence plus ledger; `studykit status` is the student's status,
§2.11). There is no separate state file. The command reads it at the start and after
every step and continues at `resume.step`, the first step that is not done (deferred steps
aside); a `stale` step is redone, a `done` one never. Success is judged from files and
gates, never from an agent's own report. The orchestrator is the command's main thread: it
asks the user, starts at most 6 agents at a time (3 for mock exams), computes every number
with `studykit calc` and asks only in rounds 1 and 2 unless a step stops. A failed gate's
findings are routed by file and SK code to their owner (the ingester of a chunk, the
exam-analyst, the author of a part, the `/verify` procedure, `studykit plan`, the user, or
the main thread itself; `errors.md` names the owners); a step that fails its gate twice
stops the run with the findings and how to continue, and publish gets 3 rounds.

0. **Preflight:**
   - `just doctor --quick`
   - the course id from the argument, or proposed from the folder name (ä → ae, …) and confirmed; if the course exists, offer to resume it. When the folder changed since the copy (step 2's `todo`: `folder_changed`, `folder_new`), `ingest add` runs before synthesis; after it, that is `/add-material`'s job
   - `studykit ingest scan <folder> --dry-run --json` builds an inventory table: PDFs, pages, text-layer share, visual and scanned pages, the guessed kind (from file name, cover page or page shape; `?` when uncertain), duplicates (sha256), unsupported files (office files and images get "export as PDF"), the language and exam dates found in the text
1. **Ask, round 1** (one AskUserQuestion call with 4 questions, after showing the inventory table):
   - Exam date: the dates found in the materials (with document and page), "Unknown yet", or free text via Other.
   - Exam format: written / written + MC part / MC only / oral.
   - Cheat sheet: not allowed / 1 / 2 / 3 pages.
   - Hours per week.

   A second call covers uncertain document kinds (multi-select "Which of these are past exams or their solutions?", at most four documents per question) and confirms the detected output language.
2. **Scaffold** (Python, `ingest init`): copy the PDFs to `sources/raw` (the user's folder is only read), write `manifest.yaml` with the round-1 answers and a draft `course.yaml`; exam duration and points only when the found exam date's context states them. Gate: the step is done and `validate --paths course.yaml sources/manifest.yaml` has no error.
3. **Extract** (Python, `ingest extract`): pypdfium2 page text into `sources/text`. A page is flagged *visual* if it has fewer than 200 characters, garbled glyphs, large image areas or many drawn shapes, and *scanned* without a text layer. Chunks are at most 20 pages, matching the Read tool's PDF page limit, and never cross a document boundary. Past exams and their solutions are kept whole.
4. **Read** (parallel, at most 6 at a time, the longest chunks first):
   - one `ingester` per chunk in the step's `todo`, reading the text first, calling `Read(pdf, pages=…)` only for flagged pages and transcribing scanned pages to `pNNNN.vision.md`
   - `exam-analyst` runs alongside over all exams and solutions and writes the exam profile and the notation; with no past exams it writes a low-confidence profile from the round-1 answers
   - Gate: the notes schema holds, every chunk has notes at its document's sha256, every scanned page has its transcription, no lint errors in notes or analysis (so formulas pass the math lint)
5. **Synthesize** (main thread):
   - merge the notes' candidate topics into 6–15 topics (fewer only for a very small course) with prerequisites on earlier topics and weights: with a profile of medium or high confidence the profile's `topic_weights` added up over the merged slugs (exam point shares, MC part included), else lecture coverage, computed with `studykit calc` to two decimals summing to 1
   - write `outline.md` from `ingest/templates/outline.md` (topic table, one section per topic with sources, merged slugs, key formulas and archetypes, every chunk id)
   - fill in `course.yaml` topics, title, short, semester and the exam from the profile or the course facts; map the profile's candidate slugs to course topics
   - Gate: the step is done and `validate --paths course.yaml analysis sources` has no error
6. **Ask, round 2:**
   - Show a numbered topic table (weight, sources, past-exam frequency) and the exam as `course.yaml` now has it. The user replies in one line, for example `focus 3,5; skip 9; merge 6+7; ok` (also `weight <n>=<w>` and `exam <minutes> min <points> pts`), repeated until `ok`.
   - An estimate for both scopes (authors, items, opus agent runs, time, each as a range) computed with `studykit calc`.
   - Then AskUserQuestion: number of mock exams (1/2/3, default the number of past exams, at most 3, else 2), scope (full / core first: summary + MC + plan), and go/no-go with the estimate. `ingest round2` records the answers; no-go stops, and the next run resumes here.
7. **Author wave** (at most 6 parallel): first one `author` for `overview.md` (§2.12), then one per topic for the summary, then one per (topic, part) for the MC bank and, unless the scope is core, the exercises, each told to follow `notation.yaml` and the chunk notes `outline.md` lists for its topic (mode `add <n>` when a resumed part falls short). The hook lints every write. Gate: `validate --quick` over the new files and the step's Coverage counts.
8. **Figures:** `just figures <c>` and a look at every new PNG. Failures, and PNGs with problems, go back to the owning author (at most 2 rounds). Then a validate of step 7's files without `--quick` checks the references and figures the quick gate skipped.
9. **Verify wave** (at most 6 parallel): the `/verify` procedure per topic, one `verifier` per item (§5.3: one item per call), with the dispute loop described in §5.3.
10. **Mock exams** (deferred with scope core): `author` with `parts/exam.md` (at most 3 in parallel), including `mc.md` when `exam.mc.present`, then verification. Gate: count, points and time within ±10 %, the MC part, the profile's archetypes, every item verified or quarantined.
11. **Cheat sheet** (deferred with scope core; done when none is allowed): `author` with `parts/cheatsheet.md`, the fit loop (the user picks what to drop after three condense rounds), then a formula audit: every display formula must appear with the same symbols in its topic's summary chapter (the main thread checks it until the verifier's `checks/sum-*.py` audits exist, §2.10). Gate: a fresh `cheatsheet.pdf` within the limit.
12. **Plan:** `studykit plan` (deterministic), then the main thread writes the session goals; SK-PLAN findings go to the user.
13. **Publish:** the overview gets its `exam:` and `ex:` links and each summary chapter the `ex:` links of its topic's exercises (both were written before the exercises and mock exams existed), `just pdf <c>`, `studykit validate <c> --release`, then `status: ready` and `just build <c>` (back to draft if the build fails). Failures are routed by SK-code to the owning agent, for at most 3 rounds. `status` is set to `ready` only when everything is green. With `scope: core` the Coverage stage still asks for the deferred parts, so the course is built as a draft and becomes ready after them.
14. **Report:** `studykit pipeline report <c>` writes `state/pipeline/report.md`, and the command tells the user:
    - counts per part (exercises by difficulty, MC by type, exams, figures)
    - share verified, fixed and quarantined, with reasons
    - cheat-sheet pages and font size
    - what was assumed (exam duration, points, MC rules from a low-confidence profile) and the deferred steps
    - next steps: `just dev` → `http://localhost:4321/c/<id>/`, `/examine <id> diagnostic` (15 MC questions to seed the Leitner boxes and the plan), `/tutor`

**The Python side** (`ingest.py`, `pipeline.py`; every command takes `--json`):

```
studykit ingest scan <folder> [--dry-run] [--kind DOC=KIND …] [--today D]                    # step 0
studykit ingest init <folder> <course-id> --exam-date unknown|YYYY-MM-DD                     # steps 1–2
      --exam-format written|written-mc|mc|oral --cheatsheet 0|1|2|3 --hours-per-week H
      [--lang de|en] [--title T] [--short S] [--semester S] [--exam-minutes N] [--exam-points P]
      [--start D] [--kind DOC=KIND …] [--today D] [--dry-run]
studykit ingest extract <course>                                                              # step 3
studykit ingest round2 <course> --mock-exams 1|2|3 --scope full|core [--no-go] [--today D]    # step 6
studykit ingest add <course> <file|folder> [--kind DOC=KIND …] [--today D] [--dry-run]        # /add-material
studykit pipeline status <course>                                                             # the resume point
studykit pipeline report <course> [--today D]                                                 # step 14
```

- `scan` only reads: per PDF the proposed document id (kebab-case from the file name),
  pages, text-layer share, visual and scanned pages, the kind (`slides`, `script`,
  `exercises`, `solutions`, `exam`, `exam-solutions`, `other`) from the file name, else the
  cover page, else landscape pages (`kind_from`; anything but the file name or the user is
  `uncertain`, the candidates for the second question of round 1), duplicates by sha256,
  office files and images with "export as PDF", and future dates near "Klausur"/"exam"
  for the exam-date question. A page is visual with fewer than 200 characters, 10 % garbled
  glyphs, images over a quarter of the page or 30 drawn shapes (a circuit has 40 to 50);
  scanned with fewer than 20 characters.
- `init` copies each PDF to `sources/raw/<doc>.pdf`, records the round-1 answers in the
  manifest (`answers.round1`; a new course needs all four) and writes a draft `course.yaml`
  (status draft, the exam format and MC part, the cheat-sheet policy, the study budget, one
  placeholder topic `draft`, `targets.mock_exams: 2`); both must validate. On an existing
  course it resumes: it copies what is new, changed or missing and leaves `course.yaml`
  alone. `--kind` records a kind the user decided (`kind_from: user`).
- `extract` writes `sources/text/<doc>/p0001.txt` and `index.json` (per page: characters,
  garbled share, image share, shapes, visual, scanned, the reasons) and `sources/chunks.yaml`:
  chunks `<doc>-cNN` of at most 20 pages, as even as possible, never across documents,
  past exams and their solutions whole, each with its flagged and scanned pages and the
  document's sha256. A document whose text is current is not read again, and its chunks
  keep their ids. The ingester writes `sources/notes/<chunk>.md` (frontmatter `chunk`,
  `doc`, `pages: 'first-last'`, `source_sha256` = the chunk's sha256, `kind`, `title`,
  candidate `topics`, the `visual_pages` it looked at) and its transcription of a scanned
  page as `sources/text/<doc>/p0001.vision.md`.
- `add` is init's copy plus extract for a course that exists: a PDF with a known sha256 is
  skipped (another name: SK-INGEST-DUPLICATE), one with a known origin but new content
  replaces that document (`updated`), so its chunks are planned again and their notes go
  stale. It lists the chunks to read.
- `round2` records `answers.round2` (mock exams, scope, go) and sets
  `targets.mock_exams` in a `course.yaml` that has `ingest init`'s flow form.
- `pipeline status` derives each step's status (`done`, `pending`, `partial`, `stale`),
  its `proof` (the files that show it), `details` and a machine-readable `todo` (chunks
  without notes, topics without summary, items not verified, stale PDFs, …) and returns the
  first step that is not done as `resume`. The proofs: the manifest (0) and its round-1
  answers (1); the manifest, `course.yaml` and the sha256 of every file in `sources/raw/`,
  plus the ingested folder compared by sha256 (2); page texts and chunks at each
  document's sha256 (3); notes matching their chunk for every chunk, a transcription of
  every scanned page, the exam profile and notation, no lint errors in them (4); `sources/outline.md` naming every topic id and
  every chunk id, and topics other than `draft` (5); `answers.round2` with go and the same
  `targets.mock_exams` (6); the Coverage stage for the overview, summaries, exercises and
  MC banks (7); the figure runner's cache keys (8); the ledger of the topics' items (9);
  the mock exams' count, size, MC part, archetypes and ledger (10); a fresh cheat sheet
  within its limit (11); a valid plan for the exam date with every goal (12);
  `status: ready`, fresh PDFs (the digests `studykit pdf` would compute) and the built
  site (13); the report's fingerprint of the current content, ledger and PDF manifest
  (14). With `scope: core` the exercises, mock exams and cheat sheet are deferred.
- `pipeline report` writes `state/pipeline/report.md`: counts per part (exercises by
  difficulty, MC by type, exams, figure scripts), verified, fixed, quarantined and
  disputed items with their reasons, the cheat sheet's pages and font size, and the next
  steps.

**`/add-material <course> <file|folder>`** (`.claude/skills/add-material/SKILL.md`) brings
new or changed PDFs into a course whose step 0 is done:
1. Preview with `ingest add --dry-run` (added, changed, known, skipped with the reason);
   nothing added or changed ends the command; uncertain kinds are asked as in round 1.
2. Copy `course.yaml`, `sources/outline.md` and `analysis/exam-profile.yaml` to
   `_history/<UTC timestamp>/`, then `ingest add`, which copies and extracts and lists the
   chunks to read. Gate: pipeline steps 2 and 3 are done.
3. Ingesters for those chunks and for step 4's `todo`, and the exam-analyst again when an
   exam or its solutions was added or changed (at most 6 agents). Gate: step 4 is done.
4. A topic-map diff (weights before and after, chunks per topic, new archetypes, proposed
   new topics; ids of existing topics never change), applied after one AskUserQuestion:
   apply, apply without new topics, or keep the topics and only extend the outline. Gate:
   step 5 is done and `validate --paths course.yaml analysis sources` has no error.
5. From the rebuild dependencies below, the `/regenerate` runs that bring the content up to
   date, suggested with their reason but not run, and a report with the steps that
   `pipeline status` now shows as stale or partial.

**Rebuild dependencies** used by `/regenerate` and `/add-material`:

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

**Status:** Phases 0–6 are complete; Phase 7 is optional. The few parts of this document
marked *planned* (the summary and cheat-sheet formula audits `checks/sum-*.py`, the mock
exams' archetype-mix and n-gram checks, key points of function plots) do not exist yet.

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
- the verifier catches a seeded wrong number and a seeded wrong MC key (`test_verify.py`,
  on a copy of the sample course)
- the hook catches a broken fence (`test_claude.py` runs the configured lint hook)
- `/regenerate sample-course mc --topic rc-filter --add 3`, `/tutor`, `/examine mc`, `/import-progress` and `/study-status` all work

Commits:
- `feat(verify): add check api, runner and per-item ledger`
- `feat(verify): add blind item views`
- `feat(cli): add sympy calc command`
- `feat(cli): add verifier-guard and pre-git hooks`
- `feat(validate): report the verification ledger in the verification stage`
- `feat(verify): hide quarantined items on the site and in pdfs`
- `feat(claude): add permissions and lint hooks`
- `feat(claude): add content-format, authoring and figures skills`
- `feat(claude): add author agent`
- `feat(claude): add verifier agent with blind guard hook`
- `feat(claude): add verify and regenerate commands`
- `feat(progress): add import, examiner log and mastery report`
- `feat(plan): add deterministic study plan scheduler`
- `feat(cli): add study status command`
- `feat(claude): add tutor and examiner skills and agents`
- `feat(claude): add import-progress and study-status commands`
- `build: add verify, status, tutor and examine recipes`
- `test(claude): lint skill and agent frontmatter and referenced files`

**Phase 6: `/register-new-subject`.** Done when an end-to-end run on `examples/sample-materials`, including the rasterised scan, produces a course with a green `--release`, and an interrupted run resumes correctly.

The run built `opamp-grundlagen` (3 topics, 21 exercises, 37 MC questions, 1 mock exam, a
cheat sheet of 1 of 2 pages, 19 figure scripts) with every item verified and a green
`validate --release`; it ran over several sessions, each resuming at the step
`pipeline status` reported, and `test_pipeline.py` checks the resume point after each step
and after an interrupted reading wave.
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
| 1 | KaTeX (web) and texmath (PDF) disagree on math. This is the only remaining two-engine split. | One written subset; `math.lua` denylist with replacements; KaTeX strict plus `--fail-if-warnings`; lint hook on every write; every full `validate` compiles the course's PDFs with every warning an error (SK-PDF); golden corpus in CI, re-run on every pandoc or Typst bump |
| 2 | The custom pandoc loader is our own code: dev hot reload, speed, error mapping | The loader plus the render bridge (`studykit render`), with digest caching and a thread pool; error cards in dev; `+sourcepos` in lint; e2e tests; fallback is the research's remark path with name-only fences |
| 3 | LLM arithmetic errors, or wrong MC keys and distractors | `studykit calc` and Python for every number; blind verifier enforced by its guard hook (`verifier-guard`) and blind views; check scripts; `mc_numeric` with named mistakes and a separation check; two-method rule; content-hash ledger; quarantine instead of shipping |
| 4 | Pandoc may not detect `[x]` in *loose* task-list items (option paragraph plus `why` paragraph) | Covered by the Phase 1 golden corpus. Fallback: a tight list with the `why` as an indented `::: why`-free sub-list item that `mcq.lua` reads |
| 5 | Cheat sheet over 3 pages, or different page counts on different machines | Embedded Typst fonts only with `--ignore-system-fonts`, no `TYPST_*` environment, `SOURCE_DATE_EPOCH=0`; exact Typst pin; density presets with a 7 pt floor; overflow measured with `typst eval`; SK-PDF-CHEATSHEET in every full `validate`; at most 3 condense rounds by the author, then the user decides; hard failure that keeps the last valid PDF and drops it from the manifest |
| 6 | Figures valid but visually wrong | Templates hide placement; mandatory PNG review; facts JSON is the numeric source; `plot.custom()` is the only raw route |
| 7 | Course material leaks into the public repo | Gitignore; pre-commit hook; Claude `pre-git` hook and deny rules; CI guard; no agent memory; self-written sample course |
| 8 | Toolchain drift (pandoc 3.13 is 3 days old; Typst 0.x breaking changes; Astro 7 Markdown churn) | sha256-pinned binaries shared by local and CI; lockfiles with 7-day cooldowns; `doctor`; Astro's Markdown pipeline not used at all; one-line fallback to pandoc 3.12.1 |
| 9 | Lost browser progress (origin or port change, Safari eviction) or edits invalidating it | Fixed `localhost:4321` with strictPort; `storage.persist()`; export, import and merge; content hashes per item; `/import-progress` merges the export into `progress/state.json` and keeps a copy in `progress/browser/` |
| 10 | Claude Code's Grep and Glob may skip the gitignored `courses/` | Every skill and agent lists course files with `studykit ls <c>` and ids with `studykit index <c> --json` and reads explicit paths (Read is unaffected); the hooks take the path from the event |
| 11 | Cost and time of a full ingest and generation run on large courses | Text-first reading: ingesters read the extracted page text and open PDF pages only where `ingest extract` flagged them, and transcribe a scanned page once into `pNNNN.vision.md`; chunks of at most 20 pages, past exams whole; the `ingester` on sonnet with medium effort and 40 turns; at most 6 agents at a time (3 for mock exams) and at most 2 fix rounds per step (3 for publish); round 2 shows an estimate of authors, items, agent runs and time for both scopes before the go, and no-go stops; scope core builds summary, MC and plan first and defers exercises, mock exams and the cheat sheet; `pipeline status` derives every step from the files, so a resumed run redoes only its `todo` (missing or stale notes, items not verified, stale PDFs); `ingest extract` and `add` skip documents whose sha256 is known and keep their chunk ids, and `/add-material` reads only new and changed chunks; figures and PDFs are cached by digest (a code change to `src/studykit` still makes every figure, and with them the PDFs, stale) |
| 12 | Mock exams copy past exams too closely | Modelled at archetype level; n-gram similarity warning (planned); new values and circuits required |
| 13 | YAML pitfalls (backslash escapes, YAML 1.1 vs 1.2) | Scalar-style lint from parser events; restricted PyYAML loader that reads plain scalars like the YAML 1.2 core schema; the site gets frontmatter from that loader through the render bridge and reads `course.yaml` and `plan.yaml` with `yaml` 1.2 (core schema); no LaTeX in `course.yaml` |
