/**
 * QuestionReviewCard Component
 * Displays a question with review controls
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Box,
  Chip,
  Button,
  IconButton,
  Divider,
  List,
  ListItem,
  ListItemText,
  Collapse,
  Alert,
  LinearProgress,
  Tooltip,
  Stack,
  CircularProgress,
} from '@mui/material';
import {
  CheckCircle,
  Cancel,
  Edit,
  Comment,
  ExpandMore,
  ExpandLess,
  Psychology,
  Timer,
  Grade,
  Source,
  Lightbulb,
} from '@mui/icons-material';
import { QuestionReview, ReviewStatus, ReviewComment } from '../types/review';
import { ReviewService } from '../services/ReviewService';

interface QuestionReviewCardProps {
  question: QuestionReview;
  onApprove?: (questionId: number) => void;
  onReject?: (questionId: number) => void;
  onEdit?: (questionId: number) => void;
  onComment?: (questionId: number) => void;
  loading?: boolean;
}

const QuestionReviewCard: React.FC<QuestionReviewCardProps> = ({
  question,
  onApprove,
  onReject,
  onEdit,
  onComment,
  loading = false,
}) => {
  const [showSources, setShowSources] = useState(false);
  const [showComments, setShowComments] = useState(false);
  const [comments, setComments] = useState<ReviewComment[]>([]);
  const [loadingComments, setLoadingComments] = useState(false);

  // Load comments when showComments is toggled
  useEffect(() => {
    const loadComments = async () => {
      if (showComments && comments.length === 0) {
        setLoadingComments(true);
        try {
          const fetchedComments = await ReviewService.getComments(question.id);
          setComments(fetchedComments);
        } catch (error) {
          console.error('Failed to load comments:', error);
        } finally {
          setLoadingComments(false);
        }
      }
    };

    loadComments();
  }, [showComments, question.id, comments.length]);

  const getStatusColor = (status: ReviewStatus): 'default' | 'success' | 'error' | 'warning' | 'info' => {
    switch (status) {
      case ReviewStatus.APPROVED:
        return 'success';
      case ReviewStatus.REJECTED:
        return 'error';
      case ReviewStatus.EDITED:
        return 'warning';
      case ReviewStatus.IN_REVIEW:
        return 'info';
      default:
        return 'default';
    }
  };

  const getDifficultyColor = (difficulty: string): 'success' | 'warning' | 'error' => {
    switch (difficulty.toLowerCase()) {
      case 'easy':
        return 'success';
      case 'medium':
        return 'warning';
      case 'hard':
        return 'error';
      default:
        return 'warning';
    }
  };

  const getBloomLevelLabel = (level?: number): string => {
    if (!level) return 'N/A';
    const labels = ['', 'Remember', 'Understand', 'Apply', 'Analyze', 'Evaluate', 'Create'];
    return `${level} - ${labels[level] || 'Unknown'}`;
  };

  const formatQuestionType = (type: string): string => {
    return type.split('_').map(word =>
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  return (
    <Card
      sx={{
        mb: 2,
        border: question.review_status === ReviewStatus.PENDING ? '2px solid #1976d2' : undefined,
        opacity: loading ? 0.6 : 1,
      }}
    >
      {loading && <LinearProgress />}

      <CardContent>
        {/* Header with Status and Metadata */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Box sx={{ flex: 1 }}>
            <Typography variant="caption" color="text.secondary">
              Question #{question.id} • {formatQuestionType(question.question_type)}
            </Typography>
            <Typography variant="h6" sx={{ mt: 0.5 }}>
              {question.question_text}
            </Typography>
          </Box>
          <Chip
            label={question.review_status.toUpperCase()}
            color={getStatusColor(question.review_status)}
            size="small"
          />
        </Box>

        {/* Options (for multiple choice) */}
        {question.options && question.options.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              Options:
            </Typography>
            <List dense>
              {question.options.map((option, index) => (
                <ListItem
                  key={index}
                  sx={{
                    py: 0.5,
                    bgcolor: option === question.correct_answer ? 'success.light' : undefined,
                    borderRadius: 1,
                    mb: 0.5,
                  }}
                >
                  <ListItemText
                    primary={option}
                    primaryTypographyProps={{
                      fontWeight: option === question.correct_answer ? 'bold' : 'normal',
                    }}
                  />
                  {option === question.correct_answer && (
                    <CheckCircle color="success" fontSize="small" />
                  )}
                </ListItem>
              ))}
            </List>
          </Box>
        )}

        {/* Correct Answer (for open-ended) */}
        {question.correct_answer && !question.options && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              Correct Answer:
            </Typography>
            <Alert severity="success" icon={<CheckCircle />}>
              {question.correct_answer}
            </Alert>
          </Box>
        )}

        {/* Explanation */}
        {question.explanation && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              Explanation:
            </Typography>
            <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
              {question.explanation}
            </Typography>
          </Box>
        )}

        <Divider sx={{ my: 2 }} />

        {/* Quality Indicators */}
        <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap>
          <Tooltip title="Difficulty Level">
            <Chip
              icon={<Grade />}
              label={question.difficulty.toUpperCase()}
              color={getDifficultyColor(question.difficulty)}
              size="small"
              variant="outlined"
            />
          </Tooltip>

          <Tooltip title="AI Confidence Score">
            <Chip
              icon={<Psychology />}
              label={`${(question.confidence_score * 100).toFixed(0)}% Confidence`}
              size="small"
              variant="outlined"
              color={question.confidence_score >= 0.8 ? 'success' : 'warning'}
            />
          </Tooltip>

          {question.bloom_level && (
            <Tooltip title="Bloom's Taxonomy Level">
              <Chip
                icon={<Lightbulb />}
                label={getBloomLevelLabel(question.bloom_level)}
                size="small"
                variant="outlined"
              />
            </Tooltip>
          )}

          {question.estimated_time_minutes && (
            <Tooltip title="Estimated Time">
              <Chip
                icon={<Timer />}
                label={`${question.estimated_time_minutes} min`}
                size="small"
                variant="outlined"
              />
            </Tooltip>
          )}

          {question.quality_tier && (
            <Tooltip title="Quality Tier">
              <Chip
                label={`Tier ${question.quality_tier}`}
                size="small"
                variant="outlined"
                color={question.quality_tier === 'A' ? 'success' : 'default'}
              />
            </Tooltip>
          )}

          <Tooltip title="Topic">
            <Chip
              label={question.topic}
              size="small"
              variant="outlined"
            />
          </Tooltip>
        </Stack>

        {/* Source Citations */}
        {question.source_documents && question.source_documents.length > 0 && (
          <Box sx={{ mt: 2 }}>
            <Button
              size="small"
              startIcon={showSources ? <ExpandLess /> : <ExpandMore />}
              onClick={() => setShowSources(!showSources)}
              endIcon={<Source />}
            >
              {showSources ? 'Hide' : 'Show'} Sources ({question.source_documents.length})
            </Button>
            <Collapse in={showSources}>
              <Box sx={{ mt: 1, pl: 2 }}>
                <Typography variant="caption" color="text.secondary">
                  Source Documents:
                </Typography>
                <List dense>
                  {question.source_documents.map((doc, index) => (
                    <ListItem key={index} sx={{ py: 0 }}>
                      <ListItemText
                        primary={doc}
                        primaryTypographyProps={{ variant: 'caption' }}
                      />
                    </ListItem>
                  ))}
                </List>
              </Box>
            </Collapse>
          </Box>
        )}

        {/* Comments Section */}
        <Box sx={{ mt: 2 }}>
          <Button
            size="small"
            startIcon={showComments ? <ExpandLess /> : <ExpandMore />}
            onClick={() => setShowComments(!showComments)}
            endIcon={<Comment />}
          >
            {showComments ? 'Hide' : 'Show'} Comments
          </Button>
          <Collapse in={showComments}>
            <Box sx={{ mt: 1, pl: 2 }}>
              {loadingComments ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
                  <CircularProgress size={24} />
                </Box>
              ) : comments.length === 0 ? (
                <Typography variant="caption" color="text.secondary">
                  No comments yet. Click the comment icon to add one.
                </Typography>
              ) : (
                <List dense>
                  {comments.map((comment) => (
                    <ListItem key={comment.id} sx={{ py: 1, flexDirection: 'column', alignItems: 'flex-start' }}>
                      <Box sx={{ width: '100%' }}>
                        <Typography variant="body2" sx={{ mb: 0.5 }}>
                          {comment.comment_text}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {comment.author} • {new Date(comment.created_at).toLocaleString()} • {comment.comment_type}
                        </Typography>
                      </Box>
                      {comment !== comments[comments.length - 1] && <Divider sx={{ width: '100%', mt: 1 }} />}
                    </ListItem>
                  ))}
                </List>
              )}
            </Box>
          </Collapse>
        </Box>

        {/* Review Metadata */}
        {question.reviewed_by && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="caption" color="text.secondary">
              Reviewed by {question.reviewed_by} on {new Date(question.reviewed_at!).toLocaleString()}
            </Typography>
          </Box>
        )}
      </CardContent>

      {/* Action Buttons */}
      <CardActions sx={{ justifyContent: 'space-between', px: 2, pb: 2 }}>
        <Box>
          <Tooltip title="Approve Question">
            <span>
              <Button
                variant="contained"
                color="success"
                startIcon={<CheckCircle />}
                onClick={() => onApprove?.(question.id)}
                disabled={loading || question.review_status === ReviewStatus.APPROVED}
                size="small"
              >
                Approve
              </Button>
            </span>
          </Tooltip>
          <Tooltip title="Reject Question">
            <span>
              <Button
                variant="contained"
                color="error"
                startIcon={<Cancel />}
                onClick={() => onReject?.(question.id)}
                disabled={loading || question.review_status === ReviewStatus.REJECTED}
                size="small"
                sx={{ ml: 1 }}
              >
                Reject
              </Button>
            </span>
          </Tooltip>
        </Box>
        <Box>
          <Tooltip title="Edit Question">
            <IconButton
              onClick={() => onEdit?.(question.id)}
              disabled={loading}
              size="small"
            >
              <Edit />
            </IconButton>
          </Tooltip>
          <Tooltip title="Add Comment">
            <IconButton
              onClick={() => onComment?.(question.id)}
              disabled={loading}
              size="small"
            >
              <Comment />
            </IconButton>
          </Tooltip>
        </Box>
      </CardActions>
    </Card>
  );
};

export default QuestionReviewCard;
