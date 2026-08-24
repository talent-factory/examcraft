import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { ComposerService, getErrorMessage } from '../../services/ComposerService';
import { ExamStatus } from '../../types/composer';
import ExamMetadataBar from './ExamMetadataBar';
import QuestionPoolPanel from './QuestionPoolPanel';
import ExamQuestionsPanel from './ExamQuestionsPanel';
import ExportDialog from './ExportDialog';
import QuestionPreviewModal from './QuestionPreviewModal';

interface ExamBuilderViewProps {
  examId: number;
  onBack: () => void;
}

const ExamBuilderView: React.FC<ExamBuilderViewProps> = ({ examId, onBack }) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [exportOpen, setExportOpen] = useState(false);
  const [builderError, setBuilderError] = useState<string | null>(null);
  // TF-405: read-only preview modal, shared by both panels (left pool + right exam).
  const [previewQuestionId, setPreviewQuestionId] = useState<number | null>(null);

  const { data: exam, isLoading, isError } = useQuery({
    queryKey: ['exam', examId],
    queryFn: () => ComposerService.getExam(examId),
  });

  const invalidateExam = () => {
    queryClient.invalidateQueries({ queryKey: ['exam', examId] });
    queryClient.invalidateQueries({ queryKey: ['exams'] });
  };

  const addMutation = useMutation({
    mutationFn: (qIds: number[]) => ComposerService.addQuestions(examId, qIds),
    onSuccess: invalidateExam,
    onError: (err) => {
      setBuilderError(getErrorMessage(err, t('composer.examBuilder.errorAddQuestions')));
    },
  });

  const removeMutation = useMutation({
    mutationFn: (eqId: number) => ComposerService.removeExamQuestion(examId, eqId),
    onSuccess: invalidateExam,
    onError: (err) => {
      setBuilderError(getErrorMessage(err, t('composer.examBuilder.errorRemoveQuestion')));
    },
  });

  const updatePointsMutation = useMutation({
    mutationFn: ({ eqId, points }: { eqId: number; points: number }) =>
      ComposerService.updateExamQuestion(examId, eqId, { points }),
    onSuccess: invalidateExam,
    onError: (err) => {
      setBuilderError(getErrorMessage(err, t('composer.examBuilder.errorUpdatePoints')));
    },
  });

  const reorderMutation = useMutation({
    mutationFn: (order: { id: number; position: number }[]) =>
      ComposerService.reorderQuestions(examId, order),
    onSuccess: invalidateExam,
    onError: (err) => {
      setBuilderError(getErrorMessage(err, t('composer.examBuilder.errorReorder')));
    },
  });

  if (isLoading) {
    return <div className="text-center py-12 text-gray-500">{t('composer.examBuilder.loading')}</div>;
  }

  if (isError || !exam) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500">{t('composer.examBuilder.loadError')}</p>
        <button
          onClick={onBack}
          className="mt-4 text-sm text-gray-500 hover:text-gray-700 underline"
        >
          {t('composer.examBuilder.backToOverview')}
        </button>
      </div>
    );
  }

  const addedQuestionIds = new Set(exam.questions.map((q) => q.question_id));
  const isDraft = exam.status === ExamStatus.DRAFT;

  return (
    <div className="space-y-4" data-testid="exam-builder">
      {/* Back button */}
      <button
        onClick={onBack}
        className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1 transition-colors"
      >
        <span aria-hidden="true">&larr;</span> {t('composer.examBuilder.backToOverview')}
      </button>

      {/* Error banner */}
      {builderError && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex justify-between items-center">
          <span>{builderError}</span>
          <button
            onClick={() => setBuilderError(null)}
            className="ml-4 text-red-500 hover:text-red-700 font-bold text-lg leading-none"
            aria-label={t('composer.examBuilder.closeError')}
          >
            &times;
          </button>
        </div>
      )}

      {/* Top metadata bar */}
      <ExamMetadataBar
        exam={exam}
        onExport={() => setExportOpen(true)}
        onInvalidate={invalidateExam}
      />

      {/* Two-column builder layout */}
      <div className="flex gap-4" style={{ minHeight: '60vh' }}>
        {/* Left: Question Pool */}
        <div className="w-1/2 min-w-0">
          <QuestionPoolPanel
            addedQuestionIds={addedQuestionIds}
            onAddQuestions={(ids) => addMutation.mutate(ids)}
            examId={examId}
            disabled={!isDraft}
            onInvalidate={invalidateExam}
            defaultDocumentIds={exam.default_document_ids ?? []}
            onPreview={setPreviewQuestionId}
          />
        </div>

        {/* Right: Exam Questions (DnD) */}
        <div className="w-1/2 min-w-0">
          <ExamQuestionsPanel
            questions={exam.questions}
            disabled={!isDraft}
            onRemove={(eqId) => removeMutation.mutate(eqId)}
            onUpdatePoints={(eqId, points) =>
              updatePointsMutation.mutate({ eqId, points })
            }
            onReorder={(order) => reorderMutation.mutate(order)}
            onPreview={setPreviewQuestionId}
          />
        </div>
      </div>

      {/* Export Dialog */}
      <ExportDialog
        open={exportOpen}
        onClose={() => setExportOpen(false)}
        examId={examId}
        examTitle={exam.title}
        hasQuestions={exam.questions.length > 0}
      />

      {/* TF-405: read-only preview modal, shared by both panels */}
      <QuestionPreviewModal
        questionId={previewQuestionId}
        isAdded={previewQuestionId !== null && addedQuestionIds.has(previewQuestionId)}
        canEdit={isDraft}
        onAdd={() => {
          if (previewQuestionId !== null) {
            addMutation.mutate([previewQuestionId]);
          }
        }}
        onRemove={() => {
          if (previewQuestionId === null) return;
          const eq = exam.questions.find((q) => q.question_id === previewQuestionId);
          if (eq) {
            removeMutation.mutate(eq.id);
          } else {
            // Defensive: the "Remove" button only appears when isAdded is true
            // (same exam.questions source) — so this branch should never be
            // reached. If the two ever diverge, it's better to show an error
            // than to close the modal silently (no silent fail).
            setBuilderError(t('composer.examBuilder.errorRemoveQuestion'));
          }
        }}
        onClose={() => setPreviewQuestionId(null)}
      />
    </div>
  );
};

export default ExamBuilderView;
