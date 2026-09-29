/**
 * TF-736: display helpers shared by the generation panel (GenerationTasksBar)
 * and the "running generations" list in Premium's RAGExamCreator, so both
 * decide under-fill and render progress the same way.
 */

import type { TFunction } from 'i18next';
import type { GenerationTaskState } from '../types';

export interface ContextLimit {
  requested: number | null;
  generated: number | null;
}

/**
 * Requested and generated question counts of a SUCCESS that produced fewer
 * questions than asked for, because the document material ran out. `null` for
 * every other task. Decided by the `context_limited` boolean, never by the
 * presence of a notice text. The live result's quality_metrics win; the
 * job-row values from the result endpoint cover an expired Celery result.
 * Relies on `result` and `contextLimited`/`generatedQuestionCount` always
 * being refreshed together (true today — see GenerationTasksContext's recovery
 * effect) — do not update one without the other.
 */
export const contextLimitOf = (task: GenerationTaskState): ContextLimit | null => {
  if (task.status !== 'SUCCESS') return null;
  const metrics = task.result?.quality_metrics;
  if (metrics?.context_limited === true) {
    return {
      requested: metrics.requested_question_count ?? task.questionCount,
      generated: metrics.generated_question_count ?? null,
    };
  }
  if (task.contextLimited === true) {
    return { requested: task.questionCount, generated: task.generatedQuestionCount ?? null };
  }
  return null;
};

const numberParam = (params: Record<string, unknown> | null | undefined, key: string) =>
  typeof params?.[key] === 'number' ? (params[key] as number) : null;

/**
 * The progress line of a running task in the user's language, built from the
 * backend's progress code and parameters. Falls back to the plain `message`
 * when there is no code, for an unknown code (e.g. a newer backend) and for
 * `question_generated` without numeric `current`/`total`; returns `null` when
 * there is nothing to show.
 *
 * Literal `t()` calls per code, not a key built from the code: the i18n key
 * gate only sees literal keys.
 */
export const progressMessageOf = (task: GenerationTaskState, t: TFunction): string | null => {
  switch (task.messageCode) {
    case 'generation_started':
      return t('components.generationTasks.progress.generationStarted');
    case 'context_loaded':
      return t('components.generationTasks.progress.contextLoaded');
    case 'question_generated': {
      const current = numberParam(task.messageParams, 'current');
      const total = numberParam(task.messageParams, 'total');
      if (current === null || total === null) break;
      return t('components.generationTasks.progress.questionGenerated', { current, total });
    }
    case 'task_started':
      return t('contexts.generationTasks.started');
    case 'task_retrying':
      return t('contexts.generationTasks.retrying');
  }
  return task.message || null;
};
