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
  SelectChangeEvent,
  Tabs,
  Tab
} from '@mui/material';
import { DocumentUpload as SimpleDocumentUpload } from './components/DocumentUpload_simple';
import DocumentUpload from './components/DocumentUpload';
import DocumentLibrary from './components/DocumentLibrary';
import RAGExamCreator from './components/RAGExamCreator';
import DocumentChatPage from './components/DocumentChat/DocumentChatPage';
import { School, Psychology, Quiz, CloudUpload, LibraryBooks, AutoAwesome, Chat } from '@mui/icons-material';
import { ExamService } from './services/ExamService';
import { ExamRequest, ExamResponse } from './types/exam';
import { RAGExamResponse } from './types/document';
import ExamDisplay from './components/ExamDisplay';

function App() {
  const [examRequest, setExamRequest] = useState<ExamRequest>({
    topic: '',
    difficulty: 'medium',
    question_count: 5,
    question_types: ['multiple_choice', 'open_ended'],
    language: 'de'
  });
  
  const [exam, setExam] = useState<ExamResponse | null>(null);
  const [ragExam, setRAGExam] = useState<RAGExamResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState(0);
  const [documentRefreshTrigger, setDocumentRefreshTrigger] = useState(0);
  const [selectedDocuments, setSelectedDocuments] = useState<number[]>([]);
  const [showRAGCreator, setShowRAGCreator] = useState(false);

  const handleGenerateExam = async () => {
    if (!examRequest.topic.trim()) {
      setError('Bitte geben Sie ein Thema ein.');
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      const response = await ExamService.generateExam(examRequest);
      setExam(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ein unbekannter Fehler ist aufgetreten.');
    } finally {
      setLoading(false);
    }
  };

  const handleNewExam = () => {
    setExam(null);
    setRAGExam(null);
    setShowRAGCreator(false);
    setExamRequest({
      topic: '',
      difficulty: 'medium',
      question_count: 5,
      question_types: ['multiple_choice', 'open_ended'],
      language: 'de'
    });
  };

  const handleDocumentUploadComplete = (documentId: number, filename: string) => {
    console.log(`Document uploaded successfully: ${filename} (ID: ${documentId})`);
    setDocumentRefreshTrigger(prev => prev + 1);
  };

  const handleDocumentUploadError = (filename: string, error: string) => {
    console.error(`Document upload failed for ${filename}: ${error}`);
    setError(`Upload-Fehler für ${filename}: ${error}`);
  };

  const handleCreateRAGExam = (documentIds: number[]) => {
    setSelectedDocuments(documentIds);
    setShowRAGCreator(true);
  };

  const handleRAGExamGenerated = (exam: RAGExamResponse) => {
    setRAGExam(exam);
    setShowRAGCreator(false);
  };

  const handleBackFromRAGCreator = () => {
    setShowRAGCreator(false);
    setSelectedDocuments([]);
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
          Für OpenBook-Prüfungen mit Claude API Integration & Document Upload
        </Typography>
      </Box>

      {!exam && !ragExam && !showRAGCreator ? (
        <>
          {/* Tab Navigation */}
          <Paper elevation={2} sx={{ mb: 4 }}>
            <Tabs
              value={activeTab}
              onChange={(_, newValue: number) => setActiveTab(newValue)}
              variant="fullWidth"
              sx={{ borderBottom: 1, borderColor: 'divider' }}
            >
              <Tab label="KI-Prüfung erstellen" icon={<Psychology />} />
              <Tab label="Dokumente hochladen" icon={<CloudUpload />} />
              <Tab label="Dokumentenbibliothek" icon={<LibraryBooks />} />
              <Tab label="RAG-Prüfung erstellen" icon={<AutoAwesome />} />
              <Tab label="Dokument ChatBot" icon={<Chat />} />
            </Tabs>
          </Paper>

          {/* Tab Content */}
          {activeTab === 0 && (
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
                    {['multiple_choice', 'open_ended'].map((type) => (
                      <Chip
                        key={type}
                        label={type === 'multiple_choice' ? 'Multiple Choice' : 'Offene Fragen'}
                        color={examRequest.question_types.includes(type) ? 'primary' : 'default'}
                        onClick={() => {
                          const newTypes = examRequest.question_types.includes(type)
                            ? examRequest.question_types.filter(t => t !== type)
                            : [...examRequest.question_types, type];
                          setExamRequest({ ...examRequest, question_types: newTypes });
                        }}
                        sx={{ cursor: 'pointer' }}
                      />
                    ))}
                  </Box>
                </Grid>
              </Grid>

              {error && (
                <Alert severity="error" sx={{ mt: 3 }}>
                  {error}
                </Alert>
              )}

              <Box sx={{ textAlign: 'center', mt: 4 }}>
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
          )}

          {activeTab === 1 && (
            /* Document Upload Tab */
            <Paper elevation={3} sx={{ p: 4, mb: 4 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                <CloudUpload sx={{ color: 'primary.main', mr: 2 }} />
                <Typography variant="h5" component="h2">
                  Dokumente hochladen
                </Typography>
              </Box>

              <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
                Laden Sie Dokumente hoch, um daraus automatisch Prüfungsfragen zu generieren. 
                Unterstützte Formate: PDF, DOC, DOCX, TXT, MD
              </Typography>

              <DocumentUpload
                onUploadComplete={handleDocumentUploadComplete}
                onUploadError={handleDocumentUploadError}
                onAllUploadsComplete={() => setDocumentRefreshTrigger(prev => prev + 1)}
                maxFiles={10}
              />

              <Alert severity="success" sx={{ mt: 3 }}>
                <Typography variant="body2">
                  <strong>Neu:</strong> RAG-basierte Fragenerstellung aus hochgeladenen Dokumenten 
                  ist jetzt verfügbar! Wechseln Sie zur Dokumentenbibliothek, um Ihre Dokumente zu verwalten 
                  und RAG-Prüfungen zu erstellen.
                </Typography>
              </Alert>
            </Paper>
          )}

          {activeTab === 2 && (
            /* Document Library Tab */
            <Paper elevation={3} sx={{ p: 4, mb: 4 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                <LibraryBooks sx={{ color: 'primary.main', mr: 2 }} />
                <Typography variant="h5" component="h2">
                  Dokumentenbibliothek
                </Typography>
              </Box>

              <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
                Verwalten Sie Ihre hochgeladenen Dokumente und erstellen Sie RAG-basierte Prüfungen.
              </Typography>

              <DocumentLibrary
                onCreateRAGExam={handleCreateRAGExam}
                refreshTrigger={documentRefreshTrigger}
              />
            </Paper>
          )}

          {activeTab === 3 && (
            /* RAG Exam Creator Tab */
            <Paper elevation={3} sx={{ p: 4, mb: 4 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                <AutoAwesome sx={{ color: 'primary.main', mr: 2 }} />
                <Typography variant="h5" component="h2">
                  RAG-Prüfung erstellen
                </Typography>
              </Box>

              <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
                Erstellen Sie intelligente Prüfungen basierend auf Ihren hochgeladenen Dokumenten
                mit Retrieval-Augmented Generation (RAG).
              </Typography>

              <RAGExamCreator
                onExamGenerated={handleRAGExamGenerated}
              />
            </Paper>
          )}

          {activeTab === 4 && (
            /* Document ChatBot Tab */
            <Paper elevation={3} sx={{ p: 4, mb: 4 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                <Chat sx={{ color: 'primary.main', mr: 2 }} />
                <Typography variant="h5" component="h2">
                  Dokument ChatBot
                </Typography>
              </Box>

              <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
                Chatten Sie mit Ihren hochgeladenen Dokumenten. Der ChatBot nutzt RAG-Technologie,
                um präzise Antworten basierend auf Ihren Dokumenten zu geben.
              </Typography>

              <DocumentChatPage />
            </Paper>
          )}
        </>
      ) : showRAGCreator ? (
        /* RAG Exam Creator */
        <RAGExamCreator
          selectedDocuments={selectedDocuments}
          onExamGenerated={handleRAGExamGenerated}
          onBack={handleBackFromRAGCreator}
        />
      ) : exam ? (
        /* Regular Exam Display */
        <Box>
          <ExamDisplay exam={exam} onNewExam={handleNewExam} />
        </Box>
      ) : ragExam ? (
        /* RAG Exam Display */
        <Box>
          <ExamDisplay 
            exam={{
              id: ragExam.exam_id,
              exam_id: ragExam.exam_id,
              topic: ragExam.topic,
              questions: ragExam.questions.map((q, index) => ({
                id: index + 1,
                question: q.question_text,
                type: q.question_type as 'multiple_choice' | 'open_ended' | 'true_false' | 'short_answer',
                options: q.options || [],
                correct_answer: q.correct_answer || '',
                explanation: Array.isArray(q.explanation) ? q.explanation.join('\n') : q.explanation || '',
                difficulty: q.difficulty || 'medium',
                topic: ragExam.topic,
                sources: q.source_documents,
                confidence: q.confidence_score
              })),
              difficulty: ragExam.questions[0]?.difficulty || 'medium',
              language: 'de',
              created_at: new Date().toISOString(),
              generation_time: ragExam.generation_time,
              metadata: {
                difficulty: 'medium',
                question_count: ragExam.questions.length,
                language: 'de',
                generated_by: 'rag',
                generation_time: ragExam.generation_time,
                quality_metrics: ragExam.quality_metrics,
                source_documents: ragExam.context_summary.source_documents
              }
            }} 
            onNewExam={handleNewExam} 
          />
        </Box>
      ) : null}

      {/* System Status */}
      <Card sx={{ mt: 4, bgcolor: 'info.light', color: 'info.contrastText' }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 1 }}>
            📊 ExamCraft AI - System Status
          </Typography>
          <Typography variant="body2">
            🤖 <strong>KI-Modell:</strong> Claude Sonnet 4 (neueste Generation) •
            🔍 <strong>Embeddings:</strong> OpenAI text-embedding-3-small (1536 dim) •
            📚 <strong>Vector DB:</strong> Qdrant mit semantischer Suche •
            📄 <strong>Dokumente:</strong> PDF, DOC, Markdown Support •
            ✅ <strong>Status:</strong> Production Ready
          </Typography>
        </CardContent>
      </Card>
    </Container>
  );
}

export default App;
