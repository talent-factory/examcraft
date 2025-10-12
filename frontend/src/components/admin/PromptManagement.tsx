import React, { useState } from 'react';
import { PromptLibrary } from './PromptLibrary';
import { PromptEditor } from './PromptEditor';
import { PromptVersionHistory } from './PromptVersionHistory';
import { PromptUsageChart } from './PromptUsageChart';
import { Box, Paper, Tabs, Tab } from '@mui/material';
import { LibraryBooks, Edit, History, BarChart } from '@mui/icons-material';

type ViewMode = 'library' | 'editor' | 'versions' | 'analytics';

export const PromptManagement: React.FC = () => {
  const [viewMode, setViewMode] = useState<ViewMode>('library');
  const [selectedPromptId, setSelectedPromptId] = useState<string | undefined>();
  const [selectedPromptName, setSelectedPromptName] = useState<string>('');

  const handleEditPrompt = (promptId: string) => {
    setSelectedPromptId(promptId);
    setViewMode('editor');
  };

  const handleCreateNew = () => {
    setSelectedPromptId(undefined);
    setViewMode('editor');
  };

  const handleSaveComplete = () => {
    setViewMode('library');
    setSelectedPromptId(undefined);
  };

  const handleCancel = () => {
    setViewMode('library');
    setSelectedPromptId(undefined);
  };

  const handleShowVersions = (promptName: string) => {
    setSelectedPromptName(promptName);
    setViewMode('versions');
  };

  const handleShowAnalytics = (promptId: string) => {
    setSelectedPromptId(promptId);
    setViewMode('analytics');
  };

  const handleBackToLibrary = () => {
    setViewMode('library');
    setSelectedPromptId(undefined);
    setSelectedPromptName('');
  };

  return (
    <Box>
      {viewMode === 'library' && (
        <PromptLibrary
          onEditPrompt={handleEditPrompt}
          onCreateNew={handleCreateNew}
        />
      )}

      {viewMode === 'editor' && (
        <PromptEditor
          promptId={selectedPromptId}
          onSave={handleSaveComplete}
          onCancel={handleCancel}
        />
      )}

      {viewMode === 'versions' && (
        <PromptVersionHistory
          promptName={selectedPromptName}
          onBack={handleBackToLibrary}
        />
      )}

      {viewMode === 'analytics' && selectedPromptId && (
        <Box sx={{ p: 4 }}>
          <PromptUsageChart promptId={selectedPromptId} />
        </Box>
      )}
    </Box>
  );
};

