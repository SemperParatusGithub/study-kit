// study-kit house library (docs/architecture.md §3.3).
//
// pandoc/filters/studykit.lua emits calls to these functions (lib/document.lua for the
// documents `studykit pdf` assembles), so their names and parameters are the contract
// between the filter and this file; change both together.
//
// Compile with `typst compile --root <repo> --ignore-system-fonts`: only Typst's embedded
// fonts are used (New Computer Modern, New Computer Modern Math, DejaVu Sans Mono), so a
// document has the same page count on every machine. The cheat sheet reads
// `--input density=0..4` (9, 8.5, 8, 7.5, 7 pt) and records its page geometry under
// <cs-page>, so `studykit cheatsheet fit` can turn the position of <cs-end> and of each
// section heading (`typst eval … --in cheatsheet.typ`) into pages.
//
// Colours are print-friendly versions of the site's roles (site/src/styles/tokens.css):
// a box is a light tint with a coloured rule and title, and colour is never the only
// signal (every box has a title, every key a letter and a word).

// --- palette ------------------------------------------------------------------------------

#let sk-fg = rgb("#1f2328")
#let sk-muted = rgb("#59636e")
#let sk-rule = rgb("#c9cdd1")
#let sk-faint = rgb("#e2e4e1")
#let sk-surface = rgb("#f6f7f5")
#let sk-accent = rgb("#1f5fbf")

// kind: (rule and title colour, tint)
#let sk-box-colors = (
  definition: (rgb("#1f5fbf"), rgb("#f1f5fc")),
  theorem: (rgb("#6f42c1"), rgb("#f6f2fc")),
  example: (rgb("#0f7b6c"), rgb("#eef7f4")),
  note: (rgb("#57606a"), rgb("#f4f5f3")),
  warning: (rgb("#ad5600"), rgb("#fff5ea")),
  takeaways: (rgb("#1a7f37"), rgb("#eef7f0")),
  hint: (rgb("#966400"), rgb("#fff8e6")),
  solution: (rgb("#197c35"), rgb("#eff7f1")),
)

// The filter passes its own labels (`labels: sk-l`, from lib/i18n.lua); these English
// ones only fill in for a key a caller leaves out.
#let sk-default-labels = (
  yes: [true],
  no: [false],
  explanation: [Explanation],
  answer-key: [Answer key],
  question: [Question],
  correct: [Answer],
  single: [Exactly one answer is correct.],
  multi: [One or more answers are correct.],
  kprim: [Mark each statement as true or false.],
  hint: [Hint],
  solution: [Solution],
  rubric: [Marking scheme],
  criterion: [Criterion],
  points: [points],
  total: [Total],
  results: [Results],
  objectives: [Learning objectives],
  page-of: "Page %s of %s",
)

#let sk-label(labels, key) = {
  let own = if labels == none { (:) } else { labels }
  own.at(key, default: sk-default-labels.at(key))
}

// The document kind (sk-doc) for functions whose look depends on it.
#let sk-kind = state("sk-kind", "file")

// Level-1 headings so far (unnumbered headings do not step the heading counter).
#let sk-chapters = counter("sk-chapters")

// Cheat-sheet densities 0–4: font size, leading, paragraph spacing, page margin, gutter.
#let sk-densities = (
  (size: 9pt, leading: 0.5em, spacing: 0.75em, margin: 1.3cm, gutter: 0.8cm),
  (size: 8.5pt, leading: 0.46em, spacing: 0.7em, margin: 1.15cm, gutter: 0.7cm),
  (size: 8pt, leading: 0.42em, spacing: 0.65em, margin: 1cm, gutter: 0.6cm),
  (size: 7.5pt, leading: 0.4em, spacing: 0.6em, margin: 0.9cm, gutter: 0.55cm),
  (size: 7pt, leading: 0.38em, spacing: 0.55em, margin: 0.8cm, gutter: 0.5cm),
)

#let sk-density-level() = {
  let raw = sys.inputs.at("density", default: "0")
  if raw in ("0", "1", "2", "3", "4") { int(raw) } else { 0 }
}

#let sk-density() = sk-densities.at(sk-density-level())

// --- document info (written once by the filter, read by footers) --------------------------

