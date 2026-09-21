/**
 * Tests fuer `AppErrorBoundary` (TF-866): faengt Render-Fehler ab, meldet
 * sie ueber `utils/errorReporting` statt (bisher) Sentry, und zeigt eine
 * Fallback-UI mit funktionierendem Retry.
 *
 * Mockt react-i18next (t gibt den Key zurueck) analog zu den bestehenden
 * Component-Tests (siehe `DocumentLibrary.tags-menu.test.tsx`).
 */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { AppErrorBoundary } from '../ErrorBoundary';
import { reportClientError } from '../../utils/errorReporting';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'de' },
  }),
}));

jest.mock('../../utils/errorReporting', () => ({
  reportClientError: jest.fn(),
}));

const mockReportClientError = reportClientError as jest.MockedFunction<typeof reportClientError>;

/** Wirft beim ersten Render, danach nicht mehr — testet den Retry-Pfad. */
let shouldThrow = true;
function FlakyChild() {
  if (shouldThrow) {
    throw new Error('kaboom');
  }
  return <div>recovered</div>;
}

describe('AppErrorBoundary', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    shouldThrow = true;
    // React logt gefangene Fehler zusaetzlich per console.error — nicht
    // Teil dessen, was dieser Test verifiziert.
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    (console.error as jest.Mock).mockRestore();
  });

  it('rendert die Kinder unveraendert, wenn kein Fehler auftritt', () => {
    render(
      <AppErrorBoundary>
        <div>alles gut</div>
      </AppErrorBoundary>
    );

    expect(screen.getByText('alles gut')).toBeInTheDocument();
    expect(mockReportClientError).not.toHaveBeenCalled();
  });

  it('faengt einen Render-Fehler ab und zeigt die Fallback-UI', () => {
    render(
      <AppErrorBoundary>
        <FlakyChild />
      </AppErrorBoundary>
    );

    expect(screen.getByText('components.errorBoundary.title')).toBeInTheDocument();
    expect(screen.getByText('components.errorBoundary.retry')).toBeInTheDocument();
  });

  it('meldet den gefangenen Fehler inkl. componentStack/userAgent an errorReporting', () => {
    render(
      <AppErrorBoundary>
        <FlakyChild />
      </AppErrorBoundary>
    );

    expect(mockReportClientError).toHaveBeenCalledTimes(1);
    const reported = mockReportClientError.mock.calls[0][0];
    expect(reported.message).toBe('kaboom');
    expect(reported.userAgent).toBe(navigator.userAgent);
    expect(reported.url).toBe(window.location.href);
    expect(reported.componentStack).toEqual(expect.stringContaining('FlakyChild'));
  });

  it('setzt sich ueber den Retry-Button zurueck und rendert erholte Kinder', () => {
    render(
      <AppErrorBoundary>
        <FlakyChild />
      </AppErrorBoundary>
    );

    expect(screen.getByText('components.errorBoundary.title')).toBeInTheDocument();

    shouldThrow = false;
    fireEvent.click(screen.getByText('components.errorBoundary.retry'));

    expect(screen.getByText('recovered')).toBeInTheDocument();
  });

  it('bricht nicht ab, wenn der onError-Callback selbst wirft', () => {
    mockReportClientError.mockImplementationOnce(() => {
      throw new Error('reporter kaputt');
    });

    render(
      <AppErrorBoundary>
        <FlakyChild />
      </AppErrorBoundary>
    );

    expect(screen.getByText('components.errorBoundary.title')).toBeInTheDocument();
  });
});
