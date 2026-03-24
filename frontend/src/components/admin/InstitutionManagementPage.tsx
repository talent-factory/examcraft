/**
 * Institution Management Page
 * Admin page for managing institutions and subscription tiers
 */

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { InstitutionList } from './InstitutionList';
import { InstitutionEditDialog } from './InstitutionEditDialog';
import { InstitutionCreateDialog } from './InstitutionCreateDialog';

export const InstitutionManagementPage: React.FC = () => {
  const { t } = useTranslation();
  const [editInstitutionId, setEditInstitutionId] = useState<number | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleEditInstitution = (institutionId: number) => {
    setEditInstitutionId(institutionId);
  };

  const handleCreateInstitution = () => {
    setShowCreateDialog(true);
  };

  const handleEditSuccess = () => {
    setRefreshKey((prev) => prev + 1);
  };

  const handleCreateSuccess = () => {
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
          <h1 className="text-3xl font-bold text-gray-900">{t('admin.institutionManagement.title')}</h1>
          <p className="mt-2 text-sm text-gray-600">
            {t('admin.institutionManagement.subtitle')}
          </p>
        </div>

        {/* Institution List */}
        <InstitutionList
          key={refreshKey}
          onEditInstitution={handleEditInstitution}
          onCreateInstitution={handleCreateInstitution}
          onRefresh={handleRefresh}
        />

        {/* Create Institution Dialog */}
        <InstitutionCreateDialog
          isOpen={showCreateDialog}
          onClose={() => setShowCreateDialog(false)}
          onSuccess={handleCreateSuccess}
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
