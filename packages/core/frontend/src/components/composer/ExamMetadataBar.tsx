import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
} from '@mui/material';
import { ComposerService, getErrorMessage } from '../../services/ComposerService';
import { getDateLocale } from '../../utils/dateLocale';
import type { ExamDetail, UpdateExamRequest } from '../../types/composer';
import { ExamStatus } from '../../types/composer';

interface ExamMetadataBarProps {
  exam: ExamDetail;
  onExport: () => void;
  onInvalidate: () => void;
}

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-yellow-100 text-yellow-800',
  finalized: 'bg-green-100 text-green-800',
  exported: 'bg-blue-100 text-blue-800',
};

interface EditForm {
  title: string;
  course: string;
  exam_date: string;
  time_limit_minutes: string;
  allowed_aids: string;
  instructions: string;
  passing_percentage: string;
}

const ExamMetadataBar: React.FC<ExamMetadataBarProps> = ({ exam, onExport, onInvalidate }) => {
  const { t, i18n } = useTranslation();

  const STATUS_LABELS: Record<string, string> = {
    draft: t('composer.examMetadata.statusDraft'),
    finalized: t('composer.examMetadata.statusFinalized'),
    exported: t('composer.examMetadata.statusExported'),
  };

  const [editOpen, setEditOpen] = useState(false);
  const [form, setForm] = useState<EditForm>({
    title: '',
    course: '',
    exam_date: '',
    time_limit_minutes: '',
    allowed_aids: '',
    instructions: '',
    passing_percentage: '',
  });
  const [finalizeError, setFinalizeError] = useState<string | null>(null);

  const openEdit = () => {
    setForm({
      title: exam.title,
      course: exam.course || '',
      exam_date: exam.exam_date || '',
      time_limit_minutes: exam.time_limit_minutes?.toString() || '',
      allowed_aids: exam.allowed_aids || '',
      instructions: exam.instructions || '',
      passing_percentage: exam.passing_percentage?.toString() || '50',
    });
    setEditOpen(true);
  };

  const updateMutation = useMutation({
    mutationFn: (data: UpdateExamRequest) => ComposerService.updateExam(exam.id, data),
    onSuccess: () => {
      setEditOpen(false);
      onInvalidate();
    },
    onError: (err) => {
      setFinalizeError(getErrorMessage(err, t('composer.examMetadata.errorSave')));
    },
  });

  const finalizeMutation = useMutation({
    mutationFn: () => ComposerService.finalizeExam(exam.id),
    onSuccess: () => {
      setFinalizeError(null);
      onInvalidate();
    },
    onError: (err) => {
      setFinalizeError(getErrorMessage(err, t('composer.examMetadata.errorFinalize')));
    },
  });

  const unfinalizeMutation = useMutation({
    mutationFn: () => ComposerService.unfinalizeExam(exam.id),
    onSuccess: () => {
      setFinalizeError(null);
      onInvalidate();
    },
    onError: (err) => {
      setFinalizeError(getErrorMessage(err, t('composer.examMetadata.errorUnfinalize')));
    },
  });

  const handleSave = () => {
    const payload: UpdateExamRequest = {
      updated_at: exam.updated_at,
      title: form.title.trim() || undefined,
      course: form.course || undefined,
      exam_date: form.exam_date || undefined,
      time_limit_minutes: form.time_limit_minutes ? parseInt(form.time_limit_minutes) : undefined,
      allowed_aids: form.allowed_aids || undefined,
      instructions: form.instructions || undefined,
      passing_percentage: form.passing_percentage ? parseFloat(form.passing_percentage) : undefined,
    };
    updateMutation.mutate(payload);
  };

  const isDraft = exam.status === ExamStatus.DRAFT;
  const isFinalized = exam.status === ExamStatus.FINALIZED;

  return (
    <div className="card p-4 bg-white rounded-lg border border-gray-200">
      <div className="flex items-start justify-between gap-4">
        {/* Title + stats */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h2 className="text-2xl font-bold text-gray-900 truncate">{exam.title}</h2>
            <span
              className={`text-xs px-2 py-1 rounded-full font-medium ${
                STATUS_COLORS[exam.status] || 'bg-gray-100 text-gray-800'
              }`}
            >
              {STATUS_LABELS[exam.status] || exam.status}
            </span>
          </div>
          {exam.course && (
            <p className="text-sm text-gray-500 mt-1">{exam.course}</p>
          )}
          <div className="flex gap-4 mt-2 text-sm text-gray-600 flex-wrap">
            <span>
              <strong>{exam.question_count}</strong> {t('composer.examMetadata.questions')}
            </span>
            <span>
              <strong>{exam.total_points}</strong> {t('composer.examMetadata.points')}
            </span>
            {exam.time_limit_minutes && (
              <span>
                <strong>{exam.time_limit_minutes}</strong> {t('composer.examMetadata.minutes')}
              </span>
            )}
            {exam.exam_date && (
              <span>{t('composer.examMetadata.date')}: <strong>{new Date(exam.exam_date).toLocaleDateString(getDateLocale(i18n.language), { day: '2-digit', month: '2-digit', year: 'numeric' })}</strong></span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex flex-col items-end gap-2 flex-shrink-0">
          <div className="flex items-center gap-2 flex-wrap justify-end">
            {isDraft && (
              <button
                onClick={openEdit}
                className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                {t('composer.examMetadata.editMetadata')}
              </button>
            )}

            {isDraft && (
              <button
                onClick={() => { setFinalizeError(null); finalizeMutation.mutate(); }}
                disabled={finalizeMutation.isPending}
                className="px-3 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
              >
                {finalizeMutation.isPending ? t('composer.examMetadata.finalizing') : t('composer.examMetadata.finalize')}
              </button>
            )}

            {isFinalized && (
              <button
                onClick={() => { setFinalizeError(null); unfinalizeMutation.mutate(); }}
                disabled={unfinalizeMutation.isPending}
                className="px-3 py-1.5 text-sm border border-yellow-500 text-yellow-700 rounded-lg hover:bg-yellow-50 transition-colors disabled:opacity-50"
              >
                {unfinalizeMutation.isPending ? t('composer.examMetadata.unfinalizingPending') : t('composer.examMetadata.markAsDraft')}
              </button>
            )}

            <button
              onClick={onExport}
              disabled={exam.question_count === 0}
              className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t('composer.examMetadata.export')}
            </button>
          </div>

          {finalizeError && (
            <p className="text-red-500 text-sm text-right max-w-xs">{finalizeError}</p>
          )}
        </div>
      </div>

      {/* Edit Dialog */}
      <Dialog open={editOpen} onClose={() => setEditOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{t('composer.examMetadata.editDialogTitle')}</DialogTitle>
        <DialogContent>
          <div className="space-y-4 mt-2">
            <TextField
              label={t('composer.examMetadata.fieldTitle')}
              fullWidth
              required
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
            />
            <TextField
              label={t('composer.examMetadata.fieldCourse')}
              fullWidth
              value={form.course}
              onChange={(e) => setForm({ ...form, course: e.target.value })}
            />
            <TextField
              label={t('composer.examMetadata.fieldExamDate')}
              type="date"
              fullWidth
              InputLabelProps={{ shrink: true }}
              value={form.exam_date}
              onChange={(e) => setForm({ ...form, exam_date: e.target.value })}
            />
            <TextField
              label={t('composer.examMetadata.fieldTimeLimit')}
              type="number"
              fullWidth
              value={form.time_limit_minutes}
              onChange={(e) => setForm({ ...form, time_limit_minutes: e.target.value })}
            />
            <TextField
              label={t('composer.examMetadata.fieldAllowedAids')}
              fullWidth
              multiline
              rows={2}
              value={form.allowed_aids}
              onChange={(e) => setForm({ ...form, allowed_aids: e.target.value })}
            />
            <TextField
              label={t('composer.examMetadata.fieldInstructions')}
              fullWidth
              multiline
              rows={3}
              value={form.instructions}
              onChange={(e) => setForm({ ...form, instructions: e.target.value })}
            />
            <TextField
              label={t('composer.examMetadata.fieldPassingPercentage')}
              type="number"
              fullWidth
              inputProps={{ min: 0, max: 100, step: 1 }}
              value={form.passing_percentage}
              onChange={(e) => setForm({ ...form, passing_percentage: e.target.value })}
            />
          </div>
          {updateMutation.isError && finalizeError && (
            <p className="text-red-500 text-sm mt-2">{finalizeError}</p>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditOpen(false)} disabled={updateMutation.isPending}>
            {t('composer.examMetadata.cancel')}
          </Button>
          <Button
            onClick={handleSave}
            variant="contained"
            disabled={!form.title.trim() || updateMutation.isPending}
          >
            {updateMutation.isPending ? t('composer.examMetadata.saving') : t('composer.examMetadata.save')}
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};

export default ExamMetadataBar;
