/**
 * Role Management Page Component
 * Main page for managing roles and permissions
 */

import React, { useState } from 'react';
import { Container, Box, Typography } from '@mui/material';
import { Role } from '../../types/rbac';
import RoleList from './RoleList';
import RoleEditorDialog from './RoleEditorDialog';

const RoleManagementPage: React.FC = () => {
  const [editorOpen, setEditorOpen] = useState(false);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleCreateRole = () => {
    setSelectedRole(null);
    setEditorOpen(true);
  };

  const handleEditRole = (role: Role) => {
    setSelectedRole(role);
    setEditorOpen(true);
  };

  const handleCloseEditor = () => {
    setEditorOpen(false);
    setSelectedRole(null);
  };

  const handleSaveRole = () => {
    setRefreshKey(prev => prev + 1); // Trigger refresh
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Box mb={4}>
        <Typography variant="h4" component="h1" gutterBottom>
          Rollen & Berechtigungen
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Verwalten Sie Rollen und deren Feature-Zuordnungen für Ihr Team.
        </Typography>
      </Box>

      <RoleList
        key={refreshKey}
        onEditRole={handleEditRole}
        onCreateRole={handleCreateRole}
      />

      <RoleEditorDialog
        open={editorOpen}
        role={selectedRole}
        onClose={handleCloseEditor}
        onSave={handleSaveRole}
      />
    </Container>
  );
};

export default RoleManagementPage;
