// Defines every study-kit custom element (docs/architecture.md §3.2) and fills the shell's
// progress placeholders (dashboard.ts). The base layout imports this module once.
// <sk-mc> comes first so that questions inside <sk-exam> and <sk-quiz> are already
// upgraded when their container sets up.

import { startDashboard } from './dashboard.ts';
import { SkAnswerCheck } from './sk-answer-check.ts';
import { SkExam } from './sk-exam.ts';
import { SkExport } from './sk-export.ts';
import { SkHints } from './sk-hints.ts';
import { SkMc } from './sk-mc.ts';
import { SkPlan } from './sk-plan.ts';
import { SkProgress } from './sk-progress.ts';
import { SkQuiz } from './sk-quiz.ts';
import { SkReveal } from './sk-reveal.ts';
import { SkSelfAssess } from './sk-self-assess.ts';
import { SkTheme } from './sk-theme.ts';
import { define } from './util.ts';

define('sk-theme', SkTheme);
define('sk-mc', SkMc);
define('sk-quiz', SkQuiz);
define('sk-exam', SkExam);
define('sk-hints', SkHints);
define('sk-answer-check', SkAnswerCheck);
define('sk-reveal', SkReveal);
define('sk-self-assess', SkSelfAssess);
define('sk-plan', SkPlan);
define('sk-progress', SkProgress);
define('sk-export', SkExport);

if (typeof document !== 'undefined') startDashboard();

export {
  SkAnswerCheck,
  SkExam,
  SkExport,
  SkHints,
  SkMc,
  SkPlan,
  SkProgress,
  SkQuiz,
  SkReveal,
  SkSelfAssess,
  SkTheme,
};
