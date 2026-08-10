/**
 * Tests for rolesService
 */

import { RolesService } from '../rolesService';
import * as httpClient from '../httpClient';

jest.mock('../httpClient');

const mockedGetJson = httpClient.getJson as jest.MockedFunction<typeof httpClient.getJson>;
const mockedPostJson = httpClient.postJson as jest.MockedFunction<typeof httpClient.postJson>;
const mockedPatchJson = httpClient.patchJson as jest.MockedFunction<typeof httpClient.patchJson>;
const mockedDeleteVoid = httpClient.deleteVoid as jest.MockedFunction<typeof httpClient.deleteVoid>;

describe('RolesService', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it('list() calls GET /api/admin/roles', async () => {
    const mockRoles = [
      {
        id: 1,
        name: 'admin',
        display_name: 'Administrator',
        description: 'System administrator',
        permissions: ['manage_users', 'manage_roles'],
        is_system_role: true,
        created_at: '2026-01-01T00:00:00Z',
      },
    ];
    mockedGetJson.mockResolvedValue(mockRoles);

    const result = await RolesService.list();

    expect(mockedGetJson).toHaveBeenCalledWith('/api/admin/roles');
    expect(result).toEqual(mockRoles);
  });

  it('listPermissions() calls GET /api/admin/permissions', async () => {
    const mockPermissions = [
      {
        key: 'manage_users',
        label: 'Manage users',
        category: 'users',
      },
    ];
    mockedGetJson.mockResolvedValue(mockPermissions);

    const result = await RolesService.listPermissions();

    expect(mockedGetJson).toHaveBeenCalledWith('/api/admin/permissions');
    expect(result).toEqual(mockPermissions);
  });

  it('create() calls POST /api/admin/roles with payload', async () => {
    const payload = {
      name: 'viewer',
      display_name: 'Viewer',
      description: 'Read-only access',
      permissions: ['view_documents'],
    };
    const mockResponse = {
      id: 3,
      ...payload,
      is_system_role: false,
      created_at: '2026-01-02T00:00:00Z',
    };
    mockedPostJson.mockResolvedValue(mockResponse);

    const result = await RolesService.create(payload);

    expect(mockedPostJson).toHaveBeenCalledWith('/api/admin/roles', payload);
    expect(result).toEqual(mockResponse);
  });

  it('update() calls PATCH /api/admin/roles/:id with payload', async () => {
    const payload = {
      permissions: ['manage_org_units'],
    };
    const mockResponse = {
      id: 42,
      name: 'custom_role',
      display_name: 'Custom Role',
      description: 'Custom role',
      permissions: ['manage_org_units'],
      is_system_role: false,
      created_at: '2026-01-01T00:00:00Z',
    };
    mockedPatchJson.mockResolvedValue(mockResponse);

    await RolesService.update(42, payload);

    expect(mockedPatchJson).toHaveBeenCalledWith('/api/admin/roles/42', payload);
  });

  it('remove() calls DELETE /api/admin/roles/:id', async () => {
    mockedDeleteVoid.mockResolvedValue(undefined);

    await RolesService.remove(42);

    expect(mockedDeleteVoid).toHaveBeenCalledWith('/api/admin/roles/42');
  });
});
