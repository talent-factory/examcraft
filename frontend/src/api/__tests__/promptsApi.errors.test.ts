/**
 * Error path of the Core `promptsApi` stub (TF-772 PR 4).
 *
 * Two things worth holding still here, and neither had a test before:
 *
 *   1. The Core refusal. `REACT_APP_DEPLOYMENT_MODE` is read once at module
 *      load, so each mode gets its own `jest.isolateModules` import — reusing
 *      the module would test whichever mode happened to load first.
 *   2. The 422 unpacking. It exists so `PromptEditor` can still name the field
 *      it objects to; a regression there is invisible in the UI until someone
 *      submits an invalid form, which is exactly the kind of thing that rots.
 */

import type { AppError } from '../../errors';

// Its own mock rather than `__mocks__/apiClient.ts`: that one has no `patch`,
// which `toggleActive` needs, and widening a shared mock for one suite invites
// the next suite to depend on the widening by accident.
jest.mock('../apiClient', () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    patch: jest.fn(),
    delete: jest.fn(),
  },
}));

type PromptsApi = typeof import('../promptsApi').promptsApi;
type ApiClientMock = { [K in 'get' | 'post' | 'put' | 'patch' | 'delete']: jest.Mock };

/** Load `promptsApi` fresh under a given deployment mode. */
function load(mode: string): { promptsApi: PromptsApi; apiClient: ApiClientMock } {
  const previous = process.env.REACT_APP_DEPLOYMENT_MODE;
  process.env.REACT_APP_DEPLOYMENT_MODE = mode;

  let loaded!: { promptsApi: PromptsApi; apiClient: ApiClientMock };
  jest.isolateModules(() => {
    loaded = {
      promptsApi: require('../promptsApi').promptsApi,
      apiClient: require('../apiClient').apiClient,
    };
  });

  process.env.REACT_APP_DEPLOYMENT_MODE = previous;
  return loaded;
}

function axiosError(status: number, data: unknown): unknown {
  return { isAxiosError: true, message: `Request failed with status code ${status}`, response: { status, data } };
}

/**
 * The AppError a rejected call produced, or fail loudly.
 *
 * Checked structurally, NOT with `isAppError`. `jest.isolateModules` gives the
 * freshly-required `promptsApi` its own copy of the `errors` module, so the
 * `AppError` class it throws is a different class object from the one this file
 * would import at the top — `instanceof` is false even though every field is
 * right. Same identity trap as the duplicated api/ modules in TF-660.
 */
async function thrownBy(call: Promise<unknown>): Promise<AppError> {
  try {
    await call;
  } catch (err) {
    if (err instanceof Error && err.name === 'AppError') return err as AppError;
    throw new Error(`Erwartet wurde ein AppError, bekommen: ${String(err)}`);
  }
  throw new Error('Der Aufruf hat gar nicht abgelehnt');
}

describe('promptsApi im Core-Modus', () => {
  it('lehnt jeden Aufruf mit prompts_not_available_in_core ab', async () => {
    const { promptsApi, apiClient } = load('core');

    const err = await thrownBy(promptsApi.listPrompts());

    expect(err.code).toBe('prompts_not_available_in_core');
    // Die Ablehnung ist eine Vorbedingung, kein Fehlschlag einer Anfrage —
    // es darf gar nichts gesendet worden sein.
    expect(apiClient.get).not.toHaveBeenCalled();
  });

  it('lehnt auch schreibende Aufrufe ab', async () => {
    const { promptsApi, apiClient } = load('core');

    const err = await thrownBy(promptsApi.deletePrompt('42'));

    expect(err.code).toBe('prompts_not_available_in_core');
    expect(apiClient.delete).not.toHaveBeenCalled();
  });
});

describe('promptsApi im Full-Modus', () => {
  it('gibt bei Erfolg die Daten zurück', async () => {
    const { promptsApi, apiClient } = load('full');
    apiClient.get.mockResolvedValue({ data: [{ id: '1' }] });

    await expect(promptsApi.listPrompts()).resolves.toEqual([{ id: '1' }]);
  });

  it('trägt den Fallbackcode der Operation, nicht einen gemeinsamen', async () => {
    const { promptsApi, apiClient } = load('full');
    apiClient.get.mockRejectedValue(axiosError(500, { detail: 'Failed to list prompts: boom' }));
    apiClient.delete.mockRejectedValue(axiosError(403, { detail: 'Kein Zugriff auf diesen Prompt' }));

    expect((await thrownBy(promptsApi.listPrompts())).code).toBe('prompts_list_failed');
    expect((await thrownBy(promptsApi.deletePrompt('7'))).code).toBe('prompts_delete_failed');
  });

  it('übernimmt einen registrierten error_code, sobald das Backend einen sendet', async () => {
    const { promptsApi, apiClient } = load('full');
    apiClient.get.mockRejectedValue(
      axiosError(404, { detail: 'Dokument nicht gefunden', error_code: 'documents_not_found' }),
    );

    expect((await thrownBy(promptsApi.getPrompt('7'))).code).toBe('documents_not_found');
  });

  it('packt ein 422 in Feld-für-Feld-Hinweise aus', async () => {
    const { promptsApi, apiClient } = load('full');
    apiClient.post.mockRejectedValue(
      axiosError(422, {
        detail: [
          { loc: ['body', 'name'], msg: 'field required' },
          { loc: ['body', 'content'], msg: 'ensure this value has at least 10 characters' },
        ],
      }),
    );

    const err = await thrownBy(promptsApi.createPrompt({} as never));

    expect(err.code).toBe('prompts_validation_failed');
    // Der Text landet als Interpolationswert, nicht als roher `detail` —
    // translateError rendert `detail` nie.
    expect(err.params).toEqual({
      issues: 'name: field required, content: ensure this value has at least 10 characters',
    });
  });

  it('gibt dem use_case-Muster seinen eigenen Code', async () => {
    const { promptsApi, apiClient } = load('full');
    apiClient.put.mockRejectedValue(
      axiosError(422, {
        detail: [{ loc: ['body', 'use_case'], msg: 'string does not match pattern "^question_"' }],
      }),
    );

    expect((await thrownBy(promptsApi.updatePrompt('7', {}))).code).toBe('prompts_use_case_invalid');
  });

  it('behandelt ein 422 mit String-detail wie jeden anderen Fehlschlag', async () => {
    const { promptsApi, apiClient } = load('full');
    // `prompts.py` wirft auch `HTTPException(422, detail=str(e))` — daraus ist
    // kein Feld zu lesen, also bleibt es beim Operations-Fallback.
    apiClient.post.mockRejectedValue(axiosError(422, { detail: 'Ungültige Vorlage' }));

    expect((await thrownBy(promptsApi.createPrompt({} as never))).code).toBe('prompts_create_failed');
  });

  it('behandelt eine Netzwerkablehnung ohne response', async () => {
    const { promptsApi, apiClient } = load('full');
    apiClient.get.mockRejectedValue(new Error('Network Error'));

    const err = await thrownBy(promptsApi.getUsageLogs('7'));

    expect(err.code).toBe('prompts_usage_load_failed');
    expect(err.status).toBeUndefined();
  });
});
