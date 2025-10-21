/**
 * Role Assignment Dialog Component
 * Modal dialog for managing user roles
 */

import React, { useState, useEffect } from 'react';
import AdminService, { UserDetailResponse } from '../../services/AdminService';
import { Role } from '../../types/auth';

interface RoleAssignmentDialogProps {
  userId: number | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const RoleAssignmentDialog: React.FC<RoleAssignmentDialogProps> = ({
  userId,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [user, setUser] = useState<UserDetailResponse | null>(null);
  const [allRoles, setAllRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);

  useEffect(() => {
    if (isOpen && userId) {
      loadData();
    }
  }, [isOpen, userId]);

  const loadData = async () => {
    if (!userId) return;

    try {
      setLoading(true);
      setError(null);
      
      const [userData, rolesData] = await Promise.all([
        AdminService.getUser(userId),
        AdminService.listRoles(),
      ]);
      
      setUser(userData);
      setAllRoles(rolesData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleAssignRole = async (roleId: number) => {
    if (!userId) return;

    try {
      setProcessing(true);
      setError(null);
      await AdminService.assignRole(userId, roleId);
      await loadData();
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to assign role');
    } finally {
      setProcessing(false);
    }
  };

  const handleRemoveRole = async (roleId: number) => {
    if (!userId) return;

    try {
      setProcessing(true);
      setError(null);
      await AdminService.removeRole(userId, roleId);
      await loadData();
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove role');
    } finally {
      setProcessing(false);
    }
  };

  const hasRole = (roleId: number): boolean => {
    return user?.roles.some(r => r.id === roleId) || false;
  };

  const getAvailableRoles = (): Role[] => {
    if (!user) return [];
    return allRoles.filter(role => !user.roles.some(r => r.id === role.id));
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        {/* Background overlay */}
        <div
          className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75"
          onClick={onClose}
        ></div>

        {/* Modal panel */}
        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-2xl sm:w-full">
          <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <div className="sm:flex sm:items-start">
              <div className="mt-3 text-center sm:mt-0 sm:text-left w-full">
                <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                  Manage User Roles
                </h3>

                {loading ? (
                  <div className="flex justify-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {/* Error Message */}
                    {error && (
                      <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg text-sm">
                        {error}
                      </div>
                    )}

                    {/* User Info */}
                    {user && (
                      <div className="bg-gray-50 p-4 rounded-lg">
                        <div className="text-sm">
                          <span className="font-medium text-gray-900">
                            {user.first_name} {user.last_name}
                          </span>
                          <span className="text-gray-500 ml-2">({user.email})</span>
                        </div>
                        <div className="text-sm text-gray-500 mt-1">
                          {user.institution_name}
                        </div>
                      </div>
                    )}

                    {/* Current Roles */}
                    <div>
                      <h4 className="text-sm font-medium text-gray-900 mb-3">Current Roles</h4>
                      {user && user.roles.length > 0 ? (
                        <div className="space-y-2">
                          {user.roles.map((role) => (
                            <div
                              key={role.id}
                              className="flex items-start justify-between p-3 bg-blue-50 border border-blue-200 rounded-lg"
                            >
                              <div className="flex-1">
                                <div className="flex items-center">
                                  <span className="font-medium text-gray-900">{role.display_name}</span>
                                  {role.is_system_role && (
                                    <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                                      System
                                    </span>
                                  )}
                                </div>
                                {role.description && (
                                  <p className="text-sm text-gray-600 mt-1">{role.description}</p>
                                )}
                                <div className="mt-2">
                                  <button
                                    onClick={() => setSelectedRole(selectedRole?.id === role.id ? null : role)}
                                    className="text-xs text-blue-600 hover:text-blue-800"
                                  >
                                    {selectedRole?.id === role.id ? 'Hide' : 'Show'} Permissions
                                  </button>
                                </div>
                                {selectedRole?.id === role.id && (
                                  <div className="mt-2 p-2 bg-white rounded border border-blue-100">
                                    <div className="flex flex-wrap gap-1">
                                      {role.permissions.map((perm, idx) => (
                                        <span
                                          key={idx}
                                          className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700"
                                        >
                                          {perm}
                                        </span>
                                      ))}
                                    </div>
                                  </div>
                                )}
                              </div>
                              <button
                                onClick={() => handleRemoveRole(role.id)}
                                disabled={processing || user.roles.length === 1}
                                className="ml-4 text-red-600 hover:text-red-800 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                                title={user.roles.length === 1 ? 'Cannot remove last role' : 'Remove role'}
                              >
                                Remove
                              </button>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-gray-500">No roles assigned</p>
                      )}
                    </div>

                    {/* Available Roles */}
                    <div>
                      <h4 className="text-sm font-medium text-gray-900 mb-3">Available Roles</h4>
                      {getAvailableRoles().length > 0 ? (
                        <div className="space-y-2">
                          {getAvailableRoles().map((role) => (
                            <div
                              key={role.id}
                              className="flex items-start justify-between p-3 bg-gray-50 border border-gray-200 rounded-lg"
                            >
                              <div className="flex-1">
                                <div className="flex items-center">
                                  <span className="font-medium text-gray-900">{role.display_name}</span>
                                  {role.is_system_role && (
                                    <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                                      System
                                    </span>
                                  )}
                                </div>
                                {role.description && (
                                  <p className="text-sm text-gray-600 mt-1">{role.description}</p>
                                )}
                              </div>
                              <button
                                onClick={() => handleAssignRole(role.id)}
                                disabled={processing}
                                className="ml-4 text-blue-600 hover:text-blue-800 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                              >
                                Assign
                              </button>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-gray-500">All roles assigned</p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
            <button
              type="button"
              onClick={onClose}
              disabled={processing}
              className="w-full inline-flex justify-center rounded-lg border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:w-auto sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

