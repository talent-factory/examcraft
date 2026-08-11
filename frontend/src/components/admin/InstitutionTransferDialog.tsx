/**
 * Institution Transfer Dialog (TF-352)
 *
 * Two-step modal launched from UserEditDialog. SuperAdmin-only.
 * Step 1: Select target institution, load preview, choose flags.
 * Step 2: Confirmation screen, execute transfer.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import AdminService, {
  TransferPreviewResponse,
  TransferUserRequest,
  UserDetailResponse,
} from '../../services/AdminService';
import { Institution } from '../../types/auth';

interface InstitutionTransferDialogProps {
  user: UserDetailResponse;
  institutions: Institution[];
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (toastMessage: string) => void;
}

type DialogStep = 'select' | 'confirm';

type TransferFlags = {
  documents: boolean;
  exams: boolean;
  questions: boolean;
  tags: boolean;
};

export const InstitutionTransferDialog: React.FC<InstitutionTransferDialogProps> = ({
  user,
  institutions,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { t } = useTranslation();
  const [step, setStep] = useState<DialogStep>('select');
  const [targetId, setTargetId] = useState<number | null>(null);
  const [preview, setPreview] = useState<TransferPreviewResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [flags, setFlags] = useState<TransferFlags>({
    documents: true,
    exams: true,
    questions: true,
    tags: true,
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setStep('select');
      setTargetId(null);
      setPreview(null);
      setError(null);
      setFlags({ documents: true, exams: true, questions: true, tags: true });
    }
  }, [isOpen]);

  useEffect(() => {
    if (!targetId || targetId === user.institution_id) {
      setPreview(null);
      return;
    }
    // Debounce: avoid hammering the preview API while the user toggles through
    // the institution dropdown. 300ms is fast enough to feel instant but
    // slow enough to absorb keyboard scroll-through of the options list.
    //
    // `cancelled` guards against an in-flight stale response: clearing the
    // timeout cancels a not-yet-fired request, but a request already dispatched
    // for an older target could resolve *after* a newer one and overwrite the
    // preview with stale counts (which then flow into the confirm step + toast).
    // Bail before touching state if this effect run has been superseded.
    let cancelled = false;
    const handle = setTimeout(async () => {
      setPreviewLoading(true);
      setError(null);
      try {
        const p = await AdminService.previewTransfer(user.id, targetId);
        if (cancelled) return;
        setPreview(p);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : t('admin.institutionTransfer.previewError'));
        setPreview(null);
      } finally {
        if (!cancelled) setPreviewLoading(false);
      }
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(handle);
    };
  }, [targetId, user.id, user.institution_id, t]);

  const handleSubmit = useCallback(async () => {
    if (!targetId) return;
    setSubmitting(true);
    setError(null);
    try {
      const body: TransferUserRequest = {
        target_institution_id: targetId,
        transfer_documents: flags.documents,
        transfer_exams: flags.exams,
        transfer_questions: flags.questions,
        transfer_tags: flags.tags,
      };
      await AdminService.transferUser(user.id, body);
      const targetName = preview?.target_institution_name || '';
      onSuccess(
        t('admin.institutionTransfer.successToast', {
          user: `${user.first_name} ${user.last_name}`,
          target: targetName,
        }),
      );
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.institutionTransfer.transferError'));
    } finally {
      setSubmitting(false);
    }
  }, [targetId, flags, user, preview, onSuccess, onClose, t]);

  if (!isOpen) return null;

  const canProceed =
    targetId !== null && targetId !== user.institution_id && preview !== null;
  const totalArtifacts =
    (preview?.transferable.documents ?? 0) +
    (preview?.transferable.exams ?? 0) +
    (preview?.transferable.questions ?? 0) +
    (preview?.transferable.tags ?? 0);

  return (
    <div
      className="fixed inset-0 z-[60] overflow-y-auto"
      role="dialog"
      aria-modal="true"
    >
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 sm:block sm:p-0">
        <div
          className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75"
          onClick={submitting ? undefined : onClose}
        />
        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-2xl sm:w-full">
          {step === 'select' ? (
            <StepSelect
              user={user}
              institutions={institutions}
              targetId={targetId}
              setTargetId={setTargetId}
              preview={preview}
              previewLoading={previewLoading}
              flags={flags}
              setFlags={setFlags}
              error={error}
              onCancel={onClose}
              onNext={() => setStep('confirm')}
              canProceed={canProceed}
              totalArtifacts={totalArtifacts}
            />
          ) : (
            <StepConfirm
              user={user}
              preview={preview!}
              flags={flags}
              error={error}
              submitting={submitting}
              onBack={() => setStep('select')}
              onExecute={handleSubmit}
            />
          )}
        </div>
      </div>
    </div>
  );
};

interface StepSelectProps {
  user: UserDetailResponse;
  institutions: Institution[];
  targetId: number | null;
  setTargetId: (id: number | null) => void;
  preview: TransferPreviewResponse | null;
  previewLoading: boolean;
  flags: TransferFlags;
  setFlags: (f: TransferFlags) => void;
  error: string | null;
  onCancel: () => void;
  onNext: () => void;
  canProceed: boolean;
  totalArtifacts: number;
}

const StepSelect: React.FC<StepSelectProps> = ({
  user,
  institutions,
  targetId,
  setTargetId,
  preview,
  previewLoading,
  flags,
  setFlags,
  error,
  onCancel,
  onNext,
  canProceed,
  totalArtifacts,
}) => {
  const { t } = useTranslation();
  const sameInstitution = targetId !== null && targetId === user.institution_id;

  return (
    <>
      <div className="bg-white px-6 pt-5 pb-4 sm:p-6">
        <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
          {t('admin.institutionTransfer.title')}
        </h3>

        <div className="space-y-4">
          <div className="text-sm">
            <div>
              <span className="text-gray-500">
                {t('admin.institutionTransfer.userLabel')}:
              </span>
              <span className="ml-2 font-medium">
                {user.first_name} {user.last_name} ({user.email})
              </span>
            </div>
            <div>
              <span className="text-gray-500">
                {t('admin.institutionTransfer.currentLabel')}:
              </span>
              <span className="ml-2 font-medium">{user.institution_name}</span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('admin.institutionTransfer.targetLabel')}
            </label>
            <select
              value={targetId ?? ''}
              onChange={(e) =>
                setTargetId(e.target.value ? Number(e.target.value) : null)
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">
                {t('admin.institutionTransfer.targetPlaceholder')}
              </option>
              {institutions
                .filter((i) => i.id !== user.institution_id)
                .map((i) => (
                  <option key={i.id} value={i.id}>
                    {i.name}
                  </option>
                ))}
            </select>
            {sameInstitution && (
              <p className="text-sm text-amber-600 mt-1">
                {t('admin.institutionTransfer.sameInstitutionHint')}
              </p>
            )}
          </div>

          {previewLoading && (
            <div className="text-sm text-gray-500 italic">
              {t('admin.institutionTransfer.previewLoading')}
            </div>
          )}

          {preview && !previewLoading && (
            <>
              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-2">
                  {t('admin.institutionTransfer.transferableHeading')}
                </h4>
                <div className="space-y-1">
                  {(['documents', 'exams', 'questions', 'tags'] as const).map(
                    (key) => (
                      <label key={key} className="flex items-center text-sm">
                        <input
                          type="checkbox"
                          checked={flags[key]}
                          disabled={preview.transferable[key] === 0}
                          onChange={(e) =>
                            setFlags({ ...flags, [key]: e.target.checked })
                          }
                          className="mr-2"
                        />
                        <span className="flex-1">
                          {t(`admin.institutionTransfer.${key}`)}
                        </span>
                        <span className="text-gray-500">
                          ({preview.transferable[key]})
                        </span>
                      </label>
                    ),
                  )}
                </div>
                {totalArtifacts === 0 && (
                  <p className="text-sm text-gray-500 mt-2">
                    {t('admin.institutionTransfer.noArtifactsHint')}
                  </p>
                )}
              </div>

              <div className="bg-gray-50 p-3 rounded-lg">
                <h4 className="text-sm font-medium text-gray-700 mb-1">
                  {t('admin.institutionTransfer.excludedHeading')}
                </h4>
                <ul className="text-sm text-gray-600 list-disc ml-5">
                  <li>
                    {t('admin.institutionTransfer.students')} (
                    {preview.excluded.students})
                  </li>
                  <li>
                    {t('admin.institutionTransfer.classes')} (
                    {preview.excluded.classes})
                  </li>
                  <li>
                    {t('admin.institutionTransfer.submissions')} (
                    {preview.excluded.submissions})
                  </li>
                </ul>
              </div>

              {preview.org_unit_memberships > 0 && (
                <p className="text-sm text-amber-600" data-testid="itd-org-units-warning">
                  {t('admin.institutionTransfer.orgUnitMembershipsWarning', {
                    count: preview.org_unit_memberships,
                  })}
                </p>
              )}
            </>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-2 rounded-lg text-sm">
              {error}
            </div>
          )}
        </div>
      </div>

      <div className="bg-gray-50 px-6 py-3 sm:flex sm:flex-row-reverse">
        <button
          type="button"
          onClick={onNext}
          disabled={!canProceed}
          className="w-full inline-flex justify-center rounded-lg px-4 py-2 bg-blue-600 text-white sm:ml-3 sm:w-auto disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {t('admin.institutionTransfer.next')}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="mt-3 w-full inline-flex justify-center rounded-lg border border-gray-300 px-4 py-2 bg-white text-gray-700 sm:mt-0 sm:w-auto"
        >
          {t('admin.institutionTransfer.cancel')}
        </button>
      </div>
    </>
  );
};

interface StepConfirmProps {
  user: UserDetailResponse;
  preview: TransferPreviewResponse;
  flags: TransferFlags;
  error: string | null;
  submitting: boolean;
  onBack: () => void;
  onExecute: () => void;
}

const StepConfirm: React.FC<StepConfirmProps> = ({
  user,
  preview,
  flags,
  error,
  submitting,
  onBack,
  onExecute,
}) => {
  const { t } = useTranslation();
  const types = ['documents', 'exams', 'questions', 'tags'] as const;
  const enabledTypes = types.filter(
    (k) => flags[k] && preview.transferable[k] > 0,
  );
  const disabledTypes = types.filter(
    (k) => !flags[k] && preview.transferable[k] > 0,
  );

  return (
    <>
      <div className="bg-white px-6 pt-5 pb-4 sm:p-6">
        <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
          {t('admin.institutionTransfer.confirmTitle')}
        </h3>
        <div className="space-y-3 text-sm">
          <p>
            {t('admin.institutionTransfer.confirmIntro', {
              user: `${user.first_name} ${user.last_name}`,
              source: preview.source_institution_name,
              target: preview.target_institution_name,
            })}
          </p>
          {enabledTypes.length > 0 && (
            <div>
              <p className="font-medium">
                {t('admin.institutionTransfer.confirmTransferred')}
              </p>
              <ul className="list-disc ml-5">
                {enabledTypes.map((k) => (
                  <li key={k}>
                    {preview.transferable[k]}{' '}
                    {t(`admin.institutionTransfer.${k}`)}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {disabledTypes.length > 0 && (
            <div>
              <p className="font-medium">
                {t('admin.institutionTransfer.confirmExcluded')}
              </p>
              <p>
                {disabledTypes
                  .map((k) => t(`admin.institutionTransfer.${k}`))
                  .join(', ')}
              </p>
            </div>
          )}
          {preview.org_unit_memberships > 0 && (
            <p className="text-amber-600" data-testid="itd-confirm-org-units-warning">
              {t('admin.institutionTransfer.orgUnitMembershipsWarning', {
                count: preview.org_unit_memberships,
              })}
            </p>
          )}
          <p className="text-amber-600 font-medium">
            {t('admin.institutionTransfer.confirmIrreversible')}
          </p>
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-2 rounded-lg">
              {error}
            </div>
          )}
        </div>
      </div>
      <div className="bg-gray-50 px-6 py-3 sm:flex sm:flex-row-reverse">
        <button
          type="button"
          onClick={onExecute}
          disabled={submitting}
          className="w-full inline-flex justify-center rounded-lg px-4 py-2 bg-red-600 text-white sm:ml-3 sm:w-auto disabled:opacity-50"
        >
          {submitting
            ? t('admin.institutionTransfer.submitting')
            : t('admin.institutionTransfer.execute')}
        </button>
        <button
          type="button"
          onClick={onBack}
          disabled={submitting}
          className="mt-3 w-full inline-flex justify-center rounded-lg border border-gray-300 px-4 py-2 bg-white text-gray-700 sm:mt-0 sm:w-auto"
        >
          {t('admin.institutionTransfer.back')}
        </button>
      </div>
    </>
  );
};
