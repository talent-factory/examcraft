import { OrgUnitsService } from '../orgUnitsService';
import * as httpClient from '../httpClient';
import { ApiError } from '../submissionsService';
import { AppError, isAppError } from '../../errors';

jest.mock('../httpClient');
const mockedHttpClient = httpClient as jest.Mocked<typeof httpClient>;

describe('OrgUnitsService', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it('list() calls getJson with the org-units root path', async () => {
    mockedHttpClient.getJson.mockResolvedValue({ items: [] });

    const result = await OrgUnitsService.list();

    expect(mockedHttpClient.getJson).toHaveBeenCalledWith('/api/v1/org-units');
    expect(result).toEqual({ items: [] });
  });

  it('mine() calls getJson with the org-units mine path (TF-620)', async () => {
    mockedHttpClient.getJson.mockResolvedValue({ items: [] });

    const result = await OrgUnitsService.mine();

    expect(mockedHttpClient.getJson).toHaveBeenCalledWith('/api/v1/org-units/mine');
    expect(result).toEqual({ items: [] });
  });

  it('create() posts the payload to the org-units root path', async () => {
    const created = {
      id: 1,
      parent_org_unit_id: null,
      unit_type: 'abteilung',
      name: 'Informatik',
      descendant_count: 0,
      created_at: '2026-08-07T00:00:00Z',
      updated_at: '2026-08-07T00:00:00Z',
    };
    mockedHttpClient.postJson.mockResolvedValue(created);

    const result = await OrgUnitsService.create({
      unit_type: 'abteilung',
      name: 'Informatik',
      parent_org_unit_id: null,
    });

    expect(mockedHttpClient.postJson).toHaveBeenCalledWith('/api/v1/org-units', {
      unit_type: 'abteilung',
      name: 'Informatik',
      parent_org_unit_id: null,
    });
    expect(result).toEqual(created);
  });

  it('update() patches the org-unit id path', async () => {
    mockedHttpClient.patchJson.mockResolvedValue({} as never);

    await OrgUnitsService.update(7, { name: 'Neuer Name' });

    expect(mockedHttpClient.patchJson).toHaveBeenCalledWith('/api/v1/org-units/7', {
      name: 'Neuer Name',
    });
  });

  it('remove() calls deleteVoid with the org-unit id in the path', async () => {
    mockedHttpClient.deleteVoid.mockResolvedValue(undefined);

    await OrgUnitsService.remove(42);

    expect(mockedHttpClient.deleteVoid).toHaveBeenCalledWith('/api/v1/org-units/42');
  });

  /**
   * TF-772: the error path, which had no coverage at all.
   *
   * `OrgUnitsService` keeps using the shared `httpClient` — converting that
   * helper would change the error type under six services outside this package
   * — and turns its `ApiError` into an `AppError` one layer up. These tests
   * pin the part of that which is easy to get wrong later: a code per
   * operation, and no backend text on the way out.
   */
  describe('Fehlerpfad', () => {
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

    const apiError = (message: string, status = 409): ApiError =>
      new ApiError({ kind: 'conflict', status, message });

    it('trägt je Operation einen eigenen Code', async () => {
      mockedHttpClient.getJson.mockRejectedValue(apiError('OrgUnit nicht gefunden', 404));
      mockedHttpClient.postJson.mockRejectedValue(apiError('Name bereits vergeben'));
      mockedHttpClient.patchJson.mockRejectedValue(apiError('Zyklus in der Hierarchie'));
      mockedHttpClient.deleteVoid.mockRejectedValue(apiError('OrgUnit hat noch Mitglieder'));

      expect((await thrownBy(OrgUnitsService.list())).code).toBe('org_units_list_failed');
      expect((await thrownBy(OrgUnitsService.create({} as never))).code).toBe(
        'org_units_create_failed',
      );
      expect((await thrownBy(OrgUnitsService.update(7, {}))).code).toBe(
        'org_units_update_failed',
      );
      expect((await thrownBy(OrgUnitsService.remove(7))).code).toBe('org_units_delete_failed');
      expect((await thrownBy(OrgUnitsService.addMember(7, 1))).code).toBe(
        'org_units_add_member_failed',
      );
      expect((await thrownBy(OrgUnitsService.removeMember(7, 1))).code).toBe(
        'org_units_remove_member_failed',
      );
    });

    it('teilt einen Code zwischen list() und mine()', async () => {
      mockedHttpClient.getJson.mockRejectedValue(apiError('Kein Zugriff', 403));

      expect((await thrownBy(OrgUnitsService.mine())).code).toBe('org_units_list_failed');
    });

    it('behält die Backend-Meldung als detail, nicht als Code', async () => {
      mockedHttpClient.deleteVoid.mockRejectedValue(
        apiError('OrgUnit hat noch Mitglieder und kann nicht gelöscht werden'),
      );

      const err = await thrownBy(OrgUnitsService.remove(7));

      expect(err.detail).toBe('OrgUnit hat noch Mitglieder und kann nicht gelöscht werden');
      expect(err.status).toBe(409);
    });

    it('übernimmt einen echten org_units_*-Code des Backends (TF-773)', async () => {
      // `org_units.py` sendet seit TF-773 spezifische Codes (siehe
      // errors/codes/orgUnits.ts) — der generische Operations-Fallback tritt
      // nur noch bei Netzwerkfehlern oder unregistrierten Codes zurück.
      mockedHttpClient.deleteVoid.mockRejectedValue(
        new ApiError({
          kind: 'conflict',
          status: 409,
          message: 'Diese Organisationseinheit hat noch Mitglieder.',
          errorCode: 'org_units_delete_conflict',
        }),
      );

      expect((await thrownBy(OrgUnitsService.remove(7))).code).toBe('org_units_delete_conflict');
    });
  });
});
