import React, { useState, ChangeEvent } from 'react';
import {
  Container,
  Typography,
  Box,
  Paper,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Grid,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  SelectChangeEvent
} from '@mui/material';
import { School, Psychology, Quiz } from '@mui/icons-material';
import { ExamService } from './services/ExamService';
import { ExamRequest, ExamResponse } from './types/exam';
import ExamDisplay from './components/ExamDisplay';

function App() {
  const [examRequest, setExamRequest] = useState<ExamRequest>({
    topic: '',
    difficulty: 'medium',
    question_count: 5,
    question_types: ['multiple_choice', 'open_ended'],
    language: 'de'
  });
  
  const [examResponse, setExamResponse] = useState<ExamResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerateExam = async () => {
    if (!examRequest.topic.trim()) {
      setError('Bitte geben Sie ein Thema ein.');
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      const response = await ExamService.generateExam(examRequest);
      setExamResponse(response);
    } catch (err) {
      setError('Fehler beim Generieren der Prüfung. Bitte versuchen Sie es erneut.');
      console.error('Error generating exam:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleNewExam = () => {
    setExamResponse(null);
    setExamRequest({
      topic: '',
      difficulty: 'medium',
      question_count: 5,
      question_types: ['multiple_choice', 'open_ended'],
      language: 'de'
    });
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ textAlign: 'center', mb: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', mb: 2 }}>
          <School sx={{ fontSize: 40, color: 'primary.main', mr: 2 }} />
          <Typography variant="h3" component="h1" color="primary">
            ExamCraft AI
          </Typography>
        </Box>
        <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
          KI-gestützte Plattform zur automatischen Generierung von Prüfungsaufgaben
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Für OpenBook-Prüfungen mit Claude API Integration
        </Typography>
      </Box>

      {!examResponse ? (
        /* Exam Generation Form */
        <Paper elevation={3} sx={{ p: 4, mb: 4 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
            <Psychology sx={{ color: 'primary.main', mr: 2 }} />
            <Typography variant="h5" component="h2">
              Neue Prüfung erstellen
            </Typography>
          </Box>

          <Grid container spacing={3}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Prüfungsthema"
                value={examRequest.topic}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setExamRequest({ ...examRequest, topic: e.target.value })}
                placeholder="z.B. Python Programmierung, Datenstrukturen, Webentwicklung..."
                variant="outlined"
              />
            </Grid>

            <Grid item xs={12} md={4}>
              <FormControl fullWidth>
                <InputLabel>Schwierigkeitsgrad</InputLabel>
                <Select
                  value={examRequest.difficulty}
                  label="Schwierigkeitsgrad"
                  onChange={(e: SelectChangeEvent) => setExamRequest({ ...examRequest, difficulty: e.target.value as 'easy' | 'medium' | 'hard' })}
                >
                  <MenuItem value="easy">Einfach</MenuItem>
                  <MenuItem value="medium">Mittel</MenuItem>
                  <MenuItem value="hard">Schwer</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                type="number"
                label="Anzahl Fragen"
                value={examRequest.question_count}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setExamRequest({ 
                  ...examRequest, 
                  question_count: Math.max(1, Math.min(20, parseInt(e.target.value) || 5))
                })}
                inputProps={{ min: 1, max: 20 }}
              />
            </Grid>

            <Grid item xs={12} md={4}>
              <FormControl fullWidth>
                <InputLabel>Sprache</InputLabel>
                <Select
                  value={examRequest.language}
                  label="Sprache"
                  onChange={(e: SelectChangeEvent) => setExamRequest({ ...examRequest, language: e.target.value as 'de' | 'en' })}
                >
                  <MenuItem value="de">Deutsch</MenuItem>
                  <MenuItem value="en">English</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12}>
              <Typography variant="subtitle1" sx={{ mb: 1 }}>
                Fragetypen:
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                <Chip 
                  label="Multiple Choice" 
                  color="primary" 
                  variant="filled"
                />
                <Chip 
                  label="Offene Fragen" 
                  color="primary" 
                  variant="filled"
                />
              </Box>
            </Grid>
          </Grid>

          {error && (
            <Alert severity="error" sx={{ mt: 3 }}>
              {error}
            </Alert>
          )}

          <Box sx={{ mt: 4, textAlign: 'center' }}>
            <Button
              variant="contained"
              size="large"
              onClick={handleGenerateExam}
              disabled={loading || !examRequest.topic.trim()}
              startIcon={loading ? <CircularProgress size={20} /> : <Quiz />}
              sx={{ minWidth: 200 }}
            >
              {loading ? 'Generiere Prüfung...' : 'Prüfung generieren'}
            </Button>
          </Box>
        </Paper>
      ) : (
        /* Exam Display */
        <Box>
          <ExamDisplay exam={examResponse} onNewExam={handleNewExam} />
        </Box>
      )}

      {/* Demo Info */}
      <Card sx={{ mt: 4, bgcolor: 'info.light', color: 'info.contrastText' }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 1 }}>
            🚀 Workshop Demo Version
          </Typography>
          <Typography variant="body2">
            Dies ist eine Demo-Version für den Workshop. In der finalen Version wird die Claude API 
            für die intelligente Generierung von Prüfungsfragen verwendet.
          </Typography>
        </CardContent>
      </Card>
    </Container>
  );
}

export default App;
