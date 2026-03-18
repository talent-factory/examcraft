/**
 * QuestionReviewDetail Component
 * Detail page for reviewing a single question with role-based editing
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box, Typography, Paper, Button, Tabs, Tab, TextField,
  Alert, CircularProgress, Chip, Grid, Card, CardContent,
  FormControl, InputLabel, Select, MenuItem, Divider,
} from '@mui/material';
import { ArrowBack, Save, CheckCircle, Cancel, Send } from '@mui/icons-material';
import { ReviewService } from '../services/ReviewService';
import { useAuth } from '../contexts/AuthContext';
import MarkdownRenderer from './MarkdownRenderer';
import { QuestionReview, ReviewStatus } from '../types/review';

const QuestionReviewDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user: currentUser } = useAuth();

  const [question, setQuestion] = useState<QuestionReview | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState(0);
  const [commentText, setCommentText] = useState('');
  const [comments, setComments] = useState<any[]>([]);

  const [editData, setEditData] = useState({
    question_text: '',
    correct_answer: '',
    explanation: '',
    difficulty: 'medium',
    bloom_level: undefined as number | undefined,
    estimated_time_minutes: undefined as number | undefined,
  });

  const isReviewer = currentUser && question && currentUser.id === question.reviewed_by;

  const loadQuestion = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await ReviewService.getQuestionDetail(parseInt(id));
      setQuestion(data);
      setEditData({
        question_text: data.question_text || '',
        correct_answer: data.correct_answer || '',
        explanation: data.explanation || '',
        difficulty: data.difficulty || 'medium',
        bloom_level: data.bloom_level,
        estimated_time_minutes: data.estimated_time_minutes,
      });
      // Load comments
      try {
        const fetchedComments = await ReviewService.getComments(parseInt(id));
        setComments(fetchedComments);
      } catch {
        // Comments may not be available
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Laden der Frage');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadQuestion();
  }, [loadQuestion]);

  const handleSave = async () => {
    if (!question) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await ReviewService.editQuestion(question.id, editData);
      setQuestion(updated);
      setSuccess('Aenderungen gespeichert');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Speichern');
    } finally {
      setSaving(false);
    }
  };

  const handleApprove = async () => {
    if (!question) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await ReviewService.approveQuestion(question.id, {});
      setQuestion(updated);
      setSuccess('Frage genehmigt');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Genehmigen');
    } finally {
      setSaving(false);
    }
  };

  const handleReject = async () => {
    if (!question) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await ReviewService.rejectQuestion(question.id, {});
      setQuestion(updated);
      setSuccess('Frage abgelehnt');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Ablehnen');
    } finally {
      setSaving(false);
    }
  };

  const handleAddComment = async () => {
    if (!question || !commentText.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const newComment = await ReviewService.addComment(question.id, {
        comment_text: commentText,
        comment_type: 'general' as any,
      });
      setComments(prev => [...prev, newComment]);
      setCommentText('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Kommentieren');
    } finally {
      setSaving(false);
    }
  };

  const getStatusColor = (status: ReviewStatus): 'default' | 'success' | 'error' | 'warning' | 'info' => {
    switch (status) {
      case ReviewStatus.APPROVED: return 'success';
      case ReviewStatus.REJECTED: return 'error';
      case ReviewStatus.EDITED: return 'warning';
      case ReviewStatus.IN_REVIEW: return 'info';
      default: return 'default';
    }
  };

  // Loading state
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  // Error state (no question)
  if (!question) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error || 'Frage nicht gefunden'}
        </Alert>
        <Button
          startIcon={<ArrowBack />}
          onClick={() => navigate('/questions/review')}
        >
          Zurueck zur Queue
        </Button>
      </Box>
    );
  }

  const formatQuestionType = (type: string): string => {
    return type.split('_').map(word =>
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Button
            startIcon={<ArrowBack />}
            onClick={() => navigate('/questions/review')}
          >
            Zurueck
          </Button>
          <Typography variant="h5">
            Question #{question.id} &middot; {formatQuestionType(question.question_type)}
          </Typography>
          <Chip
            label={question.review_status.toUpperCase()}
            color={getStatusColor(question.review_status)}
            size="small"
          />
        </Box>
      </Box>

      {/* Reviewer info */}
      {question.reviewer_info && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Reviewer: {question.reviewer_info.first_name} {question.reviewer_info.last_name}
        </Typography>
      )}

      {/* Alerts */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {/* Content */}
      <Paper sx={{ p: 3, mb: 3 }}>
        {isReviewer ? (
          <>
            <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)} sx={{ mb: 2 }}>
              <Tab label="Bearbeiten" />
              <Tab label="Vorschau" />
            </Tabs>

            {activeTab === 0 && (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <TextField
                  label="Fragetext"
                  multiline
                  rows={6}
                  fullWidth
                  value={editData.question_text}
                  onChange={(e) => setEditData(prev => ({ ...prev, question_text: e.target.value }))}
                  InputProps={{ sx: { fontFamily: 'monospace' } }}
                />
                <TextField
                  label="Korrekte Antwort"
                  multiline
                  rows={4}
                  fullWidth
                  value={editData.correct_answer}
                  onChange={(e) => setEditData(prev => ({ ...prev, correct_answer: e.target.value }))}
                  InputProps={{ sx: { fontFamily: 'monospace' } }}
                />
                <TextField
                  label="Erklaerung"
                  multiline
                  rows={4}
                  fullWidth
                  value={editData.explanation}
                  onChange={(e) => setEditData(prev => ({ ...prev, explanation: e.target.value }))}
                  InputProps={{ sx: { fontFamily: 'monospace' } }}
                />
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={4}>
                    <FormControl fullWidth size="small">
                      <InputLabel>Schwierigkeit</InputLabel>
                      <Select
                        value={editData.difficulty}
                        onChange={(e) => setEditData(prev => ({ ...prev, difficulty: e.target.value }))}
                        label="Schwierigkeit"
                      >
                        <MenuItem value="easy">Easy</MenuItem>
                        <MenuItem value="medium">Medium</MenuItem>
                        <MenuItem value="hard">Hard</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <TextField
                      label="Bloom Level"
                      type="number"
                      fullWidth
                      size="small"
                      value={editData.bloom_level ?? ''}
                      onChange={(e) => setEditData(prev => ({
                        ...prev,
                        bloom_level: e.target.value ? parseInt(e.target.value) : undefined,
                      }))}
                      inputProps={{ min: 1, max: 6 }}
                    />
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <TextField
                      label="Geschaetzte Zeit (Min.)"
                      type="number"
                      fullWidth
                      size="small"
                      value={editData.estimated_time_minutes ?? ''}
                      onChange={(e) => setEditData(prev => ({
                        ...prev,
                        estimated_time_minutes: e.target.value ? parseInt(e.target.value) : undefined,
                      }))}
                      inputProps={{ min: 1 }}
                    />
                  </Grid>
                </Grid>
              </Box>
            )}

            {activeTab === 1 && (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">Fragetext:</Typography>
                <MarkdownRenderer content={editData.question_text} variant="compact" />
                <Divider />
                <Typography variant="subtitle2" color="text.secondary">Korrekte Antwort:</Typography>
                <MarkdownRenderer content={editData.correct_answer} variant="compact" />
                <Divider />
                <Typography variant="subtitle2" color="text.secondary">Erklaerung:</Typography>
                <MarkdownRenderer content={editData.explanation} variant="compact" />
              </Box>
            )}
          </>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Typography variant="subtitle2" color="text.secondary">Fragetext:</Typography>
            <MarkdownRenderer content={question.question_text} variant="compact" />
            {question.correct_answer && (
              <>
                <Divider />
                <Typography variant="subtitle2" color="text.secondary">Korrekte Antwort:</Typography>
                <MarkdownRenderer content={question.correct_answer} variant="compact" />
              </>
            )}
            {question.explanation && (
              <>
                <Divider />
                <Typography variant="subtitle2" color="text.secondary">Erklaerung:</Typography>
                <MarkdownRenderer content={question.explanation} variant="compact" />
              </>
            )}
          </Box>
        )}
      </Paper>

      {/* Action Buttons (reviewer only) */}
      {isReviewer && (
        <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
          <Button
            variant="contained"
            startIcon={<Save />}
            onClick={handleSave}
            disabled={saving}
          >
            Speichern
          </Button>
          <Button
            variant="contained"
            color="success"
            startIcon={<CheckCircle />}
            onClick={handleApprove}
            disabled={saving || question.review_status === ReviewStatus.APPROVED}
          >
            Approve
          </Button>
          <Button
            variant="contained"
            color="error"
            startIcon={<Cancel />}
            onClick={handleReject}
            disabled={saving || question.review_status === ReviewStatus.REJECTED}
          >
            Reject
          </Button>
        </Box>
      )}

      {/* Comments */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Kommentare
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
          <TextField
            fullWidth
            size="small"
            placeholder="Kommentar hinzufuegen..."
            value={commentText}
            onChange={(e) => setCommentText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleAddComment();
              }
            }}
          />
          <Button
            variant="contained"
            onClick={handleAddComment}
            disabled={!commentText.trim() || saving}
            startIcon={<Send />}
          >
            Senden
          </Button>
        </Box>
        {comments.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            Noch keine Kommentare vorhanden.
          </Typography>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {comments.map((comment) => (
              <Card key={comment.id} variant="outlined">
                <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
                  <Typography variant="body2">{comment.comment_text}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {comment.author || 'Unbekannt'} &middot; {new Date(comment.created_at).toLocaleString()} &middot; {comment.comment_type}
                  </Typography>
                </CardContent>
              </Card>
            ))}
          </Box>
        )}
      </Paper>
    </Box>
  );
};

export default QuestionReviewDetail;