#let sk-info-data() = {
  let found = query(<sk-info>)
  if found.len() > 0 { found.first().value } else { (:) }
}

// "Seite %s von %s" with the numbers filled in.
#let sk-fill(template, ..values) = {
  let parts = template.split("%s")
  let out = parts.first()
  for (i, v) in values.pos().enumerate() {
    out += str(v) + parts.at(i + 1, default: "")
  }
  out
}

#let sk-footer(kind) = context {
  let info = sk-info-data()
  let n = counter(page).get().first()
  let total = counter(page).final().first()
  set text(size: if kind == "cheatsheet" { 6.5pt } else { 8pt }, fill: sk-muted)
  set par(justify: false)
  let left = if kind in ("exam", "exam-solutions") {
    info.at("title", default: "")
  } else {
    (info.at("course", default: none), info.at("title", default: none))
      .filter(x => x != none and x != "")
      .join([ · ])
  }
  let right = if kind in ("exam", "exam-solutions", "cheatsheet") {
    let labels = info.at("labels", default: (:))
    sk-fill(labels.at("page-of", default: sk-default-labels.page-of), n, total)
  } else {
    str(n)
  }
  if kind == "file" {
    align(center, str(n))
  } else {
    line(length: 100%, stroke: 0.4pt + sk-faint)
    v(-0.35em)
    grid(columns: (1fr, auto), column-gutter: 1em, if left == none { [] } else { left }, right)
  }
}

// --- the document ---------------------------------------------------------------------------

// The whole document (the pandoc template calls it). `kind` is the PDF document
// (lib/document.lua) or "file" for a single course file; `title` sets the PDF metadata.
#let sk-doc(lang: "de", solutions: "appendix", kind: "file", title: none, body) = {
  let cs = kind == "cheatsheet"
  let dens = sk-density()
  let size = if cs { dens.size } else { 10.5pt }

  set document(title: title, date: none) if title != none
  set document(date: none) if title == none
  set page(
    paper: "a4",
    margin: if cs { dens.margin } else { (left: 2.6cm, right: 2.6cm, top: 2.3cm, bottom: 2.8cm) },
    columns: if cs { 2 } else { 1 },
    footer: sk-footer(kind),
    footer-descent: if cs { 0.35cm } else { 1.8em },
  )
  set columns(gutter: dens.gutter) if cs
  set text(font: "New Computer Modern", size: size, lang: lang, fill: sk-fg, hyphenate: true)
  // the cheat sheet's lines are tight: a line measured by its glyphs, not the cap height,
  // keeps a root or fraction at the start of a box clear of the title above it
  set text(top-edge: "bounds") if cs
  show math.equation: set text(font: "New Computer Modern Math")
  show raw: set text(font: "DejaVu Sans Mono", size: 0.86em)
  set par(
    justify: true,
    leading: if cs { dens.leading } else { 0.62em },
    spacing: if cs { dens.spacing } else { 1.05em },
  )
  set list(indent: 0.4em, body-indent: 0.5em, spacing: if cs { dens.leading + 0.15em } else { auto })
  set enum(indent: 0.4em, body-indent: 0.5em)
  set terms(hanging-indent: 1.5em)
  set block(spacing: if cs { dens.spacing } else { 1.05em })
  show link: set text(fill: sk-accent)

  // headings: no numbers (the assembler writes them), sticky to what follows
  set heading(numbering: none)
  show heading: set text(weight: "bold", hyphenate: false)
  show heading: set par(justify: false)
  // a chapter of the summary and an exam task start a page (not the outline's own title);
  // in the solutions the first task shares the page with the title
  show heading.where(level: 1): it => {
    if kind in ("summary", "exam") and it.outlined {
      pagebreak(weak: true)
    } else if kind == "exam-solutions" and it.outlined {
      sk-chapters.step()
      context if sk-chapters.get().first() > 1 { pagebreak(weak: true) }
    }
    let s = if cs { 1.25em } else { 1.45em }
    block(above: if cs { 0.8em } else { 2em }, below: if cs { 0.5em } else { 0.9em }, sticky: true, {
      text(size: s, it.body)
      if not cs {
        v(-0.35em)
        line(length: 100%, stroke: 0.7pt + sk-accent)
      }
    })
  }
  show heading.where(level: 2): it => block(
    above: if cs { 0.9em } else { 1.7em },
    below: if cs { 0.45em } else { 0.75em },
    sticky: true,
    {
      if cs {
        set text(size: 1.08em, fill: sk-accent)
        it.body
        v(-0.45em)
        line(length: 100%, stroke: 0.5pt + sk-accent)
      } else {
        text(size: 1.22em, it.body)
      }
    },
  )
  show heading.where(level: 3): it => block(
    above: 1.3em,
    below: 0.6em,
    sticky: true,
    text(size: 1.05em, it.body),
  )

  // figures: images keep the size their script gave them and shrink to fit the column
  set figure(gap: 0.6em)
  show figure: set block(breakable: false)
  show figure: it => block(above: 1.2em, below: 1.2em, width: 100%, it)
  show figure.caption: it => {
    set text(size: 0.88em)
    set par(justify: false)
    if cs {
      it.body
    } else {
      [#text(fill: sk-muted, weight: "bold")[#it.supplement #context it.counter.display(it.numbering):] #it.body]
    }
  }
  show figure.where(kind: table): set figure.caption(position: top)
  set figure(numbering: none) if cs

  // tables from Markdown: rules instead of a grid, the header in bold
  set table(
    inset: (x: 0.5em, y: 0.38em),
    stroke: (x, y) => (
      top: if y == 0 { 0.8pt + sk-fg } else { 0pt },
      bottom: 0.4pt + sk-rule,
    ),
  )
  show table.cell.where(y: 0): set text(weight: "bold")
  show table: set par(justify: false)
  // pandoc centres a table; its cells read better left-aligned unless the source says so
  show table: set align(left)

  // code
  show raw.where(block: true): it => block(
    width: 100%,
    fill: sk-surface,
    inset: (x: 0.8em, y: 0.65em),
    radius: 2pt,
    stroke: 0.4pt + sk-faint,
    it,
  )

  // display math: a formula wider than the column shrinks to fit instead of overflowing
  show math.equation.where(block: true): it => layout(size => {
    let w = measure(it).width
    if w > size.width and w > 0pt {
      let f = size.width / w * 100%
      scale(x: f, y: f, reflow: true, it)
    } else {
      it
    }
  })

  sk-kind.update(kind)
  if cs {
    // the page as `studykit cheatsheet fit` measures it (A4, equal margins, two columns)
    [#metadata((
      density: sk-density-level(),
      width: 210mm,
      height: 297mm,
      margin: dens.margin,
      columns: 2,
      gutter: dens.gutter,
    )) <cs-page>]
  }
  body
}

