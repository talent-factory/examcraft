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
  RateReview,
  Visibility,
  LocalOfferOutlined,
  Description,
  Archive,
  Unarchive,
  DeleteForever,
  Verified,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { getDateLocale } from '../utils/dateLocale';
import { QuestionReview, ReviewStatus, ReviewComment } from '../types/review';
import { ReviewService } from '../services/ReviewService';
import MarkdownRenderer from './MarkdownRenderer';

interface QuestionReviewCardProps {
  question: QuestionReview;
  onStartReview?: (questionId: number) => void;
  onApprove?: (questionId: number) => void;
  onReject?: (questionId: number) => void;
  onEdit?: (questionId: number) => void;
  onComment?: (questionId: number) => void;
  onArchive?: (questionId: number) => void;
  onRestore?: (questionId: number) => void;
  onDelete?: (questionId: number) => void;
  canDelete?: boolean;
  loading?: boolean;
}

const QuestionReviewCard: React.FC<QuestionReviewCardProps> = ({
  question,
  onStartReview,
  onApprove,
  onReject,
  onEdit,
  onComment,
  onArchive,
  onRestore,
  onDelete,
  canDelete = false,
  loading = false,
}) => {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
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

  // Bloom taxonomy labels are standardized educational terms used internationally
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

  // TF-383: Provenance chip — shows which template was used to create the
  // question. Snapshot at generation time. Legacy data (null) → "not
  // recorded"; default/fallback template → standard badge; custom prompt →
  // name + version with variables in the tooltip.
  const renderTemplateChip = () => {
    const gm = question.generation_metadata;
    const provenance = t('components.questionCard.templateProvenance');

    if (!gm) {
      return (
        <Tooltip title={provenance}>
          <Chip
            icon={<Description />}
            label={t('components.questionCard.templateNotRecorded')}
            size="small"
            variant="outlined"
          />
        </Tooltip>
      );
    }

    const isDefault = Boolean(gm.is_default_template || gm.fallback_to_default);
    const version = gm.prompt_version != null ? ` v${gm.prompt_version}` : '';
    const label = isDefault
      ? t('components.questionCard.defaultTemplate')
      : `${gm.prompt_name ?? '—'}${version}`;

    const varEntries = gm.variables ? Object.entries(gm.variables) : [];
    const fmtVar = (v: unknown) =>
      typeof v === 'object' && v !== null ? JSON.stringify(v) : String(v);
    const tooltip = varEntries.length
      ? `${provenance} — ${varEntries.map(([k, v]) => `${k}: ${fmtVar(v)}`).join(', ')}`
      : provenance;

    return (
      <Tooltip title={tooltip}>
        <Chip
          icon={<Description />}
          label={label}
          size="small"
          variant="outlined"
          color={isDefault ? 'default' : 'info'}
        />
      </Tooltip>
    );
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
              {t('components.questionCard.questionNumber', { id: question.id })} • {formatQuestionType(question.question_type)}
            </Typography>
            <Box sx={{ mt: 0.5 }}>
              <MarkdownRenderer content={question.question_text} variant="compact" />
            </Box>
          </Box>
          <Chip
            label={question.review_status.toUpperCase()}
            color={getStatusColor(question.review_status)}
            size="small"
          />
        </Box>

        {question.reviewer_info && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {t('components.questionCard.reviewer', { name: `${question.reviewer_info.first_name} ${question.reviewer_info.last_name}` })}
          </Typography>
        )}

        {/* Options (for multiple choice) */}
        {question.options && question.options.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              {t('components.questionCard.options')}
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
              {t('components.questionCard.correctAnswer')}
            </Typography>
            <Alert severity="success" icon={<CheckCircle />}>
              <MarkdownRenderer content={question.correct_answer} variant="compact" />
            </Alert>
          </Box>
        )}

        {/* Explanation */}
        {question.explanation && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              {t('components.questionCard.explanation')}
            </Typography>
            <MarkdownRenderer content={question.explanation} variant="compact" />
          </Box>
        )}

        <Divider sx={{ my: 2 }} />

        {/* Quality Indicators */}
        <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap>
          <Tooltip title={t('components.questionCard.difficultyLevel')}>
            <Chip
              icon={<Grade />}
              label={question.difficulty.toUpperCase()}
              color={getDifficultyColor(question.difficulty)}
              size="small"
              variant="outlined"
            />
          </Tooltip>

          <Tooltip title={t('components.questionCard.aiConfidence')}>
            <Chip
              icon={<Psychology />}
              label={t('components.questionCard.confidenceLabel', { score: (question.confidence_score * 100).toFixed(0) })}
              size="small"
              variant="outlined"
              color={question.confidence_score >= 0.8 ? 'success' : 'warning'}
            />
          </Tooltip>

          {question.bloom_level && (
            <Tooltip title={t('components.questionCard.bloomLevel')}>
              <Chip
                icon={<Lightbulb />}
                label={getBloomLevelLabel(question.bloom_level)}
                size="small"
                variant="outlined"
              />
            </Tooltip>
          )}

          {/* TF-400: reviewed competency (HK) + LN level */}
          {question.competency && (
            <Tooltip
              title={t('components.questionCard.competencyTooltip', {
                title: question.competency.title,
              })}
            >
              <Chip
                icon={<Verified />}
                label={
                  question.ln_level
                    ? `${question.competency.code} · ${t(
                        'components.questionCard.lnLevelShort',
                        { level: question.ln_level }
                      )}`
                    : question.competency.code
                }
                size="small"
                variant="outlined"
                color="info"
              />
            </Tooltip>
          )}

          {question.estimated_time_minutes && (
            <Tooltip title={t('components.questionCard.estimatedTime')}>
              <Chip
                icon={<Timer />}
                label={`${question.estimated_time_minutes} min`}
                size="small"
                variant="outlined"
              />
            </Tooltip>
          )}

          {question.quality_tier && (
            <Tooltip title={t('components.questionCard.qualityTier')}>
              <Chip
                label={`Tier ${question.quality_tier}`}
                size="small"
                variant="outlined"
                color={question.quality_tier === 'A' ? 'success' : 'default'}
              />
            </Tooltip>
          )}

          <Tooltip title={t('components.questionCard.topic')}>
            <Chip
              label={question.topic}
              size="small"
              variant="outlined"
            />
          </Tooltip>

          {/* Template provenance (TF-383): mit welcher Vorlage wurde die Frage erstellt */}
          {renderTemplateChip()}
        </Stack>

        {question.tags && question.tags.length > 0 && (
          <Box sx={{ mt: 2, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
            {[...question.tags].sort((a, b) => a.name.localeCompare(b.name)).map((tag) => (
              <Chip
                key={tag.id}
                icon={<LocalOfferOutlined />}
                label={tag.name}
                size="small"
                sx={{
                  bgcolor: (theme) => `${theme.palette.secondary.light}22`,
                  color: 'secondary.dark',
                  border: '1px solid',
                  borderColor: (theme) => `${theme.palette.secondary.light}66`,
                  '& .MuiChip-icon': { color: 'secondary.light', fontSize: 14 },
                }}
              />
            ))}
          </Box>
        )}

        {/* Source Citations */}
        {question.source_documents && question.source_documents.length > 0 && (
          <Box sx={{ mt: 2 }}>
            <Button
              size="small"
              startIcon={showSources ? <ExpandLess /> : <ExpandMore />}
              onClick={() => setShowSources(!showSources)}
              endIcon={<Source />}
            >
              {showSources
                ? t('components.questionCard.hideSources', { count: question.source_documents.length })
                : t('components.questionCard.showSources', { count: question.source_documents.length })}
            </Button>
            <Collapse in={showSources}>
              <Box sx={{ mt: 1, pl: 2 }}>
                <Typography variant="caption" color="text.secondary">
                  {t('components.questionCard.sourceDocuments')}
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
            {showComments ? t('components.questionCard.hideComments') : t('components.questionCard.showComments')}
          </Button>
          <Collapse in={showComments}>
            <Box sx={{ mt: 1, pl: 2 }}>
              {loadingComments ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
                  <CircularProgress size={24} />
                </Box>
              ) : comments.length === 0 ? (
                <Typography variant="caption" color="text.secondary">
                  {t('components.questionCard.noComments')}
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
                          {comment.author} • {new Date(comment.created_at).toLocaleString(getDateLocale(i18n.language))} • {comment.comment_type}
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
              {t('components.questionCard.reviewedBy', {
                name: question.reviewed_by,
                date: new Date(question.reviewed_at!).toLocaleString(getDateLocale(i18n.language))
              })}
            </Typography>
          </Box>
        )}
      </CardContent>

      {/* Action Buttons */}
      <CardActions sx={{ justifyContent: 'space-between', px: 2, pb: 2 }}>
        <Box>
          {(question.review_status === ReviewStatus.PENDING || question.review_status === ReviewStatus.EDITED) && (
            <Tooltip title={t('components.questionCard.startReview')}>
              <span>
                <Button
                  variant="outlined"
                  color="info"
                  startIcon={<RateReview />}
                  onClick={() => onStartReview?.(question.id)}
                  disabled={loading}
                  size="small"
                >
                  {t('components.questionCard.startReview')}
                </Button>
              </span>
            </Tooltip>
          )}
          <Tooltip title={t('components.questionCard.approveBtn')}>
            <span>
              <Button
                variant="contained"
                color="success"
                startIcon={<CheckCircle />}
                onClick={() => onApprove?.(question.id)}
                disabled={loading || question.review_status === ReviewStatus.APPROVED}
                size="small"
              >
                {t('components.questionCard.approveBtn')}
              </Button>
            </span>
          </Tooltip>
          <Tooltip title={t('components.questionCard.rejectBtn')}>
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
                {t('components.questionCard.rejectBtn')}
              </Button>
            </span>
          </Tooltip>
        </Box>
        <Box>
          <Tooltip title={t('components.questionCard.editQuestion')}>
            <IconButton
              onClick={() => onEdit?.(question.id)}
              disabled={loading}
              size="small"
            >
              <Edit />
            </IconButton>
          </Tooltip>
          <Tooltip title={t('components.questionCard.addComment')}>
            <IconButton
              onClick={() => onComment?.(question.id)}
              disabled={loading}
              size="small"
            >
              <Comment />
            </IconButton>
          </Tooltip>
          <Tooltip title={t('components.questionCard.showDetails')}>
            <IconButton
              onClick={() => navigate(`/questions/review/${question.id}`)}
              size="small"
            >
              <Visibility />
            </IconButton>
          </Tooltip>

          {/* TF-396: Archiv-Aktionen */}
          {!question.archived_at ? (
            <Tooltip title={t('components.questionCard.archiveBtn')}>
              <IconButton
                onClick={() => onArchive?.(question.id)}
                disabled={loading}
                size="small"
              >
                <Archive />
              </IconButton>
            </Tooltip>
          ) : (
            <>
              <Tooltip title={t('components.questionCard.restoreBtn')}>
                <IconButton
                  onClick={() => onRestore?.(question.id)}
                  disabled={loading}
                  size="small"
                >
                  <Unarchive />
                </IconButton>
              </Tooltip>
              {canDelete && (
                <Tooltip title={t('components.questionCard.deleteBtn')}>
                  <IconButton
                    onClick={() => onDelete?.(question.id)}
                    disabled={loading}
                    size="small"
                    color="error"
                  >
                    <DeleteForever />
                  </IconButton>
                </Tooltip>
              )}
            </>
          )}
        </Box>
      </CardActions>
    </Card>
  );
};

export default QuestionReviewCard;
