import { RAGService } from '../RAGService';
import { 
  RAGExamRequest, 
  RAGExamResponse, 
  RAGContextSummary,
  QuestionTypesResponse 
} from '../../types/document';

// Mock fetch
global.fetch = jest.fn();
const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

// Mock URL and Blob for export tests
global.URL.createObjectURL = jest.fn(() => 'mock-url');
global.URL.revokeObjectURL = jest.fn();

// Mock DOM methods for export
const mockLink = {
  href: '',
  download: '',
  click: jest.fn()
};

Object.defineProperty(document, 'createElement', {
  value: jest.fn(() => mockLink)
});

Object.defineProperty(document.body, 'appendChild', {
  value: jest.fn()
});

Object.defineProperty(document.body, 'removeChild', {
  value: jest.fn()
});

// Sample test data
const mockRAGExamRequest: RAGExamRequest = {
  topic: 'Machine Learning',
  document_ids: [1, 2],
  question_count: 5,
  question_types: ['multiple_choice', 'open_ended'],
  difficulty: 'medium',
  language: 'de',
  context_chunks_per_question: 3
};

const mockRAGExamResponse: RAGExamResponse = {
  exam_id: 'test_exam_123',
  topic: 'Machine Learning',
  questions: [
    {
      question_text: 'Was ist Machine Learning?',
      question_type: 'multiple_choice',
      options: ['A) Ein Algorithmus', 'B) Eine Methode', 'C) Ein System', 'D) Ein Prozess'],
      correct_answer: 'B',
      explanation: 'Machine Learning ist eine Methode der KI',
      difficulty: 'medium',
      source_chunks: ['chunk_1', 'chunk_2'],
      source_documents: ['ml_basics.pdf', 'ai_intro.txt'],
      confidence_score: 0.85
    },
    {
      question_text: 'Erläutern Sie die Grundprinzipien des Machine Learning.',
      question_type: 'open_ended',
      correct_answer: 'Machine Learning basiert auf Algorithmen...',
      explanation: ['Verständnis der Grundlagen', 'Anwendungsbeispiele', 'Kritische Bewertung'],
      difficulty: 'medium',
      source_chunks: ['chunk_3', 'chunk_4'],
      source_documents: ['ml_basics.pdf'],
      confidence_score: 0.78
    }
  ],
  context_summary: {
    query: 'Machine Learning',
    total_chunks: 4,
    total_similarity_score: 3.2,
    source_documents: [
      { id: 1, filename: 'ml_basics.pdf', chunks_used: 3 },
      { id: 2, filename: 'ai_intro.txt', chunks_used: 1 }
    ],
    context_length: 1200
  },
  generation_time: 3.5,
  quality_metrics: {
    total_questions: 2,
    average_confidence: 0.815,
    source_coverage: 1.0,
    question_type_distribution: { multiple_choice: 1, open_ended: 1 },
    context_chunks_used: 4,
    total_context_length: 1200,
    average_similarity_score: 0.8
  }
};

const mockContextSummary: RAGContextSummary = {
  query: 'Machine Learning',
  total_chunks: 4,
  total_similarity_score: 3.2,
  source_documents: [
    { id: 1, filename: 'ml_basics.pdf', chunks_used: 3 },
    { id: 2, filename: 'ai_intro.txt', chunks_used: 1 }
  ],
  context_length: 1200
};

const mockQuestionTypes: QuestionTypesResponse = {
  supported_types: [
    {
      type: 'multiple_choice',
      name: 'Multiple Choice',
      description: 'Frage mit 4 Antwortoptionen',
      example: 'Welche Aussage ist korrekt?'
    },
    {
      type: 'open_ended',
      name: 'Offene Frage',
      description: 'Frage die eine ausführliche Antwort erfordert',
      example: 'Erläutern Sie...'
    },
    {
      type: 'true_false',
      name: 'Wahr/Falsch',
      description: 'Aussage die als wahr oder falsch bewertet wird',
      example: 'Die folgende Aussage ist korrekt...'
    }
  ],
  difficulty_levels: [
    {
      level: 'easy',
      name: 'Einfach',
      description: 'Grundlegende Fakten'
    },
    {
      level: 'medium',
      name: 'Mittel',
      description: 'Anwendung von Konzepten'
    },
    {
      level: 'hard',
      name: 'Schwer',
      description: 'Kritisches Denken'
    }
  ],
  supported_languages: [
    { code: 'de', name: 'Deutsch' },
    { code: 'en', name: 'English' }
  ]
};

