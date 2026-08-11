/**
 * Org-Unit Assignment Dialog Component
 * Modal dialog for managing a user's org-unit (Abteilung/Team) memberships (TF-602)
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import AdminService, { UserDetailResponse } from '../../services/AdminService';
import { OrgUnitsService } from '../../services/orgUnitsService';
import { OrgUnitOut } from '../../types/orgUnit';
import { useAuth } from '../../contexts/AuthContext';

interface OrgUnitAssignmentDialogProps {
  userId: number | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

function orgUnitLabel(name: string, parentOrgUnitId: number | null, allOrgUnits: OrgUnitOut[]): string {
  if (parentOrgUnitId === null) return name;
  const parent = allOrgUnits.find(u => u.id === parentOrgUnitId);
  return parent ? `${name} (${parent.name})` : name;
}

export const OrgUnitAssignmentDialog: React.FC<OrgUnitAssignmentDialogProps> = ({
  userId,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { t } = useTranslation();
  const { user: currentUser } = useAuth();
  const [user, setUser] = useState<UserDetailResponse | null>(null);
  const [allOrgUnits, setAllOrgUnits] = useState<OrgUnitOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [roleInputs, setRoleInputs] = useState<Record<number, string>>({});

  const loadData = useCallback(async () => {
    if (!userId) return;

    try {
      setLoading(true);
      setError(null);

      const [userData, orgUnitsData] = await Promise.all([
        AdminService.getUser(userId),
        OrgUnitsService.list(),
      ]);

      setUser(userData);
      setAllOrgUnits(orgUnitsData.items);
    } catch (err) {
      console.error('[OrgUnitAssignmentDialog] loadData failed:', err);
      setError(err instanceof Error ? err.message : t('admin.orgUnitAssignment.failedLoad'));
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    if (isOpen && userId) {
      loadData();
    }
  }, [isOpen, userId, loadData]);

  const handleAssign = async (orgUnitId: number) => {
    if (!userId) return;

    try {
      setProcessing(true);
      setError(null);
      const role = roleInputs[orgUnitId]?.trim() || undefined;
      await OrgUnitsService.addMember(orgUnitId, userId, role);
      setRoleInputs(prev => ({ ...prev, [orgUnitId]: '' }));
      await loadData();
      onSuccess();
    } catch (err) {
      console.error('[OrgUnitAssignmentDialog] handleAssign failed:', { orgUnitId, userId, err });
      setError(err instanceof Error ? err.message : t('admin.orgUnitAssignment.failedAssign'));
    } finally {
      setProcessing(false);
    }
  };

  const handleRemove = async (orgUnitId: number) => {
    if (!userId) return;

    try {
      setProcessing(true);
      setError(null);
      await OrgUnitsService.removeMember(orgUnitId, userId);
      await loadData();
      onSuccess();
    } catch (err) {
      console.error('[OrgUnitAssignmentDialog] handleRemove failed:', { orgUnitId, userId, err });
      setError(err instanceof Error ? err.message : t('admin.orgUnitAssignment.failedRemove'));
    } finally {
      setProcessing(false);
    }
  };

  const isCrossInstitution =
    !!user && !!currentUser && user.institution_id !== currentUser.institution_id;

  const getAvailableOrgUnits = (): OrgUnitOut[] => {
    if (!user || isCrossInstitution) return [];
    return allOrgUnits.filter(unit => !user.org_units.some(m => m.org_unit_id === unit.id));
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        <div
          className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75"
          onClick={onClose}
        ></div>

        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-2xl sm:w-full">
          <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <div className="sm:flex sm:items-start">
              <div className="mt-3 text-center sm:mt-0 sm:text-left w-full">
                <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                  {t('admin.orgUnitAssignment.title')}
                </h3>

                {loading ? (
                  <div className="flex justify-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {error && (
                      <div
                        className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg text-sm"
                        data-testid="ouad-error"
                      >
                        {error}
                      </div>
                    )}

                    {user && (
                      <div className="bg-gray-50 p-4 rounded-lg">
                        <div className="text-sm">
                          <span className="font-medium text-gray-900">
                            {user.first_name} {user.last_name}
                          </span>
                          <span className="text-gray-500 ml-2">({user.email})</span>
                        </div>
                        <div className="text-sm text-gray-500 mt-1">{user.institution_name}</div>
                      </div>
                    )}

                    <div>
                      <h4 className="text-sm font-medium text-gray-900 mb-3">
                        {t('admin.orgUnitAssignment.currentOrgUnits')}
                      </h4>
                      {user && user.org_units.length > 0 ? (
                        <div className="space-y-2">
                          {user.org_units.map(membership => (
                            <div
                              key={membership.org_unit_id}
                              className="flex items-start justify-between p-3 bg-blue-50 border border-blue-200 rounded-lg"
                              data-testid={`ouad-current-${membership.org_unit_id}`}
                            >
                              <div className="flex-1">
                                <div className="flex items-center">
                                  <span className="font-medium text-gray-900">
                                    {orgUnitLabel(membership.name, membership.parent_org_unit_id, allOrgUnits)}
                                  </span>
                                </div>
                                {membership.role && (
                                  <p className="text-sm text-gray-600 mt-1">{membership.role}</p>
                                )}
                              </div>
                              {!isCrossInstitution && (
                                <button
                                  onClick={() => handleRemove(membership.org_unit_id)}
                                  disabled={processing}
                                  className="ml-4 text-red-600 hover:text-red-800 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                                  data-testid={`ouad-btn-remove-${membership.org_unit_id}`}
                                >
                                  {t('admin.orgUnitAssignment.btnRemove')}
                                </button>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-gray-500">{t('admin.orgUnitAssignment.noOrgUnits')}</p>
                      )}
                    </div>

                    <div>
                      <h4 className="text-sm font-medium text-gray-900 mb-3">
                        {t('admin.orgUnitAssignment.availableOrgUnits')}
                      </h4>
                      {isCrossInstitution ? (
                        <p
                          className="text-sm text-gray-500"
                          data-testid="ouad-cross-institution-notice"
                        >
                          {t('admin.orgUnitAssignment.crossInstitutionNotice')}
                        </p>
                      ) : getAvailableOrgUnits().length > 0 ? (
                        <div className="space-y-2">
                          {getAvailableOrgUnits().map(unit => (
                            <div
                              key={unit.id}
                              className="flex items-start justify-between p-3 bg-gray-50 border border-gray-200 rounded-lg"
                              data-testid={`ouad-available-${unit.id}`}
                            >
                              <div className="flex-1">
                                <div className="flex items-center">
                                  <span className="font-medium text-gray-900">
                                    {orgUnitLabel(unit.name, unit.parent_org_unit_id, allOrgUnits)}
                                  </span>
                                </div>
                                <input
                                  type="text"
                                  value={roleInputs[unit.id] ?? ''}
                                  onChange={e =>
                                    setRoleInputs(prev => ({ ...prev, [unit.id]: e.target.value }))
                                  }
                                  placeholder={t('admin.orgUnitAssignment.rolePlaceholder')}
                                  aria-label={t('admin.orgUnitAssignment.rolePlaceholder')}
                                  maxLength={50}
                                  className="mt-2 block w-full max-w-xs rounded-md border-gray-300 shadow-sm text-sm focus:border-blue-500 focus:ring-blue-500"
                                  data-testid={`ouad-role-input-${unit.id}`}
                                />
                              </div>
                              <button
                                onClick={() => handleAssign(unit.id)}
                                disabled={processing}
                                className="ml-4 text-blue-600 hover:text-blue-800 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                                data-testid={`ouad-btn-assign-${unit.id}`}
                              >
                                {t('admin.orgUnitAssignment.btnAssign')}
                              </button>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-gray-500">{t('admin.orgUnitAssignment.allOrgUnitsAssigned')}</p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
            <button
              type="button"
              onClick={onClose}
              disabled={processing}
              className="w-full inline-flex justify-center rounded-lg border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:w-auto sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t('admin.orgUnitAssignment.close')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
