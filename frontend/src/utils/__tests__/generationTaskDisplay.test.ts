import type { TFunction } from 'i18next';
import { progressMessageOf } from '../generationTaskDisplay';
import type { GenerationTaskState } from '../../types';

// Returns the key plus interpolation values, so the tests see which branch ran.
const t = ((key: string, params?: Record<string, unknown>) =>
  params ? `${key} ${JSON.stringify(params)}` : key) as unknown as TFunction;

const task = (overrides: Partial<GenerationTaskState>): GenerationTaskState => ({
  taskId: 'task-1',
  status: 'PROGRESS',
  progress: 10,
  message: null,
  topic: 'Heapsort',
  questionCount: 15,
  createdAt: '2026-09-29T08:00:00Z',
  result: null,
  ...overrides,
});

describe('progressMessageOf (TF-736)', () => {
  it('renders question_generated with its numbers', () => {
    expect(
      progressMessageOf(
        task({ messageCode: 'question_generated', messageParams: { current: 2, total: 6 } }),
        t
      )
    ).toBe('components.generationTasks.progress.questionGenerated {"current":2,"total":6}');
  });

  it('falls back to message when question_generated lacks numeric params', () => {
    expect(
      progressMessageOf(
        task({
          messageCode: 'question_generated',
          messageParams: { current: '2' },
          message: 'Frage 2 von 6',
        }),
        t
      )
    ).toBe('Frage 2 von 6');
    expect(progressMessageOf(task({ messageCode: 'question_generated' }), t)).toBeNull();
  });

  it('falls back to message for an unknown code and without any code', () => {
    expect(
      progressMessageOf(task({ messageCode: 'from_a_newer_backend', message: 'Text' }), t)
    ).toBe('Text');
    expect(progressMessageOf(task({ message: 'Alter Worker' }), t)).toBe('Alter Worker');
  });

  it('returns null for an unknown code without message', () => {
    expect(progressMessageOf(task({ messageCode: 'from_a_newer_backend' }), t)).toBeNull();
  });

  it.each([
    ['generation_started', 'components.generationTasks.progress.generationStarted'],
    ['context_loaded', 'components.generationTasks.progress.contextLoaded'],
    ['task_started', 'contexts.generationTasks.started'],
    ['task_retrying', 'contexts.generationTasks.retrying'],
  ])('renders %s', (code, key) => {
    expect(progressMessageOf(task({ messageCode: code }), t)).toBe(key);
  });
});
