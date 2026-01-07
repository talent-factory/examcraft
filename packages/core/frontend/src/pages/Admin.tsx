/**
 * Admin Page
 * Admin panel and settings
 */

import React, { useState } from 'react';
import { UserManagementPage } from '../components/admin/UserManagementPage';
import { InstitutionManagementPage } from '../components/admin/InstitutionManagementPage';
import RoleManagementPage from '../components/admin/RoleManagementPage';

export const Admin: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'users' | 'institutions' | 'roles'>('users');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">
          Admin-Panel
        </h1>
        <p className="text-gray-600 mt-2">
          Verwalte Benutzer, Einstellungen und Systemkonfiguration
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-4 border-b border-gray-200">
        <button
          type="button"
          onClick={() => setActiveTab('users')}
          className={`px-4 py-2 font-medium border-b-2 transition-colors ${activeTab === 'users'
            ? 'border-primary-600 text-primary-600'
            : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
        >
          Benutzer-Verwaltung
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('institutions')}
          className={`px-4 py-2 font-medium border-b-2 transition-colors ${activeTab === 'institutions'
            ? 'border-primary-600 text-primary-600'
            : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
        >
          Institutions
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('roles')}
          className={`px-4 py-2 font-medium border-b-2 transition-colors ${activeTab === 'roles'
            ? 'border-primary-600 text-primary-600'
            : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
        >
          Rollen & Berechtigungen
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'users' && (
        <div className="card p-6">
          <UserManagementPage />
        </div>
      )}

      {activeTab === 'institutions' && (
        <div className="card p-6">
          <InstitutionManagementPage />
        </div>
      )}

      {activeTab === 'roles' && (
        <div className="card p-6">
          <RoleManagementPage />
        </div>
      )}
    </div>
  );
};

