// pandoc template for study-kit (pandoc/defaults/typst.yaml); the house library does the rest.
#import "/typst/studykit.typ": *
#let horizontalRule = line(start: (25%, 0%), end: (75%, 0%))
#let divider = if "divider" in std { divider } else { horizontalRule }
$if(highlighting-definitions)$
$highlighting-definitions$
$endif$
#show: sk-doc.with(
  lang: "$if(sk-lang)$$sk-lang$$else$de$endif$",
  solutions: "$if(sk-solutions)$$sk-solutions$$else$appendix$endif$",
$if(title)$
  title: [$title$],
$endif$
)

$body$
