import React, { useState } from 'react';
import ExamListView from '../components/composer/ExamListView';
import ExamBuilderView from '../components/composer/ExamBuilderView';
import { useActivityHeartbeat } from '../hooks/useActivityHeartbeat';

export const ExamComposer: React.FC = () => {
  const [selectedExamId, setSelectedExamId] = useState<number | null>(null);
  // TF-838: "exam_compose" only counts as active while actually editing an
  // exam — browsing the list (selectedExamId === null) doesn't (TF-824 spec:
  // the route alone can't distinguish the two, only this component state can).
  useActivityHeartbeat(selectedExamId ? 'exam_compose' : null);

  if (selectedExamId) {
    return (
      <ExamBuilderView
        examId={selectedExamId}
        onBack={() => setSelectedExamId(null)}
      />
    );
  }

  return (
    <ExamListView
      onSelectExam={(id) => setSelectedExamId(id)}
    />
  );
};