// --- start of an assembled document ---------------------------------------------------------

// `data`: (kind, title, course, subtitle?, outline?, outline-depth?) from `studykit pdf`;
// the footers read it back through the <sk-info> label. Exams start with their cover
// instead of a title block.
#let sk-info(data, labels: none) = {
  let all = data + (labels: if labels == none { sk-default-labels } else { labels })
  [#metadata(all) <sk-info>]
  let kind = data.at("kind", default: "file")
  if kind == "exam" { return }
  let cs = kind == "cheatsheet"
  if cs {
    place(top, scope: "parent", float: true, clearance: 0.8em, {
      set par(justify: false)
      grid(
        columns: (1fr, auto),
        align: (left + bottom, right + bottom),
        text(size: 1.45em, weight: "bold", data.at("title", default: "")),
        text(size: 0.9em, fill: sk-muted, data.at("course", default: "")),
      )
      v(-0.3em)
      line(length: 100%, stroke: 0.8pt + sk-accent)
    })
    return
  }
  block(width: 100%, below: 1.8em, {
    set par(justify: false)
    let course = data.at("course", default: none)
    if course != none {
      text(size: 0.95em, fill: sk-muted, tracking: 0.02em, course)
      v(0.1em)
    }
    text(size: 2.1em, weight: "bold", data.at("title", default: ""))
    let sub = data.at("subtitle", default: none)
    if sub != none {
      v(0.15em)
      text(size: 1.1em, fill: sk-muted, sub)
    }
    v(0.2em)
    line(length: 100%, stroke: 1pt + sk-accent)
  })
  let outline-title = data.at("outline", default: none)
  if outline-title != none {
    show outline.entry.where(level: 1): set text(weight: "bold")
    show outline.entry.where(level: 1): set block(above: 0.9em)
    outline(title: outline-title, depth: data.at("outline-depth", default: 1), indent: 1.4em)
  }
}

