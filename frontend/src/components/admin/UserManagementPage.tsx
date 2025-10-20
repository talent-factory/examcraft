/**
 * User Management Page
 * Admin page for managing users, roles, and permissions
 */

import React, { useState } from 'react';
import { UserList } from './UserList';
import { UserEditDialog } from './UserEditDialog';
import { RoleAssignmentDialog } from './RoleAssignmentDialog';

export const UserManagementPage: React.FC = () => {
  const [editUserId, setEditUserId] = useState<number | null>(null);
  const [manageRolesUserId, setManageRolesUserId] = useState<number | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleEditUser = (userId: number) => {
    setEditUserId(userId);
  };

  const handleManageRoles = (userId: number) => {
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
          <h1 className="text-3xl font-bold text-gray-900">User Management</h1>
          <p className="mt-2 text-sm text-gray-600">
            Manage users, assign roles, and control access permissions
          </p>
        </div>

        {/* User List */}
        <UserList
          key={refreshKey}
          onEditUser={handleEditUser}
          onManageRoles={handleManageRoles}
          onRefresh={handleRefresh}
        />

        {/* Edit User Dialog */}
        <UserEditDialog
          userId={editUserId}
          isOpen={editUserId !== null}
          onClose={() => setEditUserId(null)}
          onSuccess={handleEditSuccess}
        />

        {/* Role Assignment Dialog */}
        <RoleAssignmentDialog
          userId={manageRolesUserId}
          isOpen={manageRolesUserId !== null}
          onClose={() => setManageRolesUserId(null)}
          onSuccess={handleRolesSuccess}
        />
      </div>
    </div>
  );
};

