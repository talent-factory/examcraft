import React, { useState } from 'react';
import ExamListView from '../components/composer/ExamListView';
import ExamBuilderView from '../components/composer/ExamBuilderView';

export const ExamComposer: React.FC = () => {
  const [selectedExamId, setSelectedExamId] = useState<number | null>(null);

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
