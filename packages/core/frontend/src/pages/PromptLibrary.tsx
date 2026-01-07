/**
 * Prompt Library Page
 * Prompt management and library for admins and teachers
 */

import React from 'react';
import { PromptManagement } from '../components/admin/PromptManagement';

export const PromptLibrary: React.FC = () => {
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
