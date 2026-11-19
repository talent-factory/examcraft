/**
 * Profile Page Component
 * Main profile page with tabs for view and edit (passwords live in Zitadel)
 */

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ProfileView } from './ProfileView';
import { ProfileEdit } from './ProfileEdit';

type ProfileTab = 'view' | 'edit';

export const ProfilePage: React.FC = () => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<ProfileTab>('view');

  const handleEditSuccess = () => {
    setActiveTab('view');
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Page Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">{t('profile.profilePage.title')}</h1>
        <p className="mt-2 text-gray-600">
          {t('profile.profilePage.subtitle')}
        </p>
      </div>

      {/* Tabs */}
      <div className="mb-6">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('view')}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'view'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              👤 {t('profile.profilePage.tabProfile')}
            </button>
            <button
              onClick={() => setActiveTab('edit')}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'edit'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              ✏️ {t('profile.profilePage.tabEdit')}
            </button>
          </nav>
        </div>
      </div>

      {/* Tab Content */}
      <div>
        {activeTab === 'view' && (
          <ProfileView onEdit={() => setActiveTab('edit')} />
        )}
        {activeTab === 'edit' && (
          <ProfileEdit
            onCancel={() => setActiveTab('view')}
            onSuccess={handleEditSuccess}
          />
        )}
      </div>
    </div>
  );
};
