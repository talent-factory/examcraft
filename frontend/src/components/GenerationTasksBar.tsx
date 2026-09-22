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
import { translateError } from '../errors';
import type { GenerationTaskState } from '../types';

const AUTO_HIDE_DELAY_MS = 30_000;

interface ContextLimit {
  requested: number | null;
  generated: number | null;
}

/**
 * TF-736: requested and generated question counts of a SUCCESS that produced
 * fewer questions than asked for, because the document material ran out.
 * `null` for every other task. Decided by the `context_limited` boolean,
 * never by the presence of a notice text. The live result's quality_metrics
 * win; the job-row values from the result endpoint cover an expired Celery
 * result. Relies on `result` and `contextLimited`/`generatedQuestionCount`
 * always being refreshed together (true today — see GenerationTasksContext's
 * recovery effect) — do not update one without the other.
 */
const contextLimitOf = (task: GenerationTaskState): ContextLimit | null => {
  if (task.status !== 'SUCCESS') return null;
  const metrics = task.result?.quality_metrics;
  if (metrics?.context_limited === true) {
    return {
      requested: metrics.requested_question_count ?? task.questionCount,
      generated: metrics.generated_question_count ?? null,
    };
  }
  if (task.contextLimited === true) {
    return { requested: task.questionCount, generated: task.generatedQuestionCount ?? null };
  }
  return null;
};

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
      setRetryError({ taskId, message: translateError(err, t, 'errors.rag.retryFailed') });
    } finally {
      setRetryingTaskId(null);
    }
  };
  const [visible, setVisible] = useState(true);
  const hideTimerRef = useRef<NodeJS.Timeout | null>(null);
  const loggedMissingMessageIds = useRef<Set<string>>(new Set());

  // Log once per task when a FAILURE/REVOKED arrives without a usable message
  // so the i18n fallback "errorOccurred" cannot silently mask a backend bug.
  // Tracked in a ref to avoid log-spam if completedTasks re-renders.
  useEffect(() => {
    completedTasks.forEach((task) => {
      const isFailure = task.status === 'FAILURE' || task.status === 'REVOKED';
      if (isFailure && !task.message && !loggedMissingMessageIds.current.has(task.taskId)) {
        loggedMissingMessageIds.current.add(task.taskId);
        console.warn('[GenerationTasks] Terminal task has no error message', {
          taskId: task.taskId,
          status: task.status,
        });
      }
    });
  }, [completedTasks]);

  // Auto-hide 30s after all tasks complete — but never while a task needs the
  // user's attention: a FAILURE/REVOKED, or a SUCCESS that produced fewer
  // questions than requested (TF-736). Those stay until explicitly dismissed.
  // `mustStayVisible` is a dependency because on recovery after a reload the
  // result arrives in a second step, without changing either list length —
  // the timer started for the bare task must then be cancelled.
  const mustStayVisible = completedTasks.some(
    (task) => task.status === 'FAILURE' || task.status === 'REVOKED' || contextLimitOf(task) !== null
  );
  useEffect(() => {
    if (activeTasks.length === 0 && completedTasks.length > 0 && !mustStayVisible) {
      hideTimerRef.current = setTimeout(() => {
        setVisible(false);
      }, AUTO_HIDE_DELAY_MS);
    } else if (activeTasks.length > 0 || mustStayVisible) {
      // Reset visibility and clear timer when a new active task appears, or
      // when a stay-visible reason (eg the context-limited notice) shows up
      // AFTER the panel already auto-hid — the second recovery roundtrip can
      // land past AUTO_HIDE_DELAY_MS, and the notice must still surface.
      // Safe to always bring back: an explicit dismiss (`dismissTask`) drops
      // the task from `completedTasks`, so a user-closed panel can't be
      // reopened by this branch.
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
  }, [activeTasks.length, completedTasks.length, mustStayVisible]);

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
        // 88 = HelpWidget FAB (right: 24 + 56px width, help/HelpWidget.tsx) + 8px gap,
        // so this panel doesn't disappear under the FAB (TF-506).
        right: 88,
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
            const contextLimit = contextLimitOf(task);

            return (
              <Box
                key={task.taskId}
                data-testid={isSuccess ? 'generation-task-success' : undefined}
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
                  <>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <CheckCircleIcon fontSize="small" color="success" />
                      <Typography variant="caption" color="success.main">
                        {t('components.generationTasks.clickToView')}
                      </Typography>
                    </Box>
                    {/* TF-358/TF-736: fewer questions than requested because the
                        document material ran out. Built from the counts in the
                        user's language — the backend's context_limited_notice
                        is German only. */}
                    {contextLimit && (
                      <Box
                        data-testid="generation-task-context-limited"
                        sx={{ display: 'flex', alignItems: 'flex-start', gap: 0.5, mt: 0.5 }}
                      >
                        <WarningIcon fontSize="small" color="warning" sx={{ mt: '2px' }} />
                        <Box>
                          <Typography
                            variant="caption"
                            color="warning.main"
                            sx={{ display: 'block', fontWeight: 600 }}
                          >
                            {t('components.generationTasks.contextLimitedTitle')}
                          </Typography>
                          {contextLimit.generated !== null && contextLimit.requested !== null && (
                            <Typography variant="caption" color="warning.main" sx={{ display: 'block' }}>
                              {t('components.generationTasks.contextLimitedBody', {
                                generated: contextLimit.generated,
                                requested: contextLimit.requested,
                              })}
                            </Typography>
                          )}
                          <Typography variant="caption" color="warning.main" sx={{ display: 'block' }}>
                            {t('components.generationTasks.contextLimitedAction')}
                          </Typography>
                        </Box>
                      </Box>
                    )}
                  </>
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
