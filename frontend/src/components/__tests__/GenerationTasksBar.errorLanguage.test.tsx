/**
 * TF-967: a failed generation shows its error in the UI language. The backend
 * sends `error_code` next to a German `error` text; the panel must render the
 * code through `errorMessageOf`, never the German sentence, and must follow a
 * language switch for an error that is already on screen.
 *
 * Rendered with the real i18next against the shipped locales: the global
 * react-i18next mock in setupTests.ts always answers in German, which is
 * exactly the failure this test has to be able to see.
 */
import React from 'react';
import { act, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import i18n from '../../i18n';
import frLocale from '../../locales/fr/translation.json';
import GenerationTasksBar from '../GenerationTasksBar';
import type { GenerationTaskState } from '../../types';

// Hoisted above the imports by babel-plugin-jest-hoist.
jest.unmock('react-i18next');

const mockUseGenerationTasks = jest.fn();
jest.mock('../../contexts/GenerationTasksContext', () => ({
  useGenerationTasks: () => mockUseGenerationTasks(),
}));

const GERMAN_BACKEND_TEXT = 'Verarbeitung fehlgeschlagen. Bitte versuch es erneut.';

const failedTask = (overrides: Partial<GenerationTaskState>): GenerationTaskState => ({
  taskId: 'task-failed',
  status: 'FAILURE',
  progress: 0,
  message: GERMAN_BACKEND_TEXT,
  topic: 'Heapsort',
  questionCount: 5,
  createdAt: new Date().toISOString(),
  result: null,
  ...overrides,
});

const renderWith = (task: GenerationTaskState) => {
  mockUseGenerationTasks.mockReturnValue({
    activeTasks: [],
    completedTasks: [task],
    dismissTask: jest.fn(),
    retryTask: jest.fn(),
  });
  return render(
    <MemoryRouter>
      <ThemeProvider theme={createTheme()}>
        <GenerationTasksBar />
      </ThemeProvider>
    </MemoryRouter>
  );
};

const fr = frLocale.errors;

// The six codes of TF-967, with the params the backend sends.
const CASES: Array<[string, Record<string, number> | null, string]> = [
  ['rag_task_failed', null, fr.rag_task_failed],
  ['rag_task_no_context', null, fr.rag_task_no_context],
  ['rag_task_unknown_question_type', null, fr.rag_task_unknown_question_type],
  ['rag_task_status_unavailable', null, fr.rag_task_status_unavailable],
  ['rag_task_pending_timeout', { seconds: 120 }, fr.rag_task_pending_timeout.replace('{{seconds}}', '120')],
  ['rag_task_stream_error', null, fr.rag_task_stream_error],
];

describe('GenerationTasksBar: Fehlertext in der UI-Sprache (TF-967)', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('fr');
  });

  afterAll(async () => {
    await i18n.changeLanguage('de');
  });

  it.each(CASES)('rendert %s auf Französisch statt des deutschen Backend-Texts', (code, params, expected) => {
    renderWith(failedTask({ errorCode: code, errorParams: params }));

    expect(screen.getByText(expected)).toBeInTheDocument();
    expect(screen.queryByText(GERMAN_BACKEND_TEXT)).not.toBeInTheDocument();
  });

  it('wechselt einen bereits angezeigten Fehler mit der Sprache', async () => {
    await i18n.changeLanguage('de');
    renderWith(failedTask({ errorCode: 'rag_task_no_context', message: 'Rohtext vom Backend' }));

    const de = i18n.t('errors.rag_task_no_context', { lng: 'de' });
    expect(screen.getByText(de)).toBeInTheDocument();

    await act(async () => {
      await i18n.changeLanguage('fr');
    });

    expect(screen.getByText(fr.rag_task_no_context)).toBeInTheDocument();
    expect(screen.queryByText(de)).not.toBeInTheDocument();
  });

  it('zeigt bei einem unbekannten Code den Text aus `error`', () => {
    renderWith(failedTask({ errorCode: 'rag_task_from_a_newer_backend', message: 'Texte du backend' }));

    expect(screen.getByText('Texte du backend')).toBeInTheDocument();
  });

  it('zeigt ohne Code und ohne Text den Fallback-Schlüssel des Panels', () => {
    renderWith(failedTask({ errorCode: null, message: null }));

    expect(
      screen.getByText(i18n.t('components.generationTasks.errorOccurred', { lng: 'fr' }))
    ).toBeInTheDocument();
    // Sanity: the fallback really is French, not an untranslated key.
    expect(i18n.t('components.generationTasks.errorOccurred', { lng: 'fr' })).not.toMatch(
      /components\.generationTasks/
    );
  });
});
