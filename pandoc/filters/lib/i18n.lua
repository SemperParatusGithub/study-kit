-- i18n: the few labels the filter writes into documents, in German and English.
-- Content language comes from course.lang (-M sk-lang); UI chrome lives on the site.

local M = {}

local labels = {
  de = {
    hint = 'Hinweis',
    hints = 'Hinweise',
    solution = 'Lösung',
    solutions = 'Lösungen',
    definition = 'Definition',
    theorem = 'Satz',
    example = 'Beispiel',
    note = 'Anmerkung',
    warning = 'Achtung',
    takeaways = 'Zusammenfassung',
    explanation = 'Erklärung',
    task = 'Aufgabe',
    points = 'Punkte',
    question = 'Frage',
    answer_key = 'Antwortschlüssel',
    ['true'] = 'richtig',
    ['false'] = 'falsch',
    back_task = 'zur Aufgabe',
    back_question = 'zur Frage',
    ref_ex = 'Übung',
    ref_mc = 'Frage',
    ref_topic = 'Thema',
    ref_exam = 'Klausur',
    ref_src = 'Quelle',
    page = 'S.',
  },
  en = {
    hint = 'Hint',
    hints = 'Hints',
    solution = 'Solution',
    solutions = 'Solutions',
    definition = 'Definition',
    theorem = 'Theorem',
    example = 'Example',
    note = 'Note',
    warning = 'Warning',
    takeaways = 'Key takeaways',
    explanation = 'Explanation',
    task = 'Task',
    points = 'points',
    question = 'Question',
    answer_key = 'Answer key',
    ['true'] = 'true',
    ['false'] = 'false',
    back_task = 'back to the task',
    back_question = 'back to the question',
    ref_ex = 'Exercise',
    ref_mc = 'Question',
    ref_topic = 'Topic',
    ref_exam = 'Exam',
    ref_src = 'Source',
    page = 'p.',
  },
}

M.languages = { de = true, en = true }

--- The label `key` in language `lang` (falls back to English, then to the key itself).
function M.t(lang, key)
  local tbl = labels[lang] or labels.en
  return tbl[key] or labels.en[key] or key
end

return M
