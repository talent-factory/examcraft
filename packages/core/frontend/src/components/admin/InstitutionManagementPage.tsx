/**
 * Institution Management Page
 * Admin page for managing institutions and subscription tiers
 */

import React, { useState } from 'react';
import { InstitutionList } from './InstitutionList';
import { InstitutionEditDialog } from './InstitutionEditDialog';

export const InstitutionManagementPage: React.FC = () => {
  const [editInstitutionId, setEditInstitutionId] = useState<number | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleEditInstitution = (institutionId: number) => {
    setEditInstitutionId(institutionId);
  };

  const handleEditSuccess = () => {
    setRefreshKey((prev) => prev + 1);
  };

  const handleRefresh = () => {
    setRefreshKey((prev) => prev + 1);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Institution Management</h1>
          <p className="mt-2 text-sm text-gray-600">
            Manage institutions and subscription tiers
          </p>
        </div>

        {/* Institution List */}
        <InstitutionList
          key={refreshKey}
          onEditInstitution={handleEditInstitution}
          onRefresh={handleRefresh}
        />

        {/* Edit Institution Dialog */}
        <InstitutionEditDialog
          institutionId={editInstitutionId}
          isOpen={editInstitutionId !== null}
          onClose={() => setEditInstitutionId(null)}
          onSuccess={handleEditSuccess}
        />
      </div>
    </div>
  );
};

