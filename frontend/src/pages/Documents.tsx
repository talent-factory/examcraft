/**
 * Documents Page
 * Document management and upload
 */

import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import DocumentUpload from '../components/DocumentUpload';
import DocumentLibrary from '../components/DocumentLibrary';

export const Documents: React.FC = () => {
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const libraryRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const { t } = useTranslation();

  const handleDocumentUploaded = () => {
    // Refresh document library
    setRefreshTrigger(prev => prev + 1);

    // Scroll to document library after upload
    setTimeout(() => {
      libraryRef.current?.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      });
    }, 500); // Small delay to ensure refresh completes
  };

  const handleCreateRAGExam = (documentIds: number[]) => {
    // Navigate to exam generation page with selected documents
    navigate('/questions/generate', {
      state: { selectedDocuments: documentIds }
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">
          {t('pages.documents.title')}
        </h1>
        <p className="text-gray-600 mt-2">
          {t('pages.documents.subtitle')}
        </p>
      </div>

      {/* Upload Section */}
      <div className="card p-6" data-testid="upload-area">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          {t('pages.documents.uploadTitle')}
        </h2>
        <DocumentUpload onAllUploadsComplete={handleDocumentUploaded} />
      </div>

      {/* Library Section */}
      <div className="card p-6" ref={libraryRef} data-testid="document-list">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          {t('pages.documents.myDocuments')}
        </h2>
        <DocumentLibrary
          refreshTrigger={refreshTrigger}
          onCreateRAGExam={handleCreateRAGExam}
        />
      </div>
    </div>
  );
};
