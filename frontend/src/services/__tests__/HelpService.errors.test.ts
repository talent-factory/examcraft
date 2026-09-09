import { AppError, isAppError } from '../../errors';
import { helpService } from '../HelpService';

/** The AppError a rejected call produced, or fail loudly. */
async function thrownBy(call: Promise<unknown>): Promise<AppError> {
  try {
    await call;
  } catch (err) {
    if (isAppError(err)) return err;
    throw new Error(`Erwartet wurde ein AppError, bekommen: ${String(err)}`);
  }
  throw new Error('Der Aufruf hat gar nicht abgelehnt');
}

describe('HelpService wirft AppError statt englischer Texte', () => {
  const originalFetch = global.fetch;
  afterEach(() => {
    global.fetch = originalFetch;
    jest.restoreAllMocks();
  });

  it('getStatus wirft AppError mit help.statusFailed', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 500 }) as unknown as typeof fetch;
    await expect(helpService.getStatus()).rejects.toMatchObject({
      code: 'help.statusFailed',
      status: 500,
    });
  });

  it('sendMessage behält den Status für die Rate-Limit-Auswertung', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 429 }) as unknown as typeof fetch;
    const err = await helpService.sendMessage('tok', 'Frage?', '/dashboard').catch((e) => e);
    expect(err).toBeInstanceOf(AppError);
    expect(err.code).toBe('help.messageFailed');
    expect(err.status).toBe(429);
  });

  it('sendMessage übernimmt help_rate_limit_exceeded vom Backend (TF-773)', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 429,
      json: async () => ({ detail: 'Limit erreicht', error_code: 'help_rate_limit_exceeded' }),
    }) as unknown as typeof fetch;

    expect((await thrownBy(helpService.sendMessage('tok', 'Frage?', '/dashboard'))).code).toBe(
      'help_rate_limit_exceeded',
    );
  });

  it('updateTrackStep übernimmt help_track_id_invalid vom Backend (TF-773)', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ detail: 'Ungültige Track-ID', error_code: 'help_track_id_invalid' }),
    }) as unknown as typeof fetch;

    expect(
      (await thrownBy(helpService.updateTrackStep('tok', 'unknown-track', 1, 3))).code,
    ).toBe('help_track_id_invalid');
  });

  it('macht auch aus einer Netzwerkablehnung einen AppError mit Operationscode', async () => {
    global.fetch = jest.fn().mockRejectedValue(new TypeError('Failed to fetch'));

    const err = await thrownBy(helpService.getOnboardingStatus('tok'));

    expect(err.code).toBe('help.onboardingStatusFailed');
    expect(err.status).toBeUndefined();
  });

  it('jede der neun Methoden ruft appErrorFromResponse mit ihrem eigenen Code auf', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({}) }) as unknown as typeof fetch;

    expect((await thrownBy(helpService.getStatus())).code).toBe('help.statusFailed');
    expect((await thrownBy(helpService.getOnboardingStatus('t'))).code).toBe(
      'help.onboardingStatusFailed',
    );
    expect((await thrownBy(helpService.completeOnboardingStep('t', 1))).code).toBe(
      'help.onboardingStepFailed',
    );
    expect((await thrownBy(helpService.skipOnboardingStep('t', 1))).code).toBe(
      'help.onboardingSkipFailed',
    );
    expect((await thrownBy(helpService.updateTrackStep('t', 'track-1', 1, 3))).code).toBe(
      'help_onboarding_track_step_failed',
    );
    expect((await thrownBy(helpService.getContextHint('t', '/dashboard'))).code).toBe(
      'help.contextHintFailed',
    );
    expect((await thrownBy(helpService.dismissHint('t', 1))).code).toBe('help.hintDismissFailed');
    expect((await thrownBy(helpService.sendMessage('t', 'Frage?', '/dashboard'))).code).toBe(
      'help.messageFailed',
    );
    expect(
      (await thrownBy(helpService.submitFeedback('t', { question: 'q', rating: 'up', route: '/x' }))).code,
    ).toBe('help.feedbackFailed');
  });
});
