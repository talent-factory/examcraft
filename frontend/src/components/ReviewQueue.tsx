/**
 * ReviewQueue Component
 * Main component for question review workflow
 */

import React, { useState, useEffect } from 'react';
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
  Chip,
  Stack,
  Alert,
  CircularProgress,
  Pagination,
  Card,
  CardContent,
  Divider,
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
  CheckCircle,
  Cancel,
  Edit,
  Comment as CommentIcon,
  Search,
} from '@mui/icons-material';
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
  const loadQuestions = async () => {
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
  };

  useEffect(() => {
    loadQuestions();
  }, [filters]);

  const handleFilterChange = (field: keyof ReviewFilters, value: any) => {
    setFilters(prev => ({ ...prev, [field]: value, offset: 0 }));
    setPage(1);
  };

  const handlePageChange = (_event: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
    setFilters(prev => ({ ...prev, offset: (value - 1) * pageSize }));
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
        reviewer_id: 'current_user', // TODO: Get from auth context
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
      await ReviewService.editQuestion(questionId, updates, 'current_user'); // TODO: Get from auth
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
        author: 'current_user', // TODO: Get from auth
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
          Question Review Queue
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Review and approve AI-generated exam questions
        </Typography>
      </Box>

      {/* Statistics */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={2.4}>
          <Card>
            <CardContent>
              <Typography variant="h4">{stats.total}</Typography>
              <Typography variant="body2" color="text.secondary">Total</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <Card sx={{ bgcolor: 'warning.light' }}>
            <CardContent>
              <Typography variant="h4">{stats.pending}</Typography>
              <Typography variant="body2">Pending</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <Card sx={{ bgcolor: 'success.light' }}>
            <CardContent>
              <Typography variant="h4">{stats.approved}</Typography>
              <Typography variant="body2">Approved</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <Card sx={{ bgcolor: 'error.light' }}>
            <CardContent>
              <Typography variant="h4">{stats.rejected}</Typography>
              <Typography variant="body2">Rejected</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <Card sx={{ bgcolor: 'info.light' }}>
            <CardContent>
              <Typography variant="h4">{stats.in_review}</Typography>
              <Typography variant="body2">In Review</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap" useFlexGap>
          <FilterList />
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Status</InputLabel>
            <Select
              value={filters.status || ''}
              onChange={(e) => handleFilterChange('status', e.target.value || undefined)}
              label="Status"
            >
              <MenuItem value="">All</MenuItem>
              <MenuItem value={ReviewStatus.PENDING}>Pending</MenuItem>
              <MenuItem value={ReviewStatus.APPROVED}>Approved</MenuItem>
              <MenuItem value={ReviewStatus.REJECTED}>Rejected</MenuItem>
              <MenuItem value={ReviewStatus.EDITED}>Edited</MenuItem>
              <MenuItem value={ReviewStatus.IN_REVIEW}>In Review</MenuItem>
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Difficulty</InputLabel>
            <Select
              value={filters.difficulty || ''}
              onChange={(e) => handleFilterChange('difficulty', e.target.value || undefined)}
              label="Difficulty"
            >
              <MenuItem value="">All</MenuItem>
              <MenuItem value="easy">Easy</MenuItem>
              <MenuItem value="medium">Medium</MenuItem>
              <MenuItem value="hard">Hard</MenuItem>
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>Question Type</InputLabel>
            <Select
              value={filters.question_type || ''}
              onChange={(e) => handleFilterChange('question_type', e.target.value || undefined)}
              label="Question Type"
            >
              <MenuItem value="">All</MenuItem>
              <MenuItem value="multiple_choice">Multiple Choice</MenuItem>
              <MenuItem value="open_ended">Open Ended</MenuItem>
              <MenuItem value="true_false">True/False</MenuItem>
            </Select>
          </FormControl>

          <Box sx={{ flexGrow: 1 }} />

          <Tooltip title="Refresh">
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
          No questions found matching your filters.
        </Alert>
      )}

      {questions.map((question) => (
        <QuestionReviewCard
          key={question.id}
          question={question}
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
        <DialogTitle>Add Comment</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            multiline
            rows={4}
            fullWidth
            label="Comment"
            value={commentText}
            onChange={(e) => setCommentText(e.target.value)}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCommentDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleAddComment} variant="contained" disabled={!commentText.trim() || loading}>
            Add Comment
          </Button>
        </DialogActions>
      </Dialog>

      {/* Action Dialog */}
      <Dialog open={actionDialogOpen} onClose={() => setActionDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {actionType === 'approve' ? 'Approve Question' : 'Reject Question'}
        </DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            multiline
            rows={3}
            fullWidth
            label="Reason (optional)"
            value={actionReason}
            onChange={(e) => setActionReason(e.target.value)}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setActionDialogOpen(false)}>Cancel</Button>
          <Button 
            onClick={executeAction} 
            variant="contained" 
            color={actionType === 'approve' ? 'success' : 'error'}
            disabled={loading}
          >
            {actionType === 'approve' ? 'Approve' : 'Reject'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ReviewQueue;

