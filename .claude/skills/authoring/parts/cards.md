# Part: cards (`cards/<topic>.md`)

The flash cards of one chapter of a topic (`kind: topic`, docs/architecture.md §5.6): what a
student should be able to recall without looking, once they have read the chapter. The card
page shows the front, the student thinks, turns the card and says whether they knew it.

## Inputs

The chapter `summary/<nn>-<topic>.md` (write after it exists), its notes in `sources/notes/`
and the cards the chapter already has. Numbers come from `studykit calc`.

## Structure

- Frontmatter: `topic`, `title` (for example „Karteikarten: <chapter title>“).
- Only `:::: {.flashcard #card-<topic>-NNN}` blocks, numbered from 001: the front (a question
  or a term, usually one sentence), then one `::: back` block. Template: the content-format
  skill's `templates/cards.md`.
- 8 to 20 cards per chapter, in the order the chapter teaches: at least 5 (SK-COV-CARDS).

## Rules

- **One fact per card.** A card with two answers is two cards. A list of more than three
  items is split, or asks for the idea behind the list.
- **Recall, not recognition.** Ask so that the answer must be produced: „Warum …?“, „Was
  passiert, wenn …?“, „Wofür steht …?“. Never yes/no, never a question whose wording gives the
  answer away, and no "which of these" (a topic has no multiple choice).
- **A mix:** terms and their meaning, the why behind a rule, consequences of a change, and
  a small number or formula when it matters. Never ask something the chapter does not teach.
- **Short backs:** one to three sentences, a formula, a small table or one small figure; the
  back answers the front and adds at most one sentence of reason.
- Same symbols and words as the chapter; `[…](topic:<id>)` only where another chapter really
  explains the answer.
- Existing cards keep their ids when the content changes; a removed card's id goes into
  `retired_ids` through the caller (report it under `removed`).
