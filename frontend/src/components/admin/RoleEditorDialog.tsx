/**
 * Role Editor Dialog Component
 * Create or edit roles with feature assignments
 */

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormGroup,
  FormControlLabel,
  Checkbox,
  Typography,
  Box,
  Alert,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon
} from '@mui/icons-material';
import { Role, Feature, CreateRoleRequest, UpdateRoleFeaturesRequest, FEATURE_CATEGORIES } from '../../types/rbac';
import RBACService from '../../services/RBACService';

interface RoleEditorDialogProps {
  open: boolean;
  role: Role | null; // null = create new role
  onClose: () => void;
  onSave: () => void;
}

const RoleEditorDialog: React.FC<RoleEditorDialogProps> = ({
  open,
  role,
  onClose,
  onSave
}) => {
  const [name, setName] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [description, setDescription] = useState('');
  const [selectedFeatures, setSelectedFeatures] = useState<string[]>([]);
  const [allFeatures, setAllFeatures] = useState<Feature[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingFeatures, setLoadingFeatures] = useState(true);

  const isEditMode = role !== null;

  useEffect(() => {
    if (open) {
      loadFeatures();
      if (role) {
        setName(role.name);
        setDisplayName(role.display_name);
        setDescription(role.description || '');
        setSelectedFeatures(role.features.map(f => f.id));
      } else {
        resetForm();
      }
    }
  }, [open, role]);

  const loadFeatures = async () => {
    try {
      setLoadingFeatures(true);
      const features = await RBACService.listFeatures();
      setAllFeatures(features);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load features');
    } finally {
      setLoadingFeatures(false);
    }
  };

  const resetForm = () => {
    setName('');
    setDisplayName('');
    setDescription('');
    setSelectedFeatures([]);
    setError(null);
  };

  const handleFeatureToggle = (featureId: string) => {
    setSelectedFeatures(prev =>
      prev.includes(featureId)
        ? prev.filter(id => id !== featureId)
        : [...prev, featureId]
    );
  };

  const handleSelectAllInCategory = (category: string) => {
    const categoryFeatures = allFeatures
      .filter(f => (f.category || 'other') === category)
      .map(f => f.id);

    const allSelected = categoryFeatures.every(id => selectedFeatures.includes(id));

    if (allSelected) {
      setSelectedFeatures(prev => prev.filter(id => !categoryFeatures.includes(id)));
    } else {
      // Merge arrays and remove duplicates without using Set spread
      setSelectedFeatures(prev => {
        const merged = [...prev, ...categoryFeatures];
        return merged.filter((id, index) => merged.indexOf(id) === index);
      });
    }
  };

  const handleSubmit = async () => {
    try {
      setLoading(true);
      setError(null);

      if (isEditMode && role) {
        // Update existing role
        const updateData: UpdateRoleFeaturesRequest = {
          feature_ids: selectedFeatures
        };
        await RBACService.updateRoleFeatures(role.id, updateData);
      } else {
        // Create new role
        const createData: CreateRoleRequest = {
          name,
          display_name: displayName,
          description: description || undefined,
          feature_ids: selectedFeatures
        };
        await RBACService.createRole(createData);
      }

      onSave();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save role');
    } finally {
      setLoading(false);
    }
  };

  const validateForm = (): boolean => {
    if (!isEditMode) {
      if (!name || !displayName) return false;
      if (!/^[a-z0-9_]+$/.test(name)) return false;
    }
    return selectedFeatures.length > 0;
  };

  const groupedFeatures = allFeatures.reduce((acc, feature) => {
    const category = feature.category || 'other';
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(feature);
    return acc;
  }, {} as Record<string, Feature[]>);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        {isEditMode ? `Rolle bearbeiten: ${role?.display_name}` : 'Neue Rolle erstellen'}
      </DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {!isEditMode && (
          <Box mb={3}>
            <TextField
              fullWidth
              label="Rollen-Name (technisch)"
              value={name}
              onChange={(e) => setName(e.target.value.toLowerCase())}
              placeholder="z.B. custom_reviewer"
              helperText="Nur Kleinbuchstaben, Zahlen und Unterstriche"
              required
              disabled={loading}
              sx={{ mb: 2 }}
            />
            <TextField
              fullWidth
              label="Anzeigename"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="z.B. Custom Reviewer"
              required
              disabled={loading}
              sx={{ mb: 2 }}
            />
            <TextField
              fullWidth
              label="Beschreibung"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optionale Beschreibung der Rolle"
              multiline
              rows={2}
              disabled={loading}
            />
          </Box>
        )}

        <Typography variant="h6" gutterBottom>
          Features zuordnen ({selectedFeatures.length} ausgewählt)
        </Typography>

        {loadingFeatures ? (
          <Box display="flex" justifyContent="center" py={4}>
            <CircularProgress />
          </Box>
        ) : (
          <Box>
            {Object.entries(groupedFeatures).map(([category, features]) => {
              const categorySelected = features.filter(f => selectedFeatures.includes(f.id)).length;
              const categoryTotal = features.length;

              return (
                <Accordion key={category} defaultExpanded>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Box display="flex" justifyContent="space-between" width="100%">
                      <Typography>
                        {FEATURE_CATEGORIES[category as keyof typeof FEATURE_CATEGORIES] || category}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mr: 2 }}>
                        {categorySelected} / {categoryTotal}
                      </Typography>
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Box>
                      <Button
                        size="small"
                        onClick={() => handleSelectAllInCategory(category)}
                        sx={{ mb: 1 }}
                      >
                        {categorySelected === categoryTotal ? 'Alle abwählen' : 'Alle auswählen'}
                      </Button>
                      <FormGroup>
                        {features.map((feature) => (
                          <FormControlLabel
                            key={feature.id}
                            control={
                              <Checkbox
                                checked={selectedFeatures.includes(feature.id)}
                                onChange={() => handleFeatureToggle(feature.id)}
                                disabled={loading}
                              />
                            }
                            label={
                              <Box>
                                <Typography variant="body2">{feature.display_name}</Typography>
                                {feature.description && (
                                  <Typography variant="caption" color="text.secondary">
                                    {feature.description}
                                  </Typography>
                                )}
                              </Box>
                            }
                          />
                        ))}
                      </FormGroup>
                    </Box>
                  </AccordionDetails>
                </Accordion>
              );
            })}
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          Abbrechen
        </Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          color="primary"
          disabled={loading || !validateForm()}
        >
          {loading ? <CircularProgress size={24} /> : isEditMode ? 'Speichern' : 'Erstellen'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default RoleEditorDialog;

