/**
 * Institution List Component
 * Displays all institutions in a table with subscription tier management
 */

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import AdminService from '../../services/AdminService';
import { Institution } from '../../types/auth';

interface InstitutionListProps {
  onEditInstitution: (institutionId: number) => void;
  onCreateInstitution: () => void;
  onRefresh?: () => void;
}

export const InstitutionList: React.FC<InstitutionListProps> = ({
  onEditInstitution,
  onCreateInstitution,
  onRefresh,
}) => {
  const { t } = useTranslation();
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadInstitutions();
  }, []);

  const loadInstitutions = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await AdminService.listInstitutions();
      setInstitutions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.institutionList.failedLoad'));
    } finally {
      setLoading(false);
    }
  };

  const getTierBadgeColor = (tier: string): string => {
    switch (tier) {
      case 'free':
        return 'bg-gray-100 text-gray-800';
      case 'starter':
        return 'bg-blue-100 text-blue-800';
      case 'professional':
        return 'bg-purple-100 text-purple-800';
      case 'enterprise':
        return 'bg-orange-100 text-orange-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getTierDisplayName = (tier: string): string => {
    switch (tier) {
      case 'free':
        return t('admin.institutionList.tierFree');
      case 'starter':
        return t('admin.institutionList.tierStarter');
      case 'professional':
        return t('admin.institutionList.tierProfessional');
      case 'enterprise':
        return t('admin.institutionList.tierEnterprise');
      default:
        return tier;
    }
  };

  const formatQuota = (value: number): string => {
    return value === -1 ? t('admin.institutionList.unlimited') : value.toString();
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">{error}</p>
        <button
          onClick={loadInstitutions}
          className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
        >
          {t('admin.institutionList.tryAgain')}
        </button>
      </div>
    );
  }

  return (
    <div className="bg-white shadow-md rounded-lg overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
        <h2 className="text-lg font-semibold text-gray-900">{t('admin.institutionList.header')}</h2>
        <div className="flex gap-2">
          <button
            onClick={onCreateInstitution}
            className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors text-sm font-medium"
          >
            {t('admin.institutionList.btnCreate')}
          </button>
          <button
            onClick={loadInstitutions}
            className="text-sm text-primary-600 hover:text-primary-800"
          >
            {t('admin.institutionList.btnRefresh')}
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {t('admin.institutionList.colInstitution')}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {t('admin.institutionList.colDomain')}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {t('admin.institutionList.colTier')}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {t('admin.institutionList.colQuotas')}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {t('admin.institutionList.colStatus')}
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                {t('admin.institutionList.colActions')}
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {institutions.map((institution) => (
              <tr key={institution.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-gray-900">
                    {institution.name}
                  </div>
                  <div className="text-sm text-gray-500">
                    ID: {institution.id}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900">{institution.domain || '—'}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getTierBadgeColor(
                      institution.subscription_tier
                    )}`}
                  >
                    {getTierDisplayName(institution.subscription_tier)}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-xs text-gray-600">
                    <div>👥 {formatQuota(institution.max_users)}</div>
                    <div>📄 {formatQuota(institution.max_documents)}</div>
                    <div>❓ {formatQuota(institution.max_questions_per_month)}</div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      institution.is_active
                        ? 'bg-green-100 text-green-800'
                        : 'bg-red-100 text-red-800'
                    }`}
                  >
                    {institution.is_active ? t('admin.institutionList.statusActive') : t('admin.institutionList.statusInactive')}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <button
                    onClick={() => onEditInstitution(institution.id)}
                    className="text-primary-600 hover:text-primary-900"
                  >
                    {t('admin.institutionList.btnEdit')}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Empty State */}
      {institutions.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500">{t('admin.institutionList.empty')}</p>
        </div>
      )}
    </div>
  );
};
