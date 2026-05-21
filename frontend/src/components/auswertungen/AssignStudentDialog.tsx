/**
 * AssignStudentDialog — Studi suchen + zur Klasse zuweisen
 * (TF-336 G2).
 *
 * Search debounce on input; the backend's ``/api/v1/students``
 * already filters server-side by ``external_id`` and ``display_name``.
 */

import React, { useEffect, useState } from 'react';
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  List,
  ListItemButton,
  ListItemText,
  TextField,
  CircularProgress,
  Box,
  Typography,
} from '@mui/material';
import { useTranslation } from 'react-i18next';

import { ApiError } from '../../services/submissionsService';
import { StudentClassesService } from '../../services/studentClassesService';
import { StudentsService } from '../../services/studentsService';
import type { StudentListItem } from '../../types/student';

interface Props {
  open: boolean;
  classId: number;
  onClose: () => void;
  onAssigned: () => void;
}

const SEARCH_DEBOUNCE_MS = 250;

const AssignStudentDialog: React.FC<Props> = ({
  open,
  classId,
  onClose,
  onAssigned,
}) => {
  const { t } = useTranslation();
  const [search, setSearch] = useState('');
  const [items, setItems] = useState<StudentListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    const handle = setTimeout(() => {
      setLoading(true);
      setError(null);
      StudentsService.list({ search: search || undefined, limit: 50 })
        .then((res) => {
          if (cancelled) return;
          setItems(res.items);
        })
        .catch((err) => {
          if (cancelled) return;
          // Surface the failure: a silent fallback to "no results" lets
          // the user think the student doesn't exist and create a
          // duplicate. 4xx (incl. 403/permissions) carries a message
          // worth showing; everything else gets a generic retry hint.
          setItems([]);
          setError(
            err instanceof ApiError
              ? err.message
              : t('auswertungen.klassen.assignDialog.searchError'),
          );
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }, SEARCH_DEBOUNCE_MS);
    return () => {
      cancelled = true;
      clearTimeout(handle);
    };
  }, [search, open, t]);

  const handleAssign = async (studentId: number) => {
    setSubmitting(true);
    setError(null);
    try {
      await StudentClassesService.addMember(classId, studentId);
      onAssigned();
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError(t('auswertungen.klassen.assignDialog.duplicate'));
      } else if (err instanceof ApiError) {
        setError(err.message);
      } else {
        // Non-ApiError = network / parse failure. Showing the duplicate
        // text here would mislead the user into thinking the assignment
        // was rejected by the server.
        setError(t('auswertungen.klassen.assignDialog.assignError'));
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>{t('auswertungen.klassen.assignDialog.title')}</DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        <TextField
          autoFocus
          fullWidth
          label={t('auswertungen.klassen.assignDialog.searchLabel')}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          inputProps={{ 'data-testid': 'assign-student-search' }}
          sx={{ mb: 2 }}
        />
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
            <CircularProgress size={20} />
            <Typography sx={{ ml: 1 }} variant="body2">
              {t('auswertungen.klassen.assignDialog.loading')}
            </Typography>
          </Box>
        ) : items.length === 0 ? (
          <Typography color="text.secondary" variant="body2">
            {t('auswertungen.klassen.assignDialog.noMatch')}
          </Typography>
        ) : (
          <List dense data-testid="assign-student-results">
            {items.map((s) => (
              <ListItemButton
                key={s.id}
                disabled={submitting}
                onClick={() => handleAssign(s.id)}
                data-testid={`assign-student-${s.id}`}
              >
                <ListItemText
                  primary={s.display_name || s.external_id}
                  secondary={s.external_id}
                />
              </ListItemButton>
            ))}
          </List>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>
          {t('auswertungen.klassen.assignDialog.cancel')}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default AssignStudentDialog;
