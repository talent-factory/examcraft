/**
 * GenerationTasksBar
 * Fixed-position global component showing active and recently completed generation tasks.
 */

import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Collapse,
  IconButton,
  LinearProgress,
  Paper,
  Typography,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import ReplayIcon from '@mui/icons-material/Replay';
import WarningIcon from '@mui/icons-material/Warning';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CloseIcon from '@mui/icons-material/Close';
import { useTranslation } from 'react-i18next';
import { useGenerationTasks } from '../contexts/GenerationTasksContext';
import type { GenerationTaskState } from '../types';

const AUTO_HIDE_DELAY_MS = 30_000;

const GenerationTasksBar: React.FC = () => {
  const { t } = useTranslation();
  const { activeTasks, completedTasks, dismissTask, retryTask } = useGenerationTasks();
  const navigate = useNavigate();
  const [expanded, setExpanded] = useState(true);
  const [retryingTaskId, setRetryingTaskId] = useState<string | null>(null);

  const [retryError, setRetryError] = useState<{ taskId: string; message: string } | null>(null);

  const handleRetry = async (taskId: string) => {
    try {
      setRetryingTaskId(taskId);
      setRetryError(null);
      await retryTask(taskId);
    } catch (err) {
      console.error('[GenerationTasks] Retry failed:', err);
      setRetryError({ taskId, message: err instanceof Error ? err.message : String(err) });
    } finally {
      setRetryingTaskId(null);
    }
  };
  const [visible, setVisible] = useState(true);
  const hideTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Auto-hide 30s after all tasks complete
  useEffect(() => {
    if (activeTasks.length === 0 && completedTasks.length > 0) {
      hideTimerRef.current = setTimeout(() => {
        setVisible(false);
      }, AUTO_HIDE_DELAY_MS);
    } else if (activeTasks.length > 0) {
      // Reset visibility and clear timer when new active task appears
      setVisible(true);
      if (hideTimerRef.current) {
        clearTimeout(hideTimerRef.current);
        hideTimerRef.current = null;
      }
    }

    return () => {
      if (hideTimerRef.current) {
        clearTimeout(hideTimerRef.current);
        hideTimerRef.current = null;
      }
    };
  }, [activeTasks.length, completedTasks.length]);

  const handleTaskClick = (task: GenerationTaskState) => {
    if (task.status === 'SUCCESS') {
      navigate('/questions/generate', { state: { viewTaskId: task.taskId } });
    }
  };

  const allTasks = [...activeTasks, ...completedTasks];

  if (!visible || allTasks.length === 0) {
    return null;
  }

  return (
    <Paper
      elevation={6}
      sx={{
        position: 'fixed',
        bottom: 16,
        right: 16,
        zIndex: 1300,
        width: 320,
        borderRadius: 2,
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <Box
        sx={{
          bgcolor: 'primary.main',
          color: 'white',
          px: 2,
          py: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
          {t('components.generationTasks.title', { count: activeTasks.length })}
        </Typography>
        <IconButton
          size="small"
          onClick={() => setExpanded((prev) => !prev)}
          sx={{ color: 'white', p: 0.5 }}
          aria-label={expanded ? t('components.generationTasks.collapse') : t('components.generationTasks.expand')}
        >
          {expanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
        </IconButton>
      </Box>

      {/* Task list */}
      <Collapse in={expanded}>
        <Box sx={{ maxHeight: 320, overflowY: 'auto' }}>
          {allTasks.map((task) => {
            const isTerminal =
              task.status === 'SUCCESS' || task.status === 'FAILURE' || task.status === 'REVOKED';
            const isSuccess = task.status === 'SUCCESS';
            const isFailure = task.status === 'FAILURE' || task.status === 'REVOKED';
            const isUnknown = task.status === 'UNKNOWN';

            return (
              <Box
                key={task.taskId}
                onClick={isSuccess ? () => handleTaskClick(task) : undefined}
                sx={{
                  px: 2,
                  py: 1.5,
                  borderBottom: '1px solid',
                  borderColor: 'divider',
                  cursor: isSuccess ? 'pointer' : 'default',
                  '&:hover': isSuccess
                    ? { bgcolor: 'action.hover' }
                    : undefined,
                  '&:last-child': { borderBottom: 'none' },
                }}
              >
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    mb: 0.5,
                  }}
                >
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: 500,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      flex: 1,
                      mr: 1,
                    }}
                  >
                    {task.topic || t('components.generationTasks.defaultTopic')}
                  </Typography>

                  {(isTerminal || isUnknown) && (
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        dismissTask(task.taskId);
                      }}
                      sx={{ p: 0.25 }}
                      aria-label={t('components.generationTasks.close')}
                    >
                      <CloseIcon fontSize="small" />
                    </IconButton>
                  )}
                </Box>

                {/* Unknown status: connection lost — task may still be running on backend */}
                {isUnknown && (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <WarningIcon fontSize="small" color="warning" />
                    <Typography variant="caption" color="warning.main">
                      {t('components.generationTasks.connectionLost')}
                    </Typography>
                  </Box>
                )}

                {/* Active task: progress bar */}
                {!isTerminal && !isUnknown && (
                  <>
                    <LinearProgress
                      variant="determinate"
                      value={task.progress ?? 0}
                      sx={{ mb: 0.5, borderRadius: 1 }}
                    />
                    <Typography variant="caption" color="text.secondary">
                      {task.progress ?? 0}%
                      {task.message ? ` – ${task.message}` : ''}
                    </Typography>
                  </>
                )}

                {/* Completed task: green checkmark */}
                {isSuccess && (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <CheckCircleIcon fontSize="small" color="success" />
                    <Typography variant="caption" color="success.main">
                      {t('components.generationTasks.clickToView')}
                    </Typography>
                  </Box>
                )}

                {/* Failed task: red X + error message + retry button */}
                {isFailure && (
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flex: 1, minWidth: 0 }}>
                      <ErrorIcon fontSize="small" color="error" />
                      <Typography
                        variant="caption"
                        color="error"
                        sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                      >
                        {task.message || t('components.generationTasks.errorOccurred')}
                      </Typography>
                    </Box>
                    <IconButton
                      size="small"
                      onClick={(e) => { e.stopPropagation(); handleRetry(task.taskId); }}
                      disabled={retryingTaskId === task.taskId}
                      sx={{ p: 0.25, ml: 0.5 }}
                      aria-label={t('components.generationTasks.retry')}
                      title={t('components.generationTasks.retry')}
                    >
                      <ReplayIcon fontSize="small" color="primary" />
                    </IconButton>
                  </Box>
                )}

                {/* Retry error feedback */}
                {retryError && retryError.taskId === task.taskId && retryingTaskId === null && isFailure && (
                  <Typography variant="caption" color="error" sx={{ display: 'block', mt: 0.5 }}>
                    {retryError.message}
                  </Typography>
                )}
              </Box>
            );
          })}
        </Box>
      </Collapse>
    </Paper>
  );
};

export default GenerationTasksBar;