describe('RAGService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    process.env.REACT_APP_API_URL = 'http://localhost:8000';
  });

  describe('generateRAGExam', () => {
    it('generates RAG exam successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockRAGExamResponse
      } as Response);

      const result = await RAGService.generateRAGExam(mockRAGExamRequest);

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/rag/generate-exam',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(mockRAGExamRequest)
        }
      );

      expect(result).toEqual(mockRAGExamResponse);
    });

    it('handles RAG exam generation errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: async () => ({ detail: 'Invalid request parameters' })
      } as Response);

      await expect(RAGService.generateRAGExam(mockRAGExamRequest))
        .rejects.toThrow('Invalid request parameters');
    });

    it('handles network errors during exam generation', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(RAGService.generateRAGExam(mockRAGExamRequest))
        .rejects.toThrow('Network error');
    });
  });

  describe('retrieveContext', () => {
    it('retrieves context successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockContextSummary
      } as Response);

      const result = await RAGService.retrieveContext(
        'Machine Learning',
        [1, 2],
        5,
        0.3
      );

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/rag/retrieve-context',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            query: 'Machine Learning',
            document_ids: [1, 2],
            max_chunks: 5,
            min_similarity: 0.3
          })
        }
      );

      expect(result).toEqual(mockContextSummary);
    });

    it('uses default parameters when not provided', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockContextSummary
      } as Response);

      await RAGService.retrieveContext('Test Query');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/rag/retrieve-context',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            query: 'Test Query',
            document_ids: undefined,
            max_chunks: 5,
            min_similarity: 0.3
          })
        }
      );
    });

    it('handles context retrieval errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ detail: 'No context found' })
      } as Response);

      await expect(RAGService.retrieveContext('Nonexistent Topic'))
        .rejects.toThrow('No context found');
    });
  });

  describe('getQuestionTypes', () => {
    it('retrieves question types successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockQuestionTypes
      } as Response);

      const result = await RAGService.getQuestionTypes();

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/rag/question-types',
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );

      expect(result).toEqual(mockQuestionTypes);
    });

    it('handles question types retrieval errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ detail: 'Server error' })
      } as Response);

      await expect(RAGService.getQuestionTypes())
        .rejects.toThrow('Server error');
    });
  });

  describe('checkHealth', () => {
    it('checks RAG service health successfully', async () => {
      const mockHealthResponse = {
        status: 'healthy',
        service: 'RAG Service',
        components: {
          vector_service: { status: 'available' },
          claude_service: { status: 'available' }
        }
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockHealthResponse
      } as Response);

      const result = await RAGService.checkHealth();

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/rag/health',
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );

      expect(result).toEqual(mockHealthResponse);
    });

    it('handles health check errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 503,
        statusText: 'Service Unavailable',
        json: async () => ({ detail: 'Service unhealthy' })
      } as Response);

      await expect(RAGService.checkHealth())
        .rejects.toThrow('Service unhealthy');
    });
  });

  describe('previewContext', () => {
    it('previews context successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockContextSummary
      } as Response);

      const result = await RAGService.previewContext('Machine Learning', [1, 2]);

      expect(result).toHaveProperty('context');
      expect(result).toHaveProperty('preview_text');
      expect(result).toHaveProperty('estimated_questions');
      expect(result.context).toEqual(mockContextSummary);
      expect(result.preview_text).toContain('ml_basics.pdf');
      expect(result.estimated_questions).toBeGreaterThan(0);
    });

    it('handles context preview errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Context retrieval failed'));

      await expect(RAGService.previewContext('Invalid Topic'))
        .rejects.toThrow('Context preview failed: Context retrieval failed');
    });

    it('estimates questions correctly based on chunks', async () => {
      const contextWithManyChunks = {
        ...mockContextSummary,
        total_chunks: 20
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => contextWithManyChunks
      } as Response);

      const result = await RAGService.previewContext('Large Topic');

      expect(result.estimated_questions).toBe(10); // Max 10 questions
    });
  });

  describe('validateRAGRequest', () => {
    it('validates valid RAG request', () => {
      const errors = RAGService.validateRAGRequest(mockRAGExamRequest);
      expect(errors).toHaveLength(0);
    });

    it('validates topic length', () => {
      const invalidRequest = { ...mockRAGExamRequest, topic: 'ab' };
      const errors = RAGService.validateRAGRequest(invalidRequest);
      expect(errors).toContain('Thema muss mindestens 3 Zeichen lang sein');
    });

    it('validates question count range', () => {
      const invalidRequest = { ...mockRAGExamRequest, question_count: 25 };
      const errors = RAGService.validateRAGRequest(invalidRequest);
      expect(errors).toContain('Anzahl Fragen muss zwischen 1 und 20 liegen');
    });

    it('validates question types', () => {
      const invalidRequest = { ...mockRAGExamRequest, question_types: [] };
      const errors = RAGService.validateRAGRequest(invalidRequest);
      expect(errors).toContain('Mindestens ein Fragetyp muss ausgewählt werden');
    });

    it('validates invalid question types', () => {
      const invalidRequest = { ...mockRAGExamRequest, question_types: ['invalid_type'] };
      const errors = RAGService.validateRAGRequest(invalidRequest);
      expect(errors).toContain('Ungültige Fragetypen: invalid_type');
    });

    it('validates difficulty', () => {
      const invalidRequest = { ...mockRAGExamRequest, difficulty: 'impossible' };
      const errors = RAGService.validateRAGRequest(invalidRequest);
      expect(errors).toContain('Ungültiger Schwierigkeitsgrad');
    });

    it('validates language', () => {
      const invalidRequest = { ...mockRAGExamRequest, language: 'fr' };
      const errors = RAGService.validateRAGRequest(invalidRequest);
      expect(errors).toContain('Ungültige Sprache');
    });

    it('validates empty document IDs', () => {
      const invalidRequest = { ...mockRAGExamRequest, document_ids: [] };
      const errors = RAGService.validateRAGRequest(invalidRequest);
      expect(errors).toContain('Mindestens ein Dokument muss ausgewählt werden');
    });
  });

  describe('getRAGRecommendations', () => {
    it('provides recommendations for good context', () => {
      const recommendations = RAGService.getRAGRecommendations(2, 10, 0.8);

      expect(recommendations.recommended_question_count).toBeGreaterThan(0);
      expect(recommendations.recommended_question_types).toContain('multiple_choice');
      expect(recommendations.recommended_difficulty).toBe('hard'); // High similarity
      expect(recommendations.quality_warning).toBeUndefined();
    });

    it('provides recommendations for poor context', () => {
      const recommendations = RAGService.getRAGRecommendations(1, 2, 0.1);

      expect(recommendations.recommended_question_count).toBe(1);
      expect(recommendations.recommended_difficulty).toBe('easy'); // Low similarity
      expect(recommendations.quality_warning).toBeDefined();
    });

    it('warns about low similarity', () => {
      const recommendations = RAGService.getRAGRecommendations(2, 5, 0.15);

      expect(recommendations.quality_warning).toContain('Niedrige Ähnlichkeitswerte');
    });

    it('warns about few chunks', () => {
      const recommendations = RAGService.getRAGRecommendations(2, 2, 0.5);

      expect(recommendations.quality_warning).toContain('Wenige Textabschnitte');
    });

    it('warns about single document with few chunks', () => {
      const recommendations = RAGService.getRAGRecommendations(1, 3, 0.5);

      expect(recommendations.quality_warning).toContain('Nur ein Dokument');
    });

    it('includes more question types for sufficient chunks', () => {
      const recommendations = RAGService.getRAGRecommendations(3, 12, 0.6);

      expect(recommendations.recommended_question_types).toContain('multiple_choice');
      expect(recommendations.recommended_question_types).toContain('open_ended');
      expect(recommendations.recommended_question_types).toContain('true_false');
    });
  });

  describe('formatRAGExamForDisplay', () => {
    it('formats RAG exam for display correctly', () => {
      const formatted = RAGService.formatRAGExamForDisplay(mockRAGExamResponse);

      expect(formatted.id).toBe(mockRAGExamResponse.exam_id);
      expect(formatted.topic).toBe(mockRAGExamResponse.topic);
      expect(formatted.questions).toHaveLength(2);
      expect(formatted.questions[0].id).toBe(1);
      expect(formatted.questions[0].question).toBe('Was ist Machine Learning?');
      expect(formatted.questions[0].sources).toEqual(['ml_basics.pdf', 'ai_intro.txt']);
      expect(formatted.metadata.generation_time).toBe(3.5);
    });

    it('handles array explanations correctly', () => {
      const formatted = RAGService.formatRAGExamForDisplay(mockRAGExamResponse);

      expect(formatted.questions[1].explanation).toBe('Verständnis der Grundlagen\nAnwendungsbeispiele\nKritische Bewertung');
    });
  });

  describe('exportRAGExam', () => {
    it('exports RAG exam as JSON', () => {
      const exported = RAGService.exportRAGExam(mockRAGExamResponse, 'json');

      expect(exported).toBe(JSON.stringify(mockRAGExamResponse, null, 2));
    });

    it('exports RAG exam as text', () => {
      const exported = RAGService.exportRAGExam(mockRAGExamResponse, 'txt');

      expect(exported).toContain('RAG-Prüfung: Machine Learning');
      expect(exported).toContain('Exam ID: test_exam_123');
      expect(exported).toContain('Generierungszeit: 3.50s');
      expect(exported).toContain('Quelldokumente:');
      expect(exported).toContain('ml_basics.pdf');
      expect(exported).toContain('Qualitätsmetriken:');
      expect(exported).toContain('Frage 1 (multiple_choice, medium):');
      expect(exported).toContain('Was ist Machine Learning?');
      expect(exported).toContain('Antwort: B');
      expect(exported).toContain('Konfidenz: 0.85');
    });

    it('handles questions without options in text export', () => {
      const examWithOpenQuestion = {
        ...mockRAGExamResponse,
        questions: [mockRAGExamResponse.questions[1]] // Only open-ended question
      };

      const exported = RAGService.exportRAGExam(examWithOpenQuestion, 'txt');

      expect(exported).toContain('Frage 1 (open_ended, medium):');
      expect(exported).toContain('Erläutern Sie die Grundprinzipien');
      expect(exported).not.toContain('A)'); // No options for open-ended
    });
  });

  describe('API URL Configuration', () => {
    it('uses default API URL when env var not set', async () => {
      delete process.env.REACT_APP_API_URL;
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockQuestionTypes
      } as Response);

      await RAGService.getQuestionTypes();

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/rag/question-types',
        expect.any(Object)
      );
    });

    it('uses custom API URL from env var', async () => {
      process.env.REACT_APP_API_URL = 'https://api.example.com';
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockQuestionTypes
      } as Response);

      await RAGService.getQuestionTypes();

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.example.com/api/v1/rag/question-types',
        expect.any(Object)
      );
    });
  });

  describe('Error Handling', () => {
    it('handles JSON parsing errors gracefully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => { throw new Error('Invalid JSON'); }
      } as Response);

      await expect(RAGService.getQuestionTypes())
        .rejects.toThrow('Failed to fetch question types: Internal Server Error');
    });

    it('handles network timeouts', async () => {
      mockFetch.mockImplementation(() => 
        new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Network timeout')), 100)
        )
      );

      await expect(RAGService.getQuestionTypes())
        .rejects.toThrow('Network timeout');
    });

    it('handles malformed API responses', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => null
      } as Response);

      const result = await RAGService.getQuestionTypes();
      expect(result).toBeNull();
    });
  });

  describe('Edge Cases', () => {
    it('handles empty context in preview', async () => {
      const emptyContext = {
        query: 'Empty Topic',
        total_chunks: 0,
        total_similarity_score: 0,
        source_documents: [],
        context_length: 0
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => emptyContext
      } as Response);

      const result = await RAGService.previewContext('Empty Topic');

      expect(result.estimated_questions).toBe(0);
      expect(result.preview_text).toContain('0');
    });

    it('handles very large context', async () => {
      const largeContext = {
        ...mockContextSummary,
        total_chunks: 100,
        context_length: 50000
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => largeContext
      } as Response);

      const result = await RAGService.previewContext('Large Topic');

      expect(result.estimated_questions).toBe(10); // Capped at 10
    });
  });
});
