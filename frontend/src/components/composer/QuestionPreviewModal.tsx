import React from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  CircularProgress,
} from '@mui/material';
import { ComposerService, getErrorMessage } from '../../services/ComposerService';
import type { ApprovedQuestionDetail } from '../../types/composer';

const DIFFICULTY_COLORS: Record<string, string> = {
  easy: 'bg-green-100 text-green-700',
  medium: 'bg-yellow-100 text-yellow-700',
  hard: 'bg-red-100 text-red-700',
};

interface QuestionPreviewModalProps {
  /** Question id to preview, or null to keep the modal closed. */
  questionId: number | null;
  /** Whether the question is already part of the exam (toggles the action button). */
  isAdded: boolean;
  /** Whether add/remove is allowed (exam in draft). When false the action is disabled. */
  canEdit: boolean;
  onAdd: () => void;
  onRemove: () => void;
  onClose: () => void;
}

/**
 * TF-405: Rein lesendes Detail-Modal für eine Frage. Lädt das Detail erst beim
 * Öffnen nach (lazy via React Query) und markiert die korrekte Lösung.
 * Wird vom Prüfungskomponist sowohl aus dem Fragenpool (links) als auch aus den
 * Prüfungsfragen (rechts) geöffnet; der Aktions-Button schaltet je nach Zustand
 * zwischen „+ Hinzufügen" und „− Entfernen" um.
 */
const QuestionPreviewModal: React.FC<QuestionPreviewModalProps> = ({
  questionId,
  isAdded,
  canEdit,
  onAdd,
  onRemove,
  onClose,
}) => {
  const { t } = useTranslation();
  const open = questionId !== null;

  const { data, isLoading, isError, error } = useQuery<ApprovedQuestionDetail>({
    queryKey: ['approvedQuestionDetail', questionId],
    queryFn: () => ComposerService.getApprovedQuestion(questionId as number),
    enabled: open,
  });

  const TYPE_LABELS: Record<string, string> = {
    multiple_choice: t('composer.questionPool.typeMultipleChoice'),
    true_false: t('composer.questionPool.typeTrueFalse'),
    open_ended: t('composer.questionPool.typeOpenEnded'),
  };
  const DIFFICULTY_LABELS: Record<string, string> = {
    easy: t('composer.questionPool.difficultyEasy'),
    medium: t('composer.questionPool.difficultyMedium'),
    hard: t('composer.questionPool.difficultyHard'),
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{t('composer.questionPool.previewTitle')}</DialogTitle>
      <DialogContent dividers>
        {isLoading && (
          <div className="flex justify-center py-10" role="status" aria-live="polite">
            <CircularProgress size={28} />
          </div>
        )}

        {isError && (
          <p className="text-sm text-red-600 py-6">
            {getErrorMessage(error, t('composer.questionPool.previewError'))}
          </p>
        )}

        {data && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={`text-xs px-2 py-0.5 rounded-full ${
                  DIFFICULTY_COLORS[data.difficulty] ?? 'bg-gray-100 text-gray-700'
                }`}
              >
                {DIFFICULTY_LABELS[data.difficulty] ?? data.difficulty}
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">
                {TYPE_LABELS[data.question_type] ?? data.question_type}
              </span>
              {data.bloom_level != null && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">
                  {t('composer.questionPool.previewBloom', { level: data.bloom_level })}
                </span>
              )}
              {data.ln_level != null && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">
                  {t('composer.questionPool.previewLn', { level: data.ln_level })}
                </span>
              )}
            </div>

            <p className="text-[15px] font-medium text-gray-900 whitespace-pre-wrap">
              {data.question_text}
            </p>

            {data.options.length > 0 && (
              <ul className="space-y-1.5">
                {data.options.map((opt, idx) => (
                  <li
                    key={idx}
                    className={`flex items-start gap-2 text-sm px-2.5 py-1.5 rounded border ${
                      opt.is_correct
                        ? 'bg-green-50 border-green-300 text-green-900 font-medium'
                        : 'bg-white border-gray-200 text-gray-700'
                    }`}
                  >
                    <span aria-hidden="true" className="mt-0.5">
                      {opt.is_correct ? '✓' : '○'}
                    </span>
                    <span className="flex-1 min-w-0">{opt.text}</span>
                  </li>
                ))}
              </ul>
            )}

            {data.options.length === 0 && data.correct_answer && (
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                  {t('composer.questionPool.previewModelAnswer')}
                </p>
                <p className="text-sm text-gray-800 whitespace-pre-wrap bg-green-50 border border-green-200 rounded px-2.5 py-2">
                  {data.correct_answer}
                </p>
              </div>
            )}

            {data.explanation && (
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                  {t('composer.questionPool.previewExplanation')}
                </p>
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{data.explanation}</p>
              </div>
            )}

            {data.competency && (
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                  {t('composer.questionPool.previewCompetency')}
                </p>
                <p className="text-sm text-gray-700">
                  <span className="font-medium">{data.competency.code}</span> — {data.competency.title}
                </p>
              </div>
            )}

            {data.source_documents.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                  {t('composer.questionPool.previewSource')}
                </p>
                <ul className="text-sm text-gray-700 list-disc list-inside">
                  {data.source_documents.map((doc) => (
                    <li key={doc.id}>{doc.title}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} color="inherit">
          {t('composer.questionPool.previewClose')}
        </Button>
        {isAdded ? (
          <Button
            onClick={() => {
              onRemove();
              onClose();
            }}
            disabled={!canEdit || !data}
            variant="outlined"
            color="error"
          >
            − {t('composer.questionPool.previewRemove')}
          </Button>
        ) : (
          <Button
            onClick={() => {
              onAdd();
              onClose();
            }}
            disabled={!canEdit || !data}
            variant="contained"
          >
            + {t('composer.questionPool.add')}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default QuestionPreviewModal;