// A small line under a heading (difficulty, minutes, points).
#let sk-meta(body) = context {
  let cs = sk-kind.get() == "cheatsheet"
  block(above: 0em, below: if cs { 0.5em } else { 1em }, sticky: true, {
    set par(justify: false)
    text(size: 0.86em, fill: sk-muted, body)
  })
}

// --- boxes ------------------------------------------------------------------------------------

// Keep a block on one page (or column) unless it is too tall to fit sensibly.
#let sk-keep(limit: 45%, body) = layout(size => context {
  let page-height = if page.height == auto { 1000pt } else { page.height }
  let h = measure(block(width: size.width, body)).height
  block(width: 100%, breakable: h > page-height * limit, body)
})

#let sk-box-frame(kind, title, body, cs: false) = {
  let (accent, tint) = sk-box-colors.at(kind, default: (sk-muted, sk-surface))
  block(
    width: 100%,
    fill: tint,
    stroke: (left: (if cs { 1.6pt } else { 2.2pt }) + accent),
    inset: if cs { (left: 0.6em, right: 0.5em, y: 0.42em) } else { (left: 0.95em, right: 0.85em, top: 0.7em, bottom: 0.75em) },
    radius: (right: 2pt),
    {
      if title != none {
        block(
          above: 0em,
          below: if cs { 0.4em } else { 0.6em },
          sticky: true,
          text(fill: accent, weight: "bold", size: if cs { 1em } else { 0.95em }, title),
        )
      }
      body
    },
  )
}

// Container blocks: definition, theorem, example, note, warning, takeaways. A box shorter
// than `keep` of the page stays whole; a longer one may break (in the cheat sheet, never).
#let sk-box(kind: "note", title: none, keep: 30%, body) = context {
  let cs = sk-kind.get() == "cheatsheet"
  let frame = sk-box-frame(kind, title, body, cs: cs)
  block(above: if cs { 0.7em } else { 1.25em }, below: if cs { 0.7em } else { 1.25em }, if cs {
    block(breakable: false, frame)
  } else {
    sk-keep(limit: keep, frame)
  })
}

#let sk-hint(index: 1, title: none, body) = sk-box(kind: "hint", title: title, body)

// One exercise or exam task with its heading: kept on one page unless it is long.
#let sk-unit(body) = block(width: 100%, above: 2em, below: 1.2em, sk-keep(limit: 55%, body))

#let sk-solution(title: none, body) = sk-box(kind: "solution", title: title, keep: 25%, body)

// Several formulas side by side (top-level \qquad in the source): each stays whole, and
// they are packed into as few centred rows as the column allows, 2em apart like \qquad.
#let sk-formulas(..parts) = block(width: 100%, breakable: false, layout(size => {
  let gap = 2em.to-absolute()
  let rows = ()
  let row = ()
  let used = 0pt
  for eq in parts.pos() {
    let w = measure(math.equation(block: false, math.display(eq.body))).width
    if row.len() > 0 and used + gap + w > size.width {
      rows.push(row)
      row = ()
    }
    used = if row.len() == 0 { w } else { used + gap + w }
    row.push(eq.body)
  }
  if row.len() > 0 { rows.push(row) }
  set block(spacing: 0.75em)
  for r in rows {
    math.equation(block: true, numbering: none, r.join(h(2em)))
  }
}))

// --- appendix (hints, solutions, answer keys) with back-links ------------------------------

#let sk-appendix(title: none, body) = {
  pagebreak(weak: true)
  if title != none {
    heading(level: 1, title)
  }
  body
}

#let sk-back-link(back, label) = if back != none {
  h(1fr)
  text(size: 0.82em, weight: "regular", link(back, label))
}

