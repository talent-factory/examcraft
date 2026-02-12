/**
 * Institution Create Dialog Component
 * Modal dialog for creating new institutions
 */

import React, { useState } from 'react';
import AdminService from '../../services/AdminService';

interface InstitutionCreateDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const InstitutionCreateDialog: React.FC<InstitutionCreateDialogProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [formData, setFormData] = useState({
    name: '',
    domain: '',
    subscription_tier: 'free',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name.trim()) {
      setError('Institution name is required');
      return;
    }

    if (!formData.domain.trim()) {
      setError('Domain is required');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      await AdminService.createInstitution(formData);

      // Reset form
      setFormData({
        name: '',
        domain: '',
        subscription_tier: 'free',
      });

      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create institution');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (!loading) {
      setFormData({
        name: '',
        domain: '',
        subscription_tier: 'free',
      });
      setError(null);
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Create New Institution</h2>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-6 py-4">
          {error && (
            <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {/* Institution Name */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Institution Name *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="e.g., Talent Factory GmbH"
              required
            />
          </div>

          {/* Domain */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Domain *
            </label>
            <input
              type="text"
              value={formData.domain}
              onChange={(e) => setFormData({ ...formData, domain: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="e.g., talent-factory.ch"
              required
            />
            <p className="mt-1 text-xs text-gray-500">
              Domain for email-based institution assignment
            </p>
          </div>

          {/* Subscription Tier */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Subscription Tier *
            </label>
            <select
              value={formData.subscription_tier}
              onChange={(e) => setFormData({ ...formData, subscription_tier: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="free">Free</option>
              <option value="starter">Starter</option>
              <option value="professional">Professional</option>
              <option value="enterprise">Enterprise</option>
            </select>
          </div>

          {/* Quota Preview */}
          <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h3 className="text-sm font-medium text-blue-900 mb-2">Quota Preview</h3>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-blue-700">👥 Users:</span>
                <span className="ml-2 font-medium text-blue-900">
                  {formData.subscription_tier === 'free' && '1'}
                  {formData.subscription_tier === 'starter' && '3'}
                  {formData.subscription_tier === 'professional' && '10'}
                  {formData.subscription_tier === 'enterprise' && 'Unlimited'}
                </span>
              </div>
              <div>
                <span className="text-blue-700">📄 Documents:</span>
                <span className="ml-2 font-medium text-blue-900">
                  {formData.subscription_tier === 'free' && '5'}
                  {formData.subscription_tier === 'starter' && '50'}
                  {formData.subscription_tier === 'professional' && 'Unlimited'}
                  {formData.subscription_tier === 'enterprise' && 'Unlimited'}
                </span>
              </div>
              <div>
                <span className="text-blue-700">❓ Questions/mo:</span>
                <span className="ml-2 font-medium text-blue-900">
                  {formData.subscription_tier === 'free' && '20'}
                  {formData.subscription_tier === 'starter' && '200'}
                  {formData.subscription_tier === 'professional' && '1000'}
                  {formData.subscription_tier === 'enterprise' && 'Unlimited'}
                </span>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={handleClose}
              disabled={loading}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-700 disabled:opacity-50"
            >
              {loading ? 'Creating...' : 'Create Institution'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
