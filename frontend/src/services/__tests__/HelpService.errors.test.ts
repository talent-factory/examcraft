import { AppError } from '../../errors';
import { helpService } from '../HelpService';

describe('HelpService wirft AppError statt englischer Texte', () => {
  const originalFetch = global.fetch;
  afterEach(() => {
    global.fetch = originalFetch;
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
});
