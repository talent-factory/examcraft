import { OrgUnitsService } from '../orgUnitsService';
import * as httpClient from '../httpClient';

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
});
