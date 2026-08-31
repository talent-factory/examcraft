/**
 * Impersonation Reason Dialog Component (TF-743)
 * Confirms the target user and collects the mandatory reason and the
 * admin's own step-up password (TF-758) before
 * POST /api/admin/users/{id}/impersonate is called.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import AdminService, { UserDetailResponse } from '../../services/AdminService';
import { useAuth } from '../../contexts/AuthContext';

const REASON_MIN_LENGTH = 3;
const REASON_MAX_LENGTH = 500;

interface ImpersonationReasonDialogProps {
  userId: number | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const ImpersonationReasonDialog: React.FC<ImpersonationReasonDialogProps> = ({
  userId,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { t } = useTranslation();
  const { startImpersonation } = useAuth();
  const [target, setTarget] = useState<UserDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reason, setReason] = useState('');
  // TF-758: step-up re-authentication -- the admin re-enters their own
  // (current) password before the impersonation token is minted.
  const [adminPassword, setAdminPassword] = useState('');

  const loadTarget = useCallback(async () => {
    if (!userId) return;

    try {
      setLoading(true);
      setError(null);
      setTarget(await AdminService.getUser(userId));
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.impersonation.dialogLoadFailed'));
    } finally {
      setLoading(false);
    }
  }, [userId, t]);

  useEffect(() => {
    if (isOpen && userId) {
      loadTarget();
    }
    if (!isOpen) {
      // Reset for the next open — a dialog re-opened for a different user
      // must not show the previous reason or a stale target.
      setTarget(null);
      setReason('');
      setAdminPassword('');
      setError(null);
    }
  }, [isOpen, userId, loadTarget]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userId) return;

    const trimmedReason = reason.trim();
    if (trimmedReason.length < REASON_MIN_LENGTH) {
      setError(t('admin.impersonation.reasonTooShort', { min: REASON_MIN_LENGTH }));
      return;
    }

    if (!adminPassword) {
      setError(t('admin.impersonation.passwordRequired'));
      return;
    }

    try {
      setSaving(true);
      setError(null);

      const response = await AdminService.impersonateUser(userId, trimmedReason, adminPassword);
      await startImpersonation({
        accessToken: response.access_token,
        expiresIn: response.expires_in,
      });

      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.impersonation.dialogError'));
      // TF-758 review fix: don't leave the (possibly wrong) password sitting
      // in state/DOM after a failed attempt -- the admin re-enters it either
      // way, and this keeps its lifetime in memory as short as possible.
      setAdminPassword('');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        {/* Background overlay */}
        <div
          data-testid="impersonation-dialog-backdrop"
          className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75"
          onClick={saving ? undefined : onClose}
        ></div>

        {/* Modal panel */}
        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          <form onSubmit={handleSubmit}>
            <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
              <div className="sm:flex sm:items-start">
                <div className="mt-3 text-center sm:mt-0 sm:text-left w-full">
                  <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                    {t('admin.impersonation.dialogTitle')}
                  </h3>

                  {loading ? (
                    <div className="flex justify-center py-8">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {error && (
                        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg text-sm">
                          {error}
                        </div>
                      )}

                      {target && (
                        <div className="bg-orange-50 border border-orange-200 p-3 rounded-lg text-sm">
                          <p className="text-orange-900">
                            {t('admin.impersonation.dialogTargetLabel')}{' '}
                            <span className="font-medium">
                              {target.first_name} {target.last_name}
                            </span>{' '}
                            ({target.email})
                          </p>
                        </div>
                      )}

                      <div>
                        <label htmlFor="impersonation-reason" className="block text-sm font-medium text-gray-700 mb-1">
                          {t('admin.impersonation.dialogReasonLabel')}
                        </label>
                        <textarea
                          id="impersonation-reason"
                          name="reason"
                          rows={3}
                          value={reason}
                          onChange={(e) => setReason(e.target.value)}
                          required
                          minLength={REASON_MIN_LENGTH}
                          maxLength={REASON_MAX_LENGTH}
                          placeholder={t('admin.impersonation.dialogReasonPlaceholder')}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                        />
                      </div>

                      <div>
                        <label htmlFor="impersonation-admin-password" className="block text-sm font-medium text-gray-700 mb-1">
                          {t('admin.impersonation.dialogPasswordLabel')}
                        </label>
                        <input
                          id="impersonation-admin-password"
                          name="admin_password"
                          type="password"
                          // TF-758 review fix: this is a step-up re-auth, not a
                          // login form -- "current-password" would let a saved
                          // browser/password-manager entry autofill it, which
                          // defeats the "left-open device" half of the threat
                          // model this field exists for (no fresh knowledge of
                          // the credential is actually proven). "off" is the
                          // best-effort signal most browsers respect here.
                          autoComplete="off"
                          value={adminPassword}
                          onChange={(e) => setAdminPassword(e.target.value)}
                          required
                          placeholder={t('admin.impersonation.dialogPasswordPlaceholder')}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
              <button
                type="submit"
                disabled={saving || loading}
                className="w-full inline-flex justify-center rounded-lg border border-transparent shadow-sm px-4 py-2 bg-orange-600 text-base font-medium text-white hover:bg-orange-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-500 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving ? t('admin.impersonation.dialogStarting') : t('admin.impersonation.dialogConfirm')}
              </button>
              <button
                type="button"
                onClick={onClose}
                disabled={saving}
                className="mt-3 w-full inline-flex justify-center rounded-lg border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:w-auto sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {t('admin.impersonation.dialogCancel')}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
