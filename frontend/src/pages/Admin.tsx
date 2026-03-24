/**
 * Admin Page
 * Admin panel with RBAC-controlled tabs
 */

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
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
  const { t } = useTranslation();
  const isSuperuser = user?.is_superuser ?? false;
  const isAdmin = isSuperuser || hasRole(UserRole.ADMIN);

  const tabs: TabConfig[] = [
    { key: 'users', label: t('pages.admin.tabUsers'), visible: true },
    { key: 'institutions', label: t('pages.admin.tabInstitutions'), visible: isSuperuser },
    { key: 'roles', label: t('pages.admin.tabRoles'), visible: isSuperuser },
    { key: 'audit', label: t('pages.admin.tabAudit'), visible: isAdmin },
    { key: 'subscription', label: t('pages.admin.tabSubscription'), visible: isAdmin },
  ].filter((t): t is TabConfig => t.visible);

  const [activeTab, setActiveTab] = useState<AdminTab>(tabs[0]?.key ?? 'users');
  const effectiveTab = tabs.some(t => t.key === activeTab) ? activeTab : (tabs[0]?.key ?? 'users');

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">{t('pages.admin.title')}</h1>
        <p className="text-gray-600 mt-2">
          {t('pages.admin.subtitle')}
        </p>
      </div>

      <div className="flex gap-4 border-b border-gray-200">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              effectiveTab === tab.key
                ? 'border-primary-600 text-primary-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="card p-6">
        {effectiveTab === 'users' && <UserManagementPage />}
        {effectiveTab === 'institutions' && <InstitutionManagementPage />}
        {effectiveTab === 'roles' && <RoleManagementPage />}
        {effectiveTab === 'audit' && (
          <div className="text-center py-12">
            <p className="text-gray-500 text-lg">{t('pages.admin.auditPlaceholder')}</p>
          </div>
        )}
        {effectiveTab === 'subscription' && <SubscriptionTierOverview />}
      </div>
    </div>
  );
};
