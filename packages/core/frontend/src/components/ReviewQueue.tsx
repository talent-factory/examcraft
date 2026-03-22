/**
 * ReviewQueue Component
 * Main component for question review workflow
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Button,
  Stack,
  Alert,
  CircularProgress,
  Pagination,
  Card,
  CardContent,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  FilterList,
  Refresh,
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { ReviewService } from '../services/ReviewService';
import {
  QuestionReview,
  ReviewFilters,
  ReviewStatus,
  ReviewActionRequest,
  CommentCreateRequest,
  QuestionReviewUpdateRequest,
} from '../types/review';
import QuestionReviewCard from './QuestionReviewCard';
import QuestionEditor from './QuestionEditor';

const ReviewQueue: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [questions, setQuestions] = useState<QuestionReview[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Statistics
  const [stats, setStats] = useState({
    total: 0,
    pending: 0,
    approved: 0,
    rejected: 0,
    in_review: 0,
  });

  // Filters
  const [filters, setFilters] = useState<ReviewFilters>({
    status: undefined,
    difficulty: undefined,
    question_type: undefined,
    limit: 20,
    offset: 0,
  });

  // Pagination
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Editor Dialog
  const [editorOpen, setEditorOpen] = useState(false);
  const [selectedQuestion, setSelectedQuestion] = useState<QuestionReview | null>(null);

  // Comment Dialog
  const [commentDialogOpen, setCommentDialogOpen] = useState(false);
  const [commentText, setCommentText] = useState('');
  const [commentQuestionId, setCommentQuestionId] = useState<number | null>(null);

  // Action Dialog
  const [actionDialogOpen, setActionDialogOpen] = useState(false);
  const [actionType, setActionType] = useState<'approve' | 'reject' | null>(null);
  const [actionQuestionId, setActionQuestionId] = useState<number | null>(null);
  const [actionReason, setActionReason] = useState('');

  // Load questions
  const loadQuestions = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await ReviewService.getReviewQueue(filters);
      setQuestions(response.questions);
      setStats({
        total: response.total,
        pending: response.pending,
        approved: response.approved,
        rejected: response.rejected,
        in_review: response.in_review,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load questions');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadQuestions();
  }, [loadQuestions]);

  const handleFilterChange = (field: keyof ReviewFilters, value: any) => {
    setFilters(prev => ({ ...prev, [field]: value, offset: 0 }));
    setPage(1);
  };

  const handlePageChange = (_event: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
    setFilters(prev => ({ ...prev, offset: (value - 1) * pageSize }));
  };

  const handleStartReview = async (questionId: number) => {
    try {
      setLoading(true);
      await ReviewService.startReview(questionId);
      navigate(`/questions/review/${questionId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Starten des Reviews');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = (questionId: number) => {
    setActionQuestionId(questionId);
    setActionType('approve');
    setActionDialogOpen(true);
  };

  const handleReject = (questionId: number) => {
    setActionQuestionId(questionId);
    setActionType('reject');
    setActionDialogOpen(true);
  };

  const handleEdit = (questionId: number) => {
    const question = questions.find(q => q.id === questionId);
    if (question) {
      setSelectedQuestion(question);
      setEditorOpen(true);
    }
  };

  const handleComment = (questionId: number) => {
    setCommentQuestionId(questionId);
    setCommentDialogOpen(true);
  };

  const executeAction = async () => {
    if (!actionQuestionId || !actionType) return;

    setLoading(true);
    try {
      const request: ReviewActionRequest = {
        reason: actionReason || undefined,
      };

      if (actionType === 'approve') {
        await ReviewService.approveQuestion(actionQuestionId, request);
      } else {
        await ReviewService.rejectQuestion(actionQuestionId, request);
      }

      setActionDialogOpen(false);
      setActionReason('');
      await loadQuestions();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Action failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveEdit = async (questionId: number, updates: QuestionReviewUpdateRequest) => {
    setLoading(true);
    try {
      await ReviewService.editQuestion(questionId, updates);
      setEditorOpen(false);
      await loadQuestions();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save changes');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const handleAddComment = async () => {
    if (!commentQuestionId || !commentText.trim()) return;

    setLoading(true);
    try {
      const request: CommentCreateRequest = {
        comment_text: commentText,
        comment_type: 'general' as any,
      };

      await ReviewService.addComment(commentQuestionId, request);
      setCommentDialogOpen(false);
      setCommentText('');
      await loadQuestions();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add comment');
    } finally {
      setLoading(false);
    }
  };

  const totalPages = Math.ceil(stats.total / pageSize);

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          {t('components.reviewQueue.title')}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {t('components.reviewQueue.subtitle')}
        </Typography>
      </Box>

      {/* Statistics */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={2.4}>
          <Card>
            <CardContent>
              <Typography variant="h4">{stats.total}</Typography>
              <Typography variant="body2" color="text.secondary">{t('components.reviewQueue.statsTotal')}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <Card sx={{ bgcolor: 'warning.light' }}>
            <CardContent>
              <Typography variant="h4">{stats.pending}</Typography>
              <Typography variant="body2">{t('components.reviewQueue.statsPending')}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <Card sx={{ bgcolor: 'success.light' }}>
            <CardContent>
              <Typography variant="h4">{stats.approved}</Typography>
              <Typography variant="body2">{t('components.reviewQueue.statsApproved')}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <Card sx={{ bgcolor: 'error.light' }}>
            <CardContent>
              <Typography variant="h4">{stats.rejected}</Typography>
              <Typography variant="body2">{t('components.reviewQueue.statsRejected')}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <Card sx={{ bgcolor: 'info.light' }}>
            <CardContent>
              <Typography variant="h4">{stats.in_review}</Typography>
              <Typography variant="body2">{t('components.reviewQueue.statsInReview')}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap" useFlexGap>
          <FilterList />
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>{t('components.reviewQueue.filterStatus')}</InputLabel>
            <Select
              value={filters.status || ''}
              onChange={(e) => handleFilterChange('status', e.target.value || undefined)}
              label={t('components.reviewQueue.filterStatus')}
            >
              <MenuItem value="">{t('components.reviewQueue.filterAll')}</MenuItem>
              <MenuItem value={ReviewStatus.PENDING}>{t('components.reviewQueue.filterPending')}</MenuItem>
              <MenuItem value={ReviewStatus.APPROVED}>{t('components.reviewQueue.filterApproved')}</MenuItem>
              <MenuItem value={ReviewStatus.REJECTED}>{t('components.reviewQueue.filterRejected')}</MenuItem>
              <MenuItem value={ReviewStatus.EDITED}>{t('components.reviewQueue.filterEdited')}</MenuItem>
              <MenuItem value={ReviewStatus.IN_REVIEW}>{t('components.reviewQueue.filterInReview')}</MenuItem>
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>{t('components.reviewQueue.filterDifficulty')}</InputLabel>
            <Select
              value={filters.difficulty || ''}
              onChange={(e) => handleFilterChange('difficulty', e.target.value || undefined)}
              label={t('components.reviewQueue.filterDifficulty')}
            >
              <MenuItem value="">{t('components.reviewQueue.filterAll')}</MenuItem>
              <MenuItem value="easy">{t('components.reviewQueue.filterEasy')}</MenuItem>
              <MenuItem value="medium">{t('components.reviewQueue.filterMedium')}</MenuItem>
              <MenuItem value="hard">{t('components.reviewQueue.filterHard')}</MenuItem>
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>{t('components.reviewQueue.filterQuestionType')}</InputLabel>
            <Select
              value={filters.question_type || ''}
              onChange={(e) => handleFilterChange('question_type', e.target.value || undefined)}
              label={t('components.reviewQueue.filterQuestionType')}
            >
              <MenuItem value="">{t('components.reviewQueue.filterAll')}</MenuItem>
              <MenuItem value="multiple_choice">{t('components.reviewQueue.filterMultipleChoice')}</MenuItem>
              <MenuItem value="open_ended">{t('components.reviewQueue.filterOpenEnded')}</MenuItem>
              <MenuItem value="true_false">{t('components.reviewQueue.filterTrueFalse')}</MenuItem>
            </Select>
          </FormControl>

          <Box sx={{ flexGrow: 1 }} />

          <Tooltip title={t('components.reviewQueue.refresh')}>
            <IconButton onClick={loadQuestions} disabled={loading}>
              <Refresh />
            </IconButton>
          </Tooltip>
        </Stack>
      </Paper>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Loading */}
      {loading && questions.length === 0 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {/* Questions List */}
      {!loading && questions.length === 0 && (
        <Alert severity="info">
          {t('components.reviewQueue.noQuestions')}
        </Alert>
      )}

      {questions.map((question) => (
        <QuestionReviewCard
          key={question.id}
          question={question}
          onStartReview={handleStartReview}
          onApprove={handleApprove}
          onReject={handleReject}
          onEdit={handleEdit}
          onComment={handleComment}
          loading={loading}
        />
      ))}

      {/* Pagination */}
      {totalPages > 1 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
          <Pagination
            count={totalPages}
            page={page}
            onChange={handlePageChange}
            color="primary"
            disabled={loading}
          />
        </Box>
      )}

      {/* Editor Dialog */}
      {selectedQuestion && (
        <QuestionEditor
          question={selectedQuestion}
          open={editorOpen}
          onClose={() => setEditorOpen(false)}
          onSave={handleSaveEdit}
          loading={loading}
        />
      )}

      {/* Comment Dialog */}
      <Dialog open={commentDialogOpen} onClose={() => setCommentDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{t('components.reviewQueue.addComment')}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            multiline
            rows={4}
            fullWidth
            label={t('components.reviewQueue.commentLabel')}
            value={commentText}
            onChange={(e) => setCommentText(e.target.value)}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCommentDialogOpen(false)}>{t('components.reviewQueue.cancelBtn')}</Button>
          <Button onClick={handleAddComment} variant="contained" disabled={!commentText.trim() || loading}>
            {t('components.reviewQueue.addCommentBtn')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Action Dialog */}
      <Dialog open={actionDialogOpen} onClose={() => setActionDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {actionType === 'approve' ? t('components.reviewQueue.approveTitle') : t('components.reviewQueue.rejectTitle')}
        </DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            multiline
            rows={3}
            fullWidth
            label={t('components.reviewQueue.reasonLabel')}
            value={actionReason}
            onChange={(e) => setActionReason(e.target.value)}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setActionDialogOpen(false)}>{t('components.reviewQueue.cancelBtn')}</Button>
          <Button
            onClick={executeAction}
            variant="contained"
            color={actionType === 'approve' ? 'success' : 'error'}
            disabled={loading}
          >
            {actionType === 'approve' ? t('components.reviewQueue.approve') : t('components.reviewQueue.reject')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ReviewQueue;
