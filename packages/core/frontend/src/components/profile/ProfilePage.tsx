/**
 * Profile Page Component
 * Main profile page with tabs for view, edit, and password change
 */

import React, { useState } from 'react';
import { ProfileView } from './ProfileView';
import { ProfileEdit } from './ProfileEdit';
import { PasswordChange } from './PasswordChange';

type ProfileTab = 'view' | 'edit' | 'password';

export const ProfilePage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ProfileTab>('view');

  const handleEditSuccess = () => {
    setActiveTab('view');
  };

  const handlePasswordSuccess = () => {
    setActiveTab('view');
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Page Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">My Profile</h1>
        <p className="mt-2 text-gray-600">
          Manage your account settings and preferences
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
              👤 Profile
            </button>
            <button
              onClick={() => setActiveTab('edit')}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'edit'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              ✏️ Edit Profile
            </button>
            <button
              onClick={() => setActiveTab('password')}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'password'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              🔒 Change Password
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
        {activeTab === 'password' && (
          <PasswordChange
            onCancel={() => setActiveTab('view')}
            onSuccess={handlePasswordSuccess}
          />
        )}
      </div>
    </div>
  );
};
