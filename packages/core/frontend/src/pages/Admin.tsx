/**
 * Admin Page
 * Admin panel with RBAC-controlled tabs
 */

import React, { useState } from 'react';
import { UserManagementPage } from '../components/admin/UserManagementPage';
import { InstitutionManagementPage } from '../components/admin/InstitutionManagementPage';
import RoleManagementPage from '../components/admin/RoleManagementPage';
import SubscriptionTierOverview from '../components/admin/SubscriptionTierOverview';
import { useAuth } from '../contexts/AuthContext';
import { UserRole } from '../types/auth';

type AdminTab = 'users' | 'institutions' | 'roles' | 'audit' | 'subscription';

interface TabConfig {
  key: AdminTab;
  label: string;
  visible: boolean;
}

export const Admin: React.FC = () => {
  const { user, hasRole } = useAuth();
  const isSuperuser = user?.is_superuser ?? false;
  const isAdmin = isSuperuser || hasRole(UserRole.ADMIN);

  const tabs: TabConfig[] = [
    { key: 'users', label: 'Benutzer-Verwaltung', visible: true },
    { key: 'institutions', label: 'Institutionen', visible: isSuperuser },
    { key: 'roles', label: 'Rollen & Berechtigungen', visible: isSuperuser },
    { key: 'audit', label: 'Audit Logs', visible: isAdmin },
    { key: 'subscription', label: 'Abonnement', visible: isAdmin },
  ].filter((t): t is TabConfig => t.visible);

  const [activeTab, setActiveTab] = useState<AdminTab>(tabs[0]?.key ?? 'users');

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Admin-Panel</h1>
        <p className="text-gray-600 mt-2">
          Verwalte Benutzer, Einstellungen und Systemkonfiguration
        </p>
      </div>

      <div className="flex gap-4 border-b border-gray-200">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              activeTab === tab.key
                ? 'border-primary-600 text-primary-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="card p-6">
        {activeTab === 'users' && <UserManagementPage />}
        {activeTab === 'institutions' && <InstitutionManagementPage />}
        {activeTab === 'roles' && <RoleManagementPage />}
        {activeTab === 'audit' && (
          <div className="text-center py-12">
            <p className="text-gray-500 text-lg">Audit Logs — Demnachst verfugbar</p>
          </div>
        )}
        {activeTab === 'subscription' && <SubscriptionTierOverview />}
      </div>
    </div>
  );
};
