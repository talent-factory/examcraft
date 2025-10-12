import React, { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  Card,
  CardContent,
  Radio,
  RadioGroup,
  FormControlLabel,
  FormControl,
  TextField,
  Chip,
  Divider,
  Alert,
  Grid,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import {
  ExpandMore,
  Quiz,
  CheckCircle,
  Cancel,
  Lightbulb,
  Download,
  Print,
  Refresh
} from '@mui/icons-material';
import { ExamResponse, Question } from '../types/exam';
import MarkdownRenderer from './MarkdownRenderer';

interface ExamDisplayProps {
  exam: ExamResponse;
  onNewExam: () => void;
}

interface UserAnswer {
  questionId: string;
  answer: string;
}

const ExamDisplay: React.FC<ExamDisplayProps> = ({ exam, onNewExam }) => {
  const [userAnswers, setUserAnswers] = useState<UserAnswer[]>([]);
  const [showResults, setShowResults] = useState(false);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);

  const handleAnswerChange = (questionId: string, answer: string) => {
    setUserAnswers(prev => {
      const existing = prev.find(ua => ua.questionId === questionId);
      if (existing) {
        return prev.map(ua => ua.questionId === questionId ? { ...ua, answer } : ua);
      } else {
        return [...prev, { questionId, answer }];
      }
    });
  };

  const getUserAnswer = (questionId: string): string => {
    return userAnswers.find(ua => ua.questionId === questionId)?.answer || '';
  };

  const isCorrectAnswer = (question: Question, userAnswer: string): boolean => {
    if (!question.correct_answer || !userAnswer) return false;
    return question.correct_answer.toLowerCase().trim() === userAnswer.toLowerCase().trim();
  };

  const calculateScore = (): { correct: number; total: number; percentage: number } => {
    const total = exam.questions.length;
    const correct = exam.questions.reduce((count, question) => {
      const userAnswer = getUserAnswer(String(question.id));
      return isCorrectAnswer(question, userAnswer) ? count + 1 : count;
    }, 0);
    const percentage = total > 0 ? Math.round((correct / total) * 100) : 0;
    
    return { correct, total, percentage };
  };

  const renderQuestion = (question: Question, index: number) => {
    const userAnswer = getUserAnswer(String(question.id));
    const isCorrect = showResults ? isCorrectAnswer(question, userAnswer) : null;

    return (
      <Card key={question.id} sx={{ mb: 3, border: showResults ? (isCorrect ? '2px solid green' : '2px solid red') : 'none' }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'flex-start', mb: 2 }}>
            <Chip 
              label={`Frage ${index + 1}`} 
              color="primary" 
              size="small" 
              sx={{ mr: 2, mt: 0.5 }}
            />
            <Box sx={{ flex: 1 }}>
              <Box sx={{ mb: 1 }}>
                <MarkdownRenderer content={question.question} variant="compact" />
              </Box>
              <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                <Chip label={question.type === 'multiple_choice' ? 'Multiple Choice' : 'Offene Frage'} size="small" />
                <Chip label={question.difficulty} size="small" color="secondary" />
              </Box>
            </Box>
            {showResults && (
              <Box sx={{ ml: 2 }}>
                {isCorrect ? (
                  <CheckCircle color="success" />
                ) : (
                  <Cancel color="error" />
                )}
              </Box>
            )}
          </Box>

          {question.type === 'multiple_choice' && question.options ? (
            <FormControl component="fieldset" fullWidth>
              <RadioGroup
                value={userAnswer}
                onChange={(e) => handleAnswerChange(String(question.id), e.target.value)}
              >
                {question.options.map((option, optionIndex) => (
                  <FormControlLabel
                    key={optionIndex}
                    value={option}
                    control={<Radio />}
                    label={option}
                    disabled={showResults}
                    sx={{
                      backgroundColor: showResults && option === question.correct_answer ? 'success.light' : 'transparent',
                      borderRadius: 1,
                      px: 1,
                      py: 0.5,
                      mb: 0.5
                    }}
                  />
                ))}
              </RadioGroup>
            </FormControl>
          ) : (
            <TextField
              fullWidth
              multiline
              rows={4}
              placeholder="Ihre Antwort hier eingeben..."
              value={userAnswer}
              onChange={(e) => handleAnswerChange(String(question.id), e.target.value)}
              disabled={showResults}
              variant="outlined"
            />
          )}

          {showResults && question.explanation && (
            <Accordion sx={{ mt: 2 }}>
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <Lightbulb sx={{ mr: 1, color: 'warning.main' }} />
                  <Typography variant="subtitle2">Erklärung</Typography>
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <MarkdownRenderer content={question.explanation} variant="compact" />
              </AccordionDetails>
            </Accordion>
          )}
        </CardContent>
      </Card>
    );
  };

  const score = showResults ? calculateScore() : null;

  return (
    <Box>
      {/* Exam Header */}
      <Paper elevation={3} sx={{ p: 3, mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Box>
            <Typography variant="h4" component="h1" sx={{ mb: 1 }}>
              {exam.topic}
            </Typography>
            <Typography variant="subtitle1" color="text.secondary">
              Prüfung ID: {exam.exam_id}
            </Typography>
          </Box>
          <Box sx={{ textAlign: 'right' }}>
            <Typography variant="body2" color="text.secondary">
              Erstellt: {new Date(exam.created_at).toLocaleDateString('de-DE')}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {exam.questions.length} Fragen • {exam.metadata.difficulty}
            </Typography>
          </Box>
        </Box>

        {showResults && score && (
          <Alert 
            severity={score.percentage >= 70 ? 'success' : score.percentage >= 50 ? 'warning' : 'error'}
            sx={{ mb: 2 }}
          >
            <Typography variant="h6">
              Ergebnis: {score.correct} von {score.total} Fragen richtig ({score.percentage}%)
            </Typography>
          </Alert>
        )}

        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          {!showResults ? (
            <Button
              variant="contained"
              onClick={() => setShowResults(true)}
              startIcon={<CheckCircle />}
              disabled={userAnswers.length === 0}
            >
              Prüfung auswerten
            </Button>
          ) : (
            <>
              <Button
                variant="outlined"
                onClick={() => setShowResults(false)}
                startIcon={<Refresh />}
              >
                Erneut versuchen
              </Button>
              <Button
                variant="outlined"
                startIcon={<Print />}
                onClick={() => window.print()}
              >
                Drucken
              </Button>
            </>
          )}
          
          <Button
            variant="outlined"
            onClick={onNewExam}
            startIcon={<Quiz />}
          >
            Neue Prüfung
          </Button>
        </Box>
      </Paper>

      {/* Questions */}
      <Box>
        {exam.questions.map((question, index) => renderQuestion(question, index))}
      </Box>

      {/* Footer Actions */}
      {!showResults && (
        <Paper elevation={2} sx={{ p: 3, mt: 4, textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Beantwortet: {userAnswers.length} von {exam.questions.length} Fragen
          </Typography>
          <Button
            variant="contained"
            size="large"
            onClick={() => setShowResults(true)}
            startIcon={<CheckCircle />}
            disabled={userAnswers.length === 0}
          >
            Prüfung auswerten
          </Button>
        </Paper>
      )}
    </Box>
  );
};

export default ExamDisplay;
