import React, { useState } from 'react';
import { PromptLibrary } from './PromptLibrary';
import { PromptEditor } from './PromptEditor';
import { PromptVersionHistory } from './PromptVersionHistory';
import { PromptUsageChart } from './PromptUsageChart';
import { SemanticSearchTester } from './SemanticSearchTester';
import { Box, Paper, Tabs, Tab } from '@mui/material';
import { LibraryBooks, Search } from '@mui/icons-material';

type ViewMode = 'library' | 'editor' | 'versions' | 'analytics' | 'search';

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

  const handleBackToLibrary = () => {
    setViewMode('library');
    setSelectedPromptId(undefined);
    setSelectedPromptName('');
  };

  return (
    <Box>
      {/* Tab Navigation for different views */}
      {viewMode === 'library' && (
        <Box>
          <Paper elevation={2} sx={{ mb: 3 }}>
            <Tabs value={0} variant="fullWidth">
              <Tab label="Prompt Library" icon={<LibraryBooks />} />
              <Tab
                label="Semantic Search"
                icon={<Search />}
                onClick={() => setViewMode('search')}
              />
            </Tabs>
          </Paper>
          <PromptLibrary
            onEditPrompt={handleEditPrompt}
            onCreateNew={handleCreateNew}
            onShowVersions={handleShowVersions}
          />
        </Box>
      )}

      {viewMode === 'search' && (
        <Box>
          <Paper elevation={2} sx={{ mb: 3 }}>
            <Tabs value={1} variant="fullWidth">
              <Tab
                label="Prompt Library"
                icon={<LibraryBooks />}
                onClick={() => setViewMode('library')}
              />
              <Tab label="Semantic Search" icon={<Search />} />
            </Tabs>
          </Paper>
          <SemanticSearchTester />
        </Box>
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
