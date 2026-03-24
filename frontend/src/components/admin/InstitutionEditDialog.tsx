/**
 * Institution Edit Dialog Component
 * Modal dialog for editing institution details and subscription tier
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import AdminService from '../../services/AdminService';
import { Institution } from '../../types/auth';

interface InstitutionEditDialogProps {
  institutionId: number | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const SUBSCRIPTION_TIER_VALUES = [
  { value: 'free', color: 'gray' },
  { value: 'starter', color: 'blue' },
  { value: 'professional', color: 'purple' },
  { value: 'enterprise', color: 'orange' },
];

const TIER_QUOTAS: Record<string, { users: number; documents: number; questions: number }> = {
  free: { users: 1, documents: 5, questions: 20 },
  starter: { users: 3, documents: 50, questions: 200 },
  professional: { users: 10, documents: -1, questions: 1000 },
  enterprise: { users: -1, documents: -1, questions: -1 },
};

export const InstitutionEditDialog: React.FC<InstitutionEditDialogProps> = ({
  institutionId,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { t } = useTranslation();

  const SUBSCRIPTION_TIERS = [
    { value: 'free', label: t('admin.institutionList.tierFree'), color: 'gray' },
    { value: 'starter', label: t('admin.institutionList.tierStarter'), color: 'blue' },
    { value: 'professional', label: t('admin.institutionList.tierProfessional'), color: 'purple' },
    { value: 'enterprise', label: t('admin.institutionList.tierEnterprise'), color: 'orange' },
  ];

  const [institution, setInstitution] = useState<Institution | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    name: '',
    domain: '',
    subscription_tier: 'free',
    is_active: true,
  });

  const loadInstitution = useCallback(async () => {
    if (!institutionId) return;

    try {
      setLoading(true);
      setError(null);
      const institutions = await AdminService.listInstitutions();
      const inst = institutions.find((i) => i.id === institutionId);

      if (inst) {
        setInstitution(inst);
        setFormData({
          name: inst.name,
          domain: inst.domain || '',
          subscription_tier: inst.subscription_tier,
          is_active: inst.is_active,
        });
      } else {
        setError(t('admin.institutionEdit.notFound'));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.institutionEdit.failedLoad'));
    } finally {
      setLoading(false);
    }
  }, [institutionId]);

  useEffect(() => {
    if (isOpen && institutionId) {
      loadInstitution();
    }
  }, [isOpen, institutionId, loadInstitution]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!institutionId) return;

    try {
      setSaving(true);
      setError(null);
      await AdminService.updateInstitution(institutionId, formData);
      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.institutionEdit.failedUpdate'));
    } finally {
      setSaving(false);
    }
  };

  const formatQuota = (value: number): string => {
    return value === -1 ? t('admin.institutionEdit.unlimited') : value.toString();
  };

  const getQuotasForTier = (tier: string) => {
    return TIER_QUOTAS[tier] || TIER_QUOTAS.free;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h2 className="text-xl font-semibold text-gray-900">
            {t('admin.institutionEdit.title')}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            disabled={saving}
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4">
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
          ) : error ? (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
              <p className="text-red-800">{error}</p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {t('admin.institutionEdit.nameLabel')}
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                  required
                />
              </div>

              {/* Domain */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {t('admin.institutionEdit.domainLabel')}
                </label>
                <input
                  type="text"
                  value={formData.domain}
                  onChange={(e) => setFormData({ ...formData, domain: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder={t('admin.institutionEdit.domainPlaceholder')}
                  required
                />
              </div>

              {/* Subscription Tier */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {t('admin.institutionEdit.tierLabel')}
                </label>
                <select
                  value={formData.subscription_tier}
                  onChange={(e) =>
                    setFormData({ ...formData, subscription_tier: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  {SUBSCRIPTION_TIERS.map((tier) => (
                    <option key={tier.value} value={tier.value}>
                      {tier.label}
                    </option>
                  ))}
                </select>

                {/* Quota Preview */}
                <div className="mt-3 p-3 bg-gray-50 rounded-md">
                  <p className="text-xs font-medium text-gray-700 mb-2">
                    {t('admin.institutionEdit.quotasForTier', { tier: SUBSCRIPTION_TIERS.find(tier => tier.value === formData.subscription_tier)?.label })}
                  </p>
                  <div className="grid grid-cols-3 gap-2 text-xs text-gray-600">
                    <div>
                      <span className="font-medium">{t('admin.institutionEdit.quotaUsers')}</span>{' '}
                      {formatQuota(getQuotasForTier(formData.subscription_tier).users)}
                    </div>
                    <div>
                      <span className="font-medium">{t('admin.institutionEdit.quotaDocs')}</span>{' '}
                      {formatQuota(getQuotasForTier(formData.subscription_tier).documents)}
                    </div>
                    <div>
                      <span className="font-medium">{t('admin.institutionEdit.quotaQuestions')}</span>{' '}
                      {formatQuota(getQuotasForTier(formData.subscription_tier).questions)}
                    </div>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">
                    {t('admin.institutionEdit.quotaNote')}
                  </p>
                </div>
              </div>

              {/* Status */}
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={formData.is_active}
                  onChange={(e) =>
                    setFormData({ ...formData, is_active: e.target.checked })
                  }
                  className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                />
                <label htmlFor="is_active" className="ml-2 block text-sm text-gray-700">
                  {t('admin.institutionEdit.isActiveLabel')}
                </label>
              </div>

              {/* Current Values (Read-only) */}
              {institution && (
                <div className="border-t border-gray-200 pt-4">
                  <p className="text-sm font-medium text-gray-700 mb-2">{t('admin.institutionEdit.currentQuotas')}</p>
                  <div className="grid grid-cols-3 gap-2 text-xs text-gray-600">
                    <div>
                      <span className="font-medium">{t('admin.institutionEdit.quotaUsers')}</span>{' '}
                      {formatQuota(institution.max_users)}
                    </div>
                    <div>
                      <span className="font-medium">{t('admin.institutionEdit.quotaDocs')}</span>{' '}
                      {formatQuota(institution.max_documents)}
                    </div>
                    <div>
                      <span className="font-medium">{t('admin.institutionEdit.quotaQuestions')}</span>{' '}
                      {formatQuota(institution.max_questions_per_month)}
                    </div>
                  </div>
                </div>
              )}
            </form>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
          <button
            onClick={onClose}
            disabled={saving}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
          >
            {t('admin.institutionEdit.cancel')}
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving || loading}
            className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-700 disabled:opacity-50"
          >
            {saving ? t('admin.institutionEdit.saving') : t('admin.institutionEdit.saveChanges')}
          </button>
        </div>
      </div>
    </div>
  );
};
