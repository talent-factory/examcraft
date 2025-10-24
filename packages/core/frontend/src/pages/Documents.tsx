/**
 * Documents Page
 * Document management and upload
 */

import React, { useState, useRef } from 'react';
import DocumentUpload from '../components/DocumentUpload';
import DocumentLibrary from '../components/DocumentLibrary';

export const Documents: React.FC = () => {
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const libraryRef = useRef<HTMLDivElement>(null);

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">
          Dokumentenbibliothek
        </h1>
        <p className="text-gray-600 mt-2">
          Verwalte deine Lehrmaterialien und Dokumente
        </p>
      </div>

      {/* Upload Section */}
      <div className="card p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Neues Dokument hochladen
        </h2>
        <DocumentUpload onAllUploadsComplete={handleDocumentUploaded} />
      </div>

      {/* Library Section */}
      <div className="card p-6" ref={libraryRef}>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Meine Dokumente
        </h2>
        <DocumentLibrary refreshTrigger={refreshTrigger} />
      </div>
    </div>
  );
};

