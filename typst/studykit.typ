// study-kit house library: minimal Phase 3 stub.
//
// pandoc/filters/studykit.lua emits calls to these functions, so their names and
// parameters are the contract; Phase 4 replaces the look, not the API.
// Compile with `typst compile --root <repo> --ignore-system-fonts`: only Typst's
// embedded fonts are used.

#let sk-default-labels = (
  yes: [true],
  no: [false],
  explanation: [Explanation],
  answer-key: [Answer key],
)

#let sk-accent = (
  definition: rgb("#0072b2"),
  theorem: rgb("#009e73"),
  example: rgb("#56b4e9"),
  note: rgb("#6e7781"),
  warning: rgb("#d55e00"),
  takeaways: rgb("#cc79a7"),
  hint: rgb("#e69f00"),
  solution: rgb("#009e73"),
)

// The whole document. `solutions` is informational; the filter already placed them.
#let sk-doc(lang: "de", title: none, solutions: "appendix", body) = {
  set document(title: title) if title != none
  set page(paper: "a4", margin: (x: 2.2cm, y: 2.5cm), numbering: "1")
  set text(lang: lang, size: 10.5pt)
  set par(justify: true)
  set table(inset: 6pt, stroke: none)
  set terms(hanging-indent: 1.5em)
  show figure.where(kind: image): set figure.caption(position: bottom)
  if title != none {
    align(center, text(size: 16pt, weight: "bold", title))
  }
  body
}

// Container blocks: definition, theorem, example, note, warning, takeaways.
#let sk-box(kind: "note", title: none, body) = block(
  width: 100%,
  breakable: true,
  inset: (left: 10pt, right: 8pt, y: 7pt),
  stroke: (left: 2pt + sk-accent.at(kind, default: luma(120))),
  fill: luma(247),
  {
    if title != none {
      block(below: 0.7em, text(weight: "bold", title))
    }
    body
  },
)

#let sk-hint(index: 1, title: none, body) = sk-box(kind: "hint", title: title, body)

#let sk-solution(title: none, body) = sk-box(kind: "solution", title: title, body)

// Appendix sections (hints, solutions, answer keys) with back-links.
#let sk-appendix(title: none, body) = {
  pagebreak(weak: true)
  if title != none {
    heading(level: 2, title)
  }
  body
}

#let sk-back-link(back, label) = if back != none {
  h(1fr)
  text(size: 0.85em, link(back, label))
}

#let sk-appendix-entry(title: none, back: none, back-label: [↑], body) = block(
  width: 100%,
  breakable: true,
  below: 1.2em,
  {
    block(below: 0.6em, {
      text(weight: "bold", title)
      sk-back-link(back, back-label)
    })
    body
  },
)

#let sk-checkbox = box(width: 0.75em, height: 0.75em, stroke: 0.6pt, baseline: 0.05em)

// The answer: correct keys, every option's why and the explanation.
#let sk-mcq-answer(type: "single", options: (), explanation: none, labels: sk-default-labels) = {
  let mark(o) = if type == "kprim" {
    if o.correct { labels.yes } else { labels.no }
  } else if o.correct { sym.checkmark } else { sym.times }
  let correct = options.filter(o => o.correct).map(o => o.key)
  if type != "kprim" {
    block(below: 0.6em, text(weight: "bold", correct.join(", ")))
  }
  grid(
    columns: (auto, auto, 1fr),
    column-gutter: 0.6em,
    row-gutter: 0.7em,
    ..options.map(o => ([(#o.key)], mark(o), o.why)).flatten(),
  )
  if explanation != none {
    block(above: 0.8em, [#text(weight: "bold", labels.explanation): #explanation])
  }
}

// One question. Options arrive already shuffled with their display keys.
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
) = block(width: 100%, breakable: false, above: 1.4em, below: 1.4em, {
  if number != none {
    text(weight: "bold", [#number. ])
  }
  stem
  v(0.2em)
  if type == "kprim" {
    grid(
      columns: (auto, auto, auto, 1fr),
      column-gutter: 0.8em,
      row-gutter: 0.7em,
      align: (center, center, left, left),
      text(size: 0.8em, labels.yes), text(size: 0.8em, labels.no), [], [],
      ..options.map(o => (sk-checkbox, sk-checkbox, [(#o.key)], o.text)).flatten(),
    )
  } else {
    grid(
      columns: (auto, auto, 1fr),
      column-gutter: 0.8em,
      row-gutter: 0.7em,
      ..options.map(o => (sk-checkbox, [(#o.key)], o.text)).flatten(),
    )
  }
  if answers == "inline" {
    block(
      width: 100%,
      inset: 8pt,
      above: 0.9em,
      fill: luma(247),
      sk-mcq-answer(type: type, options: options, explanation: explanation, labels: labels),
    )
  }
})

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
) = block(width: 100%, breakable: true, below: 1.2em, {
  block(below: 0.6em, {
    text(weight: "bold", if title != none { title } else { id })
    sk-back-link(back, back-label)
  })
  sk-mcq-answer(type: type, options: options, explanation: explanation, labels: labels)
})
