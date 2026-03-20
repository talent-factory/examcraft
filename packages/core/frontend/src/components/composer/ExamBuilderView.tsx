import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ComposerService } from '../../services/ComposerService';
import { ExamStatus } from '../../types/composer';
import ExamMetadataBar from './ExamMetadataBar';
import QuestionPoolPanel from './QuestionPoolPanel';
import ExamQuestionsPanel from './ExamQuestionsPanel';
import ExportDialog from './ExportDialog';

interface ExamBuilderViewProps {
  examId: number;
  onBack: () => void;
}

const ExamBuilderView: React.FC<ExamBuilderViewProps> = ({ examId, onBack }) => {
  const queryClient = useQueryClient();
  const [exportOpen, setExportOpen] = useState(false);

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
  });

  const removeMutation = useMutation({
    mutationFn: (eqId: number) => ComposerService.removeExamQuestion(examId, eqId),
    onSuccess: invalidateExam,
  });

  const updatePointsMutation = useMutation({
    mutationFn: ({ eqId, points }: { eqId: number; points: number }) =>
      ComposerService.updateExamQuestion(examId, eqId, { points }),
    onSuccess: invalidateExam,
  });

  const reorderMutation = useMutation({
    mutationFn: (order: { id: number; position: number }[]) =>
      ComposerService.reorderQuestions(examId, order),
    onSuccess: invalidateExam,
  });

  if (isLoading) {
    return <div className="text-center py-12 text-gray-500">Lade Prüfung...</div>;
  }

  if (isError || !exam) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500">Fehler beim Laden der Prüfung.</p>
        <button
          onClick={onBack}
          className="mt-4 text-sm text-gray-500 hover:text-gray-700 underline"
        >
          Zurück zur Übersicht
        </button>
      </div>
    );
  }

  const addedQuestionIds = new Set(exam.questions.map((q) => q.question_id));
  const isDraft = exam.status === ExamStatus.DRAFT;

  return (
    <div className="space-y-4">
      {/* Back button */}
      <button
        onClick={onBack}
        className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1 transition-colors"
      >
        <span aria-hidden="true">&larr;</span> Zurück zur Übersicht
      </button>

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
    </div>
  );
};

export default ExamBuilderView;