// An entry stays on one page unless it is long (a solution with a figure).
#let sk-appendix-entry(title: none, back: none, back-label: [↑], body) = block(
  width: 100%,
  above: 1.5em,
  below: 1.2em,
  sk-keep(limit: 35%, {
    block(below: 0.7em, sticky: true, {
      set par(justify: false)
      text(weight: "bold", size: 1.05em, title)
      sk-back-link(back, back-label)
      v(-0.4em)
      line(length: 100%, stroke: 0.4pt + sk-rule)
    })
    body
  }),
)

// One hint inside an appendix entry: the label in a narrow column, the hint beside it.
#let sk-hint-entry(index: 1, title: none, body) = block(above: 0.8em, below: 0.8em, breakable: false, grid(
  columns: (5.2em, 1fr),
  column-gutter: 0.6em,
  text(fill: sk-box-colors.hint.at(0), weight: "bold", size: 0.92em, title), body,
))

// --- multiple choice --------------------------------------------------------------------------

#let sk-checkbox = box(width: 0.78em, height: 0.78em, stroke: 0.7pt + sk-fg, radius: 1pt, baseline: 0.08em)

#let sk-mark(correct) = if correct {
  text(fill: sk-box-colors.solution.at(0), weight: "bold", sym.checkmark)
} else {
  text(fill: sk-box-colors.warning.at(0), weight: "bold", sym.times)
}

