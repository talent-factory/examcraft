/**
 * Prompt Library Page
 * Prompt management and library for admins and teachers
 *
 * Premium Version (Full Deployment): Shows PromptLibraryWithUpload (with tabs + file upload)
 * Core Version: Shows basic PromptManagement
 */

import React from 'react';
import { PromptManagement } from '../components/admin/PromptManagement';
import { loadPromptLibraryWithUpload } from '../utils/componentLoader';
import { isFullDeployment } from '../utils/deploymentMode';

export const PromptLibrary: React.FC = () => {
  // Try to load Premium version with upload functionality
  if (isFullDeployment()) {
    const PremiumPromptLibrary = loadPromptLibraryWithUpload();
    return <PremiumPromptLibrary />;
  }

  // Fallback: Core version without upload
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">
          Prompt Library
        </h1>
        <p className="text-gray-600 mt-2">
          Verwalte System- und User-Prompts für KI-Agents
        </p>
      </div>

      {/* Prompt Management Component */}
      <div className="card p-6">
        <PromptManagement />
      </div>
    </div>
  );
};
