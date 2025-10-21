/**
 * Exams Page
 * Exam generation and management
 */

import React from 'react';
import RAGExamCreator from '../components/RAGExamCreator';

export const Exams: React.FC = () => {
  const handleExamGenerated = (exam: any) => {
    console.log('Exam generated:', exam);
  };

  const handleBack = () => {
    console.log('Back to exams');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">
          Prüfungsgenerierung
        </h1>
        <p className="text-gray-600 mt-2">
          Erstelle intelligente Prüfungsaufgaben mit KI-Unterstützung
        </p>
      </div>

      {/* RAG Exam Creator */}
      <RAGExamCreator
        selectedDocuments={[]}
        onExamGenerated={handleExamGenerated}
        onBack={handleBack}
      />
    </div>
  );
};