// The answer: correct keys, every option with its why, and the explanation.
#let sk-mcq-answer(type: "single", options: (), explanation: none, labels: sk-default-labels) = {
  let correct = options.filter(o => o.correct).map(o => o.key)
  let wrong = options.filter(o => not o.correct).map(o => o.key)
  block(below: 0.7em, {
    text(weight: "bold", sk-label(labels, "correct") + [: ])
    if type == "kprim" {
      let yes = if correct.len() > 0 { correct.join(", ") } else { "–" }
      let no = if wrong.len() > 0 { wrong.join(", ") } else { "–" }
      sk-label(labels, "yes") + [: ] + text(weight: "bold", yes) + h(0.4em) + [·] + h(0.4em)
      sk-label(labels, "no") + [: ] + text(weight: "bold", no)
    } else {
      text(weight: "bold", correct.join(", "))
    }
  })
  grid(
    columns: (auto, auto, 1fr),
    column-gutter: 0.55em,
    row-gutter: 0.75em,
    ..options
      .map(o => (
        [(#o.key)],
        if type == "kprim" {
          text(weight: "bold", if o.correct { sk-label(labels, "yes") } else { sk-label(labels, "no") })
        } else { sk-mark(o.correct) },
        [#o.text #h(0.3em) #text(fill: sk-muted)[— #o.why]],
      ))
      .flatten(),
  )
  if explanation != none {
    block(above: 0.85em, [#text(weight: "bold", sk-label(labels, "explanation")): #explanation])
  }
}

// One question. Options arrive already shuffled with their display keys (A)–(F).
#let sk-mcq(
  id: "",
  number: none,
  type: "single",
  difficulty: none,
  answers: "appendix",
  options: (),
  explanation: none,
  labels: sk-default-labels,
  stem,
) = {
  let instruction = sk-label(labels, if type in ("single", "multi", "kprim") { type } else { "single" })
  let choices = if type == "kprim" {
    table(
      columns: (auto, 1fr, auto, auto),
      inset: (x: 0.45em, y: 0.42em),
      align: (left + top, left + top, center + horizon, center + horizon),
      stroke: (x, y) => (bottom: if y == 0 { 0.6pt + sk-rule } else { 0.3pt + sk-faint }),
      table.header(
        [],
        [],
        text(size: 0.85em, weight: "regular", sk-label(labels, "yes")),
        text(size: 0.85em, weight: "regular", sk-label(labels, "no")),
      ),
      ..options.map(o => ([(#o.key)], o.text, sk-checkbox, sk-checkbox)).flatten(),
    )
  } else {
    grid(
      columns: (auto, auto, 1fr),
      column-gutter: 0.6em,
      row-gutter: 0.8em,
      ..options.map(o => (sk-checkbox, [(#o.key)], o.text)).flatten(),
    )
  }
  let question = grid(
    columns: (1.9em, 1fr),
    text(weight: "bold", if number != none { [#number.] } else { [] }),
    {
      stem
      block(above: 0.5em, below: 0.75em, text(size: 0.86em, style: "italic", fill: sk-muted, instruction))
      choices
    },
  )
  // one block, so the label the filter puts after the call names the question; a page may
  // break between the question and its inline answer, never inside either
  block(width: 100%, above: 1.6em, below: 1.6em, {
    sk-keep(limit: 60%, question)
    if answers == "inline" {
      pad(left: 1.9em, block(
        width: 100%,
        breakable: false,
        inset: (left: 0.9em, right: 0.8em, y: 0.7em),
        above: 1em,
        fill: sk-box-colors.solution.at(1),
        stroke: (left: 2.2pt + sk-box-colors.solution.at(0)),
        sk-mcq-answer(type: type, options: options, explanation: explanation, labels: labels),
      ))
    }
  })
}

// Answer-key entry for the appendix.
#let sk-mcq-key(
  id: "",
  type: "single",
  title: none,
  options: (),
  explanation: none,
  labels: sk-default-labels,
  back: none,
  back-label: [↑],
) = block(width: 100%, above: 1.4em, below: 1.2em, sk-keep(limit: 35%, {
  block(below: 0.65em, sticky: true, {
    set par(justify: false)
    text(weight: "bold", if title != none { title } else { id })
    h(0.6em)
    text(size: 0.82em, fill: sk-muted, raw(id))
    sk-back-link(back, back-label)
    v(-0.4em)
    line(length: 100%, stroke: 0.4pt + sk-rule)
  })
  sk-mcq-answer(type: type, options: options, explanation: explanation, labels: labels)
}))

// The key at a glance: number, answer and id of every question in the appendix.
#let sk-key-table(labels: sk-default-labels, rows: ()) = {
  let answer(r) = if r.type == "kprim" {
    [#sk-label(labels, "yes"): #(if r.keys.len() > 0 { r.keys.join(", ") } else { "–" })]
  } else {
    text(weight: "bold", r.keys.join(", "))
  }
  let cell(r, body) = if r.back != none { link(r.back, body) } else { body }
  let part(rs) = table(
    columns: (auto, 1fr, auto),
    inset: (x: 0.45em, y: 0.32em),
    align: (right, left, left),
    table.header(
      [#sym.numero],
      sk-label(labels, "correct"),
      sk-label(labels, "question"),
    ),
    ..rs
      .map(r => (
        cell(r, [#r.number]),
        answer(r),
        text(size: 0.8em, fill: sk-muted, raw(r.id)),
      ))
      .flatten(),
  )
  // two tables side by side, the rows split evenly
  let half = calc.ceil(rows.len() / 2)
  block(above: 0.8em, below: 1.8em, if rows.len() < 2 { part(rows) } else {
    grid(columns: (1fr, 1fr), column-gutter: 1.6em, part(rows.slice(0, half)), part(rows.slice(half)))
  })
}

// --- exercises, exams and summaries -------------------------------------------------------

// Results of an exercise or exam task: (label, value) rows.
#let sk-answers(labels: sk-default-labels, rows: ()) = block(above: 1em, below: 1em, breakable: false, {
  sk-box-frame("solution", sk-label(labels, "results"), grid(
    columns: (auto, 1fr),
    column-gutter: 1.2em,
    row-gutter: 0.6em,
    ..rows.flatten(),
  ))
})

// Marking scheme of an exam task: (points, criterion) rows and the total.
#let sk-rubric(labels: sk-default-labels, total: "", rows: ()) = block(above: 1.1em, below: 1.1em, breakable: false, {
  block(below: 0.5em, sticky: true, text(weight: "bold", sk-label(labels, "rubric")))
  table(
    columns: (1fr, auto),
    align: (left, right),
    table.header(sk-label(labels, "criterion"), sk-label(labels, "points")),
    ..rows.map(r => (r.at(1), r.at(0))).flatten(),
    table.hline(stroke: 0.6pt + sk-fg),
    text(weight: "bold", sk-label(labels, "total")), text(weight: "bold", total),
  )
})

#let sk-objectives(labels: sk-default-labels, body) = block(above: 0.4em, below: 1.4em, {
  sk-box-frame("note", sk-label(labels, "objectives"), body)
})

// Exam cover: title, course, fields to fill in, facts, aids, notes and the points table.
// `data` comes from `studykit pdf` (strings only).
#let sk-exam-cover(data) = {
  set par(justify: false)
  block(width: 100%, below: 1.6em, {
    text(size: 1em, fill: sk-muted, data.at("course", default: ""))
    v(0.15em)
    text(size: 2.3em, weight: "bold", data.at("title", default: ""))
    v(0.15em)
    line(length: 100%, stroke: 1pt + sk-accent)
  })
  let fields = data.at("fields", default: ())
  if fields.len() > 0 {
    grid(
      columns: (auto, 1fr),
      column-gutter: 0.8em,
      row-gutter: 1.5em,
      ..fields.map(f => (text(weight: "bold", f), block(height: 1.1em, width: 100%, stroke: (bottom: 0.5pt + sk-fg)))).flatten(),
    )
    v(1.6em)
  }
  let value(v) = if type(v) == array { v.join(linebreak()) } else { v }
  grid(
    columns: (auto, 1fr),
    column-gutter: 1.2em,
    row-gutter: 0.75em,
    ..data.at("facts", default: ()).map(f => (text(weight: "bold", f.at(0)), value(f.at(1)))).flatten(),
  )
  let notes = data.at("notes", default: ())
  if notes.len() > 0 {
    block(above: 1.4em, below: 0em, {
      text(weight: "bold", data.at("notes-title", default: ""))
      list(..notes)
    })
  }
  let tbl = data.at("table", default: none)
  if tbl != none {
    v(1fr)
    block(breakable: false, {
      text(weight: "bold", tbl.at("title", default: ""))
      v(0.2em)
      table(
        columns: (auto, 1fr, auto, 5.5em),
        inset: (x: 0.6em, y: 0.65em),
        align: (left + horizon, left + horizon, right + horizon, center + horizon),
        stroke: (x, y) => (
          bottom: if y <= tbl.rows.len() { 0.4pt + sk-rule } else { 0pt },
          top: if y == 0 { 0.8pt + sk-fg } else { 0pt },
        ),
        table.header(..tbl.head),
        ..tbl.rows.map(r => (r.at(0), r.at(1), r.at(2), [])).flatten(),
        table.hline(stroke: 0.8pt + sk-fg),
        text(weight: "bold", tbl.total.at(0)), [], text(weight: "bold", tbl.total.at(1)), [],
      )
    })
    v(1.2em)
  }
  pagebreak()
}

// --- study plan -----------------------------------------------------------------------------

// `data`: (intro, head, weeks: ((title, sessions: ((date, minutes, kind, goal, topics,
// tasks), …)), …)) from `studykit pdf`, strings only.
#let sk-plan(data) = {
  let intro = data.at("intro", default: ())
  if intro.len() > 0 {
    block(below: 1.2em, {
      set par(justify: false)
      intro.join(linebreak())
    })
  }
  let head = data.at("head", default: ("", "", "", "", ""))
  for week in data.at("weeks", default: ()) {
    block(breakable: false, above: 1.5em, below: 0.6em, sticky: true, heading(level: 2, week.title))
    table(
      columns: (1.3em, 5.6em, 4.4em, 6.9em, 1fr),
      inset: (x: 0.4em, y: 0.5em),
      align: (center + top, left + top, right + top, left + top, left + top),
      stroke: (x, y) => (top: if y == 0 { 0.8pt + sk-fg } else { 0pt }, bottom: 0.4pt + sk-rule),
      table.header(..head.map(h => text(size: 0.9em, hyphenate: false, h))),
      ..week
        .sessions
        .map(s => (
          sk-checkbox,
          text(hyphenate: false, s.date),
          text(hyphenate: false, s.minutes),
          text(hyphenate: false, s.kind),
          {
            set par(justify: false)
            if s.at("goal", default: none) != none {
              text(weight: "bold", hyphenate: false, s.goal) + linebreak()
            }
            if s.at("topics", default: none) != none {
              text(size: 0.88em, fill: sk-muted, s.topics) + linebreak()
            }
            text(size: 0.92em, s.tasks.join(linebreak()))
          },
        ))
        .flatten(),
    )
  }
}
