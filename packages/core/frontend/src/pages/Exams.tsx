/**
 * Exams Page
 * Exam generation and management
 *
 * TEMPORARY: Uses BasicExamCreator until TF-200 (NPM Workspace Migration) is merged.
 * After TF-200 merge, this will use Premium RAGExamCreator via @examcraft/premium package.
 */

import React from 'react';
import { BasicExamCreator } from '../components/exam/BasicExamCreator';

export const Exams: React.FC = () => {
  const handleExamGenerated = (exam: any) => {
    console.log('Exam generated:', exam);
    // TODO: Navigate to exam review page
  };

  const handleBack = () => {
    console.log('Back to exams');
    // TODO: Navigate back
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

      {/* Basic Exam Creator (Temporary until TF-200 merge) */}
      <BasicExamCreator
        selectedDocuments={[]}
        onExamGenerated={handleExamGenerated}
        onBack={handleBack}
      />
    </div>
  );
};
