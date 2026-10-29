// Shared look of the fake lecture materials (examples/sample-materials/README.md).
// Deliberately not the study-kit house style: these stand in for a lecturer's own PDFs.
// Compiled by build.py with `--root examples/sample-materials`, so figures are the SVGs
// studykit.figures renders into /_build/work/figures/.

#let lehrstuhl = [Lehrstuhl für Elektronische Schaltungen (Beispiel)]
#let modul = [Elektronik 1]

#let fig(slug, width: 100%) = image("/_build/work/figures/" + slug + ".svg", width: width)

// A4 handout: exercise sheets, solutions, exams, the script.
#let blatt(kopf, body) = {
  set document(title: kopf, author: "Lehrstuhl für Elektronische Schaltungen")
  set page(
    paper: "a4",
    margin: (x: 2.2cm, top: 2.6cm, bottom: 2.2cm),
    header: context {
      set text(8.5pt)
      grid(columns: (1fr, auto), lehrstuhl, [#modul · #kopf])
      line(length: 100%, stroke: 0.4pt)
    },
    footer: context {
      set text(8.5pt)
      align(center)[Seite #counter(page).display() von #counter(page).final().first()]
    },
  )
  set text(lang: "de", size: 10.5pt)
  set par(justify: true)
  set heading(numbering: none)
  show heading.where(level: 1): set text(size: 15pt)
  show heading.where(level: 2): set text(size: 12pt)
  body
}

// One task with its points in the margin column.
#let aufgabe(nr, titel, punkte: none, body) = {
  v(0.6em)
  block(breakable: true, width: 100%)[
    #grid(
      columns: (1fr, auto),
      text(weight: "bold")[Aufgabe #nr: #titel],
      if punkte != none { text(weight: "bold")[(#punkte Punkte)] },
    )
    #body
  ]
}

// 16:9 lecture slides: one `folie` per page.
#let folien(titel, body) = {
  set document(title: titel, author: "Lehrstuhl für Elektronische Schaltungen")
  set page(
    width: 25.4cm,
    height: 14.29cm,
    margin: (x: 1.4cm, top: 1.2cm, bottom: 1.3cm),
    footer: context {
      set text(8pt, fill: luma(90))
      grid(
        columns: (1fr, auto),
        [#modul · Vorlesung 3 · Operationsverstärker-Grundschaltungen],
        [#counter(page).display() / #counter(page).final().first()],
      )
    },
  )
  set text(lang: "de", size: 15pt)
  set list(spacing: 0.7em)
  body
}

#let folie(titel, body) = {
  pagebreak(weak: true)
  block(width: 100%, inset: (bottom: 0.3em), stroke: (bottom: 1.2pt + rgb("#1b4f8a")))[
    #text(size: 21pt, weight: "bold", fill: rgb("#1b4f8a"), titel)
  ]
  v(0.4em)
  body
}

#let merke(body) = block(
  width: 100%,
  inset: 0.6em,
  radius: 3pt,
  fill: rgb("#eef3fa"),
  stroke: 0.8pt + rgb("#1b4f8a"),
  body,
)
