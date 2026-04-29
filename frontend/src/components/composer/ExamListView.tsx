import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Autocomplete,
  Chip,
} from '@mui/material';
import { ComposerService, getErrorMessage } from '../../services/ComposerService';
import { getDateLocale } from '../../utils/dateLocale';
import type { CreateExamRequest, DocumentWithQuestions } from '../../types/composer';

interface ExamListViewProps {
  onSelectExam: (id: number) => void;
}

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-yellow-100 text-yellow-800',
  finalized: 'bg-green-100 text-green-800',
  exported: 'bg-blue-100 text-blue-800',
};

const ExamListView: React.FC<ExamListViewProps> = ({ onSelectExam }) => {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState<CreateExamRequest>({ title: '', language: 'de' });
  const [selectedDocuments, setSelectedDocuments] = useState<DocumentWithQuestions[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);

  const STATUS_LABELS: Record<string, string> = {
    draft: t('composer.examList.statusDraft'),
    finalized: t('composer.examList.statusFinalized'),
    exported: t('composer.examList.statusExported'),
  };

  const { data, isLoading, isError: isQueryError } = useQuery({
    queryKey: ['exams', searchQuery],
    queryFn: () => ComposerService.listExams({ search: searchQuery || undefined }),
  });

  const { data: availableDocuments = [] } = useQuery({
    queryKey: ['documents-with-questions'],
    queryFn: () => ComposerService.listDocumentsWithQuestions(),
    enabled: dialogOpen,
  });

  const createMutation = useMutation({
    mutationFn: ComposerService.createExam,
    onSuccess: (exam) => {
      queryClient.invalidateQueries({ queryKey: ['exams'] });
      setDialogOpen(false);
      setForm({ title: '', language: 'de' });
      setSelectedDocuments([]);
      onSelectExam(exam.id);
    },
    onError: (err) => {
      setError(getErrorMessage(err, t('composer.examList.errorCreate')));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: ComposerService.deleteExam,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['exams'] }),
    onError: (err) => {
      setError(getErrorMessage(err, t('composer.examList.errorDelete')));
    },
  });

  const handleCreate = () => {
    if (form.title.trim()) {
      createMutation.mutate({
        ...form,
        default_document_ids:
          selectedDocuments.length > 0 ? selectedDocuments.map((d) => d.id) : undefined,
      });
    }
  };

  const handleDialogClose = () => {
    if (!createMutation.isPending) {
      setDialogOpen(false);
      setForm({ title: '', language: 'de' });
      setSelectedDocuments([]);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{t('composer.examList.title')}</h1>
          <p className="text-gray-600 mt-2">{t('composer.examList.subtitle')}</p>
        </div>
        <button
          onClick={() => setDialogOpen(true)}
          className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 transition-colors"
        >
          {t('composer.examList.newExam')}
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex justify-between items-center">
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            className="ml-4 text-red-500 hover:text-red-700 font-bold text-lg leading-none"
            aria-label={t('composer.examList.closeError')}
          >
            &times;
          </button>
        </div>
      )}

      {/* Search */}
      <div>
        <input
          type="text"
          placeholder={t('composer.examList.searchPlaceholder')}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
        />
      </div>

      {/* Exam Grid */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-500">{t('composer.examList.loading')}</div>
      ) : isQueryError ? (
        <div className="card p-12 text-center">
          <p className="text-red-500 text-lg">{t('composer.examList.loadError')}</p>
        </div>
      ) : !data?.exams.length ? (
        <div className="card p-12 text-center">
          <p className="text-gray-500 text-lg">{t('composer.examList.empty')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.exams.map((exam) => (
            <div
              key={exam.id}
              onClick={() => onSelectExam(exam.id)}
              className="card p-4 cursor-pointer hover:shadow-md transition-shadow flex flex-col"
            >
              <div className="flex justify-between items-start">
                <h3 className="font-semibold text-gray-900 truncate flex-1">{exam.title}</h3>
                <span
                  className={`text-xs px-2 py-1 rounded-full ml-2 flex-shrink-0 ${
                    STATUS_COLORS[exam.status] || 'bg-gray-100 text-gray-800'
                  }`}
                >
                  {STATUS_LABELS[exam.status] || exam.status}
                </span>
              </div>
              {exam.course && <p className="text-sm text-gray-500 mt-1">{exam.course}</p>}
              <div className="flex items-center gap-3 mt-auto pt-3 text-sm text-gray-600">
                <span>{t('composer.examList.questionCount', { count: exam.question_count })}</span>
                <span>{t('composer.examList.pointsCount', { count: exam.total_points })}</span>
                {exam.exam_date && (
                  <span>
                    {new Date(exam.exam_date).toLocaleDateString(
                      getDateLocale(i18n.language),
                      { day: '2-digit', month: '2-digit', year: 'numeric' }
                    )}
                  </span>
                )}
                {exam.status === 'draft' && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeleteConfirmId(exam.id);
                    }}
                    className="ml-auto text-gray-300 hover:text-red-500 transition-colors p-0.5"
                    aria-label={t('composer.examList.delete')}
                  >
                    <svg className="w-[22px] h-[22px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.6}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteConfirmId !== null} onClose={() => setDeleteConfirmId(null)} maxWidth="xs" fullWidth>
        <DialogTitle>{t('composer.examList.deleteDialogTitle')}</DialogTitle>
        <DialogContent>
          <p className="text-sm text-gray-600 mt-1">{t('composer.examList.deleteDialogMessage')}</p>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirmId(null)} disabled={deleteMutation.isPending}>
            {t('composer.examList.cancel')}
          </Button>
          <Button
            onClick={() => {
              if (deleteConfirmId !== null) {
                deleteMutation.mutate(deleteConfirmId);
                setDeleteConfirmId(null);
              }
            }}
            color="error"
            variant="contained"
            disabled={deleteMutation.isPending}
          >
            {t('composer.examList.delete')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Create Dialog */}
      <Dialog open={dialogOpen} onClose={handleDialogClose} maxWidth="sm" fullWidth>
        <DialogTitle>{t('composer.examList.dialogTitle')}</DialogTitle>
        <DialogContent>
          <div className="space-y-4 mt-2">
            <TextField
              label={t('composer.examList.fieldTitle')}
              fullWidth
              required
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
            />
            <TextField
              label={t('composer.examList.fieldCourse')}
              fullWidth
              value={form.course || ''}
              onChange={(e) => setForm({ ...form, course: e.target.value })}
            />
            <TextField
              label={t('composer.examList.fieldExamDate')}
              type="date"
              fullWidth
              InputLabelProps={{ shrink: true }}
              value={form.exam_date || ''}
              onChange={(e) => setForm({ ...form, exam_date: e.target.value })}
            />
            <TextField
              label={t('composer.examList.fieldTimeLimit')}
              type="number"
              fullWidth
              value={form.time_limit_minutes || ''}
              onChange={(e) =>
                setForm({ ...form, time_limit_minutes: parseInt(e.target.value) || undefined })
              }
            />
            <TextField
              label={t('composer.examList.fieldAllowedAids')}
              fullWidth
              multiline
              rows={2}
              value={form.allowed_aids || ''}
              onChange={(e) => setForm({ ...form, allowed_aids: e.target.value })}
            />
            <Autocomplete
              multiple
              options={availableDocuments}
              getOptionLabel={(doc) => `${doc.title}`}
              isOptionEqualToValue={(a, b) => a.id === b.id}
              value={selectedDocuments}
              onChange={(_, newValue) => setSelectedDocuments(newValue)}
              renderTags={(value, getTagProps) =>
                value.map((doc, index) => (
                  <Chip
                    label={`${doc.title}`}
                    size="small"
                    {...getTagProps({ index })}
                    key={doc.id}
                  />
                ))
              }
              renderInput={(params) => (
                <TextField
                  {...params}
                  label={t('composer.examList.fieldDocuments')}
                  placeholder={
                    selectedDocuments.length === 0
                      ? t('composer.examList.fieldDocumentsPlaceholder')
                      : ''
                  }
                  helperText={t('composer.examList.fieldDocumentsHint')}
                />
              )}
            />
          </div>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDialogClose} disabled={createMutation.isPending}>
            {t('composer.examList.cancel')}
          </Button>
          <Button
            onClick={handleCreate}
            variant="contained"
            disabled={!form.title.trim() || createMutation.isPending}
          >
            {createMutation.isPending
              ? t('composer.examList.creating')
              : t('composer.examList.create')}
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};

export default ExamListView;
