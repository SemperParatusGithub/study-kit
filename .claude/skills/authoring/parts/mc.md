# Part: mc (`mc/<topic>.md`)

The practice MC bank of one topic. Exam MC questions live in `exams/<id>/mc.md` and are
written with [exam.md](exam.md), never copied into a bank.

## How many and which types

- `targets.mc_per_topic: auto`: max(10, ⌈25 × weight⌉), at most 25 (SK-COV-MC); a number
  means that many; `--add n` adds n.
- Type mix from `analysis/exam-profile.yaml` (`mc.type_mix`), else **60 % single, 25 %
  multi, 15 % Kprim**, rounded so each type in `course.exam.mc.types` occurs at least once.
- Difficulty: about a third each at 1, 2 and 3; a few at 4 for focus topics.
- New questions get the next free number `mc-<topic>-NNN` (3 digits) of the bank.

## Writing one question

- **One concept per stem.** A question tests one idea (one formula, one effect, one
  definition). Two ideas make two questions.
- The stem is a complete question that could be answered without the options; no "Which of
  the following is wrong?" unless the negation is the point, then write "nicht"/"not" in
  the stem plainly.
- **Options of similar length and form:** same grammatical form, similar length (the correct
  one must not be the longest; SK-MCQ-BIAS warns when it is in more than half of the bank's
  single-choice questions), numbers in the same unit and precision.
- **Every distractor's `why` names its mistake** in one sentence ("Faktor $2\pi$
  vergessen", "Effektivwert statt Amplitude"), and the correct option's `why` gives the
  reason in one line. A distractor without a nameable mistake is replaced.
- Numeric distractors are produced by applying the mistake to the same data, computed in
  Python, so the verifier can reproduce each one (`mc_numeric`); every distractor differs
  from the correct value by more than 5 %, and no two options coincide. Write each numeric
  option as the bare value with its unit (`$4.82\,\mathrm{kHz}$`, `$-4.68$`), never
  `$V \approx …$` or `$U_a = …$`: only then does studykit treat the question as numeric
  and ask for its `mc_numeric` check (SK-VER-CHECK).
- Kprim: four independent statements about one situation, about half true; each statement
  decidable on its own.
- multi: 4-6 options, at least one right and one wrong; a final "Keine der Aussagen ist
  richtig." needs `pin-last="true"`.
- The explanation gives the short reasoning and never names an option by its letter.
- Spread the correct position: in the source order, do not always put `[x]` first or last.

## Misconception catalogue (distractor sources)

| Mistake | Example in electrical engineering |
|---|---|
| forgotten 2π | ω instead of f: $1/(RC)$ for $f_\mathrm{g}$ |
| 2π inverted | $2\pi/(RC)$ or $2\pi RC$ |
| √2 | amplitude vs. RMS ($\hat{u}$ vs. $U$), $|\underline{H}| = 1/2$ instead of $1/\sqrt{2}$ |
| dB vs. linear | $10\lg$ for an amplitude ratio, −6 dB for the half-power point |
| sign of the phase | lead vs. lag, $+45^\circ$ for a low-pass, $\arctan$ of the inverse |
| series vs. parallel | adding resistances that are in parallel, $R_\mathrm{L}$ in series |
| power of ten | nF vs. µF, kΩ vs. Ω, ms vs. µs |
| degrees vs. radians | $\arctan$ result taken as degrees, $\omega t$ in degrees |
| RMS sums | adding RMS values of phase-shifted voltages |
| limit cases | value at $f \to 0$ or $f \to \infty$ instead of at $f_\mathrm{g}$ |
| reference direction | wrong sign from the arrow convention, source vs. load arrows |
| time constant | $\tau$ vs. $\tau \ln 2$, charge vs. discharge curve |
| first vs. second order | 40 dB per decade for a first-order filter |
| reciprocal | $I_\mathrm{k}/U_\mathrm{q}$ instead of $U_\mathrm{q}/I_\mathrm{k}$ |

Extend it with the mistakes the topic's notes and past exams show; the summary's
`warning` boxes should name the same mistakes.

## Checklist before finishing

- counts and type mix as above; every option has two paragraphs; one explanation each
- `studykit validate <course> --paths mc/<topic>.md` clean, including no SK-MCQ-BIAS
- numeric questions: list their ids in `notes` so the verifier writes `mc_numeric` checks

Template: the content-format skill's `templates/mc-bank.md`.
