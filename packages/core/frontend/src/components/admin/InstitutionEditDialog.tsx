/**
 * Institution Edit Dialog Component
 * Modal dialog for editing institution details and subscription tier
 */

import React, { useState, useEffect } from 'react';
import AdminService from '../../services/AdminService';
import { Institution } from '../../types/auth';

interface InstitutionEditDialogProps {
  institutionId: number | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const SUBSCRIPTION_TIERS = [
  { value: 'free', label: 'Free', color: 'gray' },
  { value: 'starter', label: 'Starter', color: 'blue' },
  { value: 'professional', label: 'Professional', color: 'purple' },
  { value: 'enterprise', label: 'Enterprise', color: 'orange' },
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

  useEffect(() => {
    if (isOpen && institutionId) {
      loadInstitution();
    }
  }, [isOpen, institutionId]);

  const loadInstitution = async () => {
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
          domain: inst.domain,
          subscription_tier: inst.subscription_tier,
          is_active: inst.is_active,
        });
      } else {
        setError('Institution not found');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load institution');
    } finally {
      setLoading(false);
    }
  };

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
      setError(err instanceof Error ? err.message : 'Failed to update institution');
    } finally {
      setSaving(false);
    }
  };

  const formatQuota = (value: number): string => {
    return value === -1 ? 'Unlimited' : value.toString();
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
            Edit Institution
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
                  Institution Name
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
                  Domain
                </label>
                <input
                  type="text"
                  value={formData.domain}
                  onChange={(e) => setFormData({ ...formData, domain: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="example.com"
                  required
                />
              </div>

              {/* Subscription Tier */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Subscription Tier
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
                    Quotas for {SUBSCRIPTION_TIERS.find(t => t.value === formData.subscription_tier)?.label}:
                  </p>
                  <div className="grid grid-cols-3 gap-2 text-xs text-gray-600">
                    <div>
                      <span className="font-medium">👥 Users:</span>{' '}
                      {formatQuota(getQuotasForTier(formData.subscription_tier).users)}
                    </div>
                    <div>
                      <span className="font-medium">📄 Documents:</span>{' '}
                      {formatQuota(getQuotasForTier(formData.subscription_tier).documents)}
                    </div>
                    <div>
                      <span className="font-medium">❓ Questions/mo:</span>{' '}
                      {formatQuota(getQuotasForTier(formData.subscription_tier).questions)}
                    </div>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">
                    ℹ️ Quotas will be automatically updated when you save
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
                  Institution is active
                </label>
              </div>

              {/* Current Values (Read-only) */}
              {institution && (
                <div className="border-t border-gray-200 pt-4">
                  <p className="text-sm font-medium text-gray-700 mb-2">Current Quotas:</p>
                  <div className="grid grid-cols-3 gap-2 text-xs text-gray-600">
                    <div>
                      <span className="font-medium">👥 Users:</span>{' '}
                      {formatQuota(institution.max_users)}
                    </div>
                    <div>
                      <span className="font-medium">📄 Documents:</span>{' '}
                      {formatQuota(institution.max_documents)}
                    </div>
                    <div>
                      <span className="font-medium">❓ Questions/mo:</span>{' '}
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
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving || loading}
            className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-700 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
};

