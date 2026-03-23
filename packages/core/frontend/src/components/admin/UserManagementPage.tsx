/**
 * User Management Page
 * Admin page for managing users, roles, and permissions
 */

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { UserList } from './UserList';
import { UserEditDialog } from './UserEditDialog';
import { RoleAssignmentDialog } from './RoleAssignmentDialog';
import { useAuth } from '../../contexts/AuthContext';

export const UserManagementPage: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const isAdmin = user?.is_superuser || user?.roles?.some(r => r.name === 'admin') || false;
  const [editUserId, setEditUserId] = useState<number | null>(null);
  const [manageRolesUserId, setManageRolesUserId] = useState<number | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleEditUser = (userId: number) => {
    if (!isAdmin) return;
    setEditUserId(userId);
  };

  const handleManageRoles = (userId: number) => {
    if (!isAdmin) return;
    setManageRolesUserId(userId);
  };

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1);
  };

  const handleEditSuccess = () => {
    handleRefresh();
  };

  const handleRolesSuccess = () => {
    handleRefresh();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">{t('admin.userManagement.title')}</h1>
          <p className="mt-2 text-sm text-gray-600">
            {t('admin.userManagement.subtitle')}
          </p>
        </div>

        {/* User List */}
        <UserList
          key={refreshKey}
          onEditUser={handleEditUser}
          onManageRoles={handleManageRoles}
          onRefresh={handleRefresh}
          canEdit={isAdmin}
        />

        {/* Edit User Dialog (admin/superuser only) */}
        {isAdmin && (
          <UserEditDialog
            userId={editUserId}
            isOpen={editUserId !== null}
            onClose={() => setEditUserId(null)}
            onSuccess={handleEditSuccess}
          />
        )}

        {/* Role Assignment Dialog (admin/superuser only) */}
        {isAdmin && (
          <RoleAssignmentDialog
            userId={manageRolesUserId}
            isOpen={manageRolesUserId !== null}
            onClose={() => setManageRolesUserId(null)}
            onSuccess={handleRolesSuccess}
          />
        )}
      </div>
    </div>
  );
};
