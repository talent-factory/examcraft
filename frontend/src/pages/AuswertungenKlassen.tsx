/**
 * Class list (TF-336 G2).
 *
 * Table with all of the institution's classes + a "Klasse anlegen" (create
 * class) action. Clicking a row → /auswertungen/klassen/[classId].
 *
 * RBAC: the backend checks `students:manage` — forwarded errors are
 * surfaced via `ApiError.kind === 'permission'` (403/402).
 */

import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  IconButton,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import {
  Add as AddIcon,
  Class as ClassIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
} from '@mui/icons-material';

import { ApiError } from '../services/submissionsService';
import { StudentClassesService } from '../services/studentClassesService';
import type { StudentClassSummary } from '../types/studentClass';
import CreateClassDialog from '../components/auswertungen/CreateClassDialog';
import QuotaBanner, {
  isQuotaError,
} from '../components/auswertungen/QuotaBanner';

const AuswertungenKlassen: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [items, setItems] = useState<StudentClassSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [errorText, setErrorText] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [renameTarget, setRenameTarget] = useState<StudentClassSummary | null>(
    null,
  );

  const [reloadKey, setReloadKey] = useState(0);
  const reload = () => setReloadKey((k) => k + 1);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setErrorText(null);
    StudentClassesService.list({ limit: 200 })
      .then((res) => {
        if (cancelled) return;
        setItems(res.items);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError) {
          setError(err);
          setErrorText(err.message);
        } else {
          setErrorText(
            err instanceof Error
              ? err.message
              : t('auswertungen.klassen.loadError'),
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reloadKey]);

  const handleDelete = async (cls: StudentClassSummary) => {
    if (
      !window.confirm(
        t('auswertungen.klassen.deleteConfirm.body', { name: cls.name }),
      )
    ) {
      return;
    }
    try {
      await StudentClassesService.remove(cls.id);
      reload();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err);
        setErrorText(err.message);
      }
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 1 }}>
        <ClassIcon color="primary" />
        <Typography variant="h4" component="h1">
          {t('auswertungen.klassen.title')}
        </Typography>
        <Box sx={{ flexGrow: 1 }} />
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setCreateOpen(true)}
          data-testid="klassen-create"
        >
          {t('auswertungen.klassen.actionCreate')}
        </Button>
      </Box>

      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        {t('auswertungen.klassen.subtitle')}
      </Typography>

      {error && isQuotaError(error) && (
        <Box sx={{ mb: 2 }}>
          <QuotaBanner error={error} onDismiss={() => setError(null)} />
        </Box>
      )}
      {errorText && !(error && isQuotaError(error)) && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {errorText}
        </Alert>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      ) : items.length === 0 ? (
        <Alert severity="info">{t('auswertungen.klassen.emptyHint')}</Alert>
      ) : (
        <TableContainer component={Paper} data-testid="klassen-table">
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>{t('auswertungen.klassen.colName')}</TableCell>
                <TableCell>{t('auswertungen.klassen.colMembers')}</TableCell>
                <TableCell>{t('auswertungen.klassen.colCreated')}</TableCell>
                <TableCell align="right">
                  {t('auswertungen.klassen.colActions')}
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map((cls) => (
                <TableRow
                  key={cls.id}
                  hover
                  sx={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/auswertungen/klassen/${cls.id}`)}
                  data-testid={`klasse-${cls.id}`}
                >
                  <TableCell>{cls.name}</TableCell>
                  <TableCell>
                    <Chip size="small" label={cls.member_count} />
                  </TableCell>
                  <TableCell>
                    {new Date(cls.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                    <IconButton
                      size="small"
                      onClick={() => setRenameTarget(cls)}
                      title={t('auswertungen.klassen.actionRename')}
                      data-testid={`klasse-${cls.id}-rename`}
                    >
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => handleDelete(cls)}
                      title={t('auswertungen.klassen.actionDelete')}
                      data-testid={`klasse-${cls.id}-delete`}
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <CreateClassDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onSaved={() => reload()}
      />
      {renameTarget && (
        <CreateClassDialog
          open
          mode="rename"
          classId={renameTarget.id}
          initialName={renameTarget.name}
          onClose={() => setRenameTarget(null)}
          onSaved={() => {
            setRenameTarget(null);
            reload();
          }}
        />
      )}
    </Box>
  );
};

export default AuswertungenKlassen;
