import { PromptConfig } from './prompt';
import type { SupportedLanguage } from './auth';

export enum DocumentStatus {
  // Async-processing lifecycle (mirrors backend models.document.DocumentStatus).
  QUEUED = 'queued',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  // Legacy statuses kept for backward compatibility with older rows.
  UPLOADED = 'uploaded',
  PROCESSED = 'processed',
  ERROR = 'error'
}

/** Document sharing scope (TF-354/TF-620). Mirrors the backend DocumentVisibility enum. */
export enum DocumentVisibility {
  PRIVATE = 'private',
  TEAM = 'team',
  INSTITUTION = 'institution'
}

/**
 * Quality verdict reasons (TF-360). Mirrors backend
 * services.quality_assessor.QualityReason. Kept as a string union for
 * exhaustive UI mapping; `string` fallback tolerates future backend reasons.
 */
export type QualityReason =
  | 'ok'
  | 'scanned_low_text'
  | 'single_chunk_large_file'
  | 'garbage_extraction'
  | 'ocr_pages_discarded';

/**
 * Extraction-quality verdict exposed by the backend (TF-360) via
 * `Document.to_dict().quality`. `null` when no verdict was computed
 * (e.g. vectorisation failed before assessment).
 */
export interface DocumentQuality {
  ok: boolean;
  reason: QualityReason | string;
  signals?: Record<string, unknown>;
}

/**
 * OCR-Eskalations-State (TF-360/TF-365). Mirrors backend
 * services.quality_assessor.EscalationState. Exposed via
 * `Document.to_dict().escalation` so the UI can surface an in-flight or failed
 * OCR re-processing pass:
 *   - `queued`       — OCR re-processing queued/running (document still PROCESSED)
 *   - `failed`       — OCR re-processing failed (document flipped to ERROR)
 *   - `exhausted`    — OCR ran, quality still insufficient
 *   - `unavailable`  — escalation needed but OCR not available
 *   - `completed` / `not_needed` / `no_verdict` — no user-facing action
 * Closed union mirroring the backend Literal; an unknown value (deploy skew)
 * simply matches no badge branch and falls through to the default badges.
 */
export type DocumentEscalation =
  | 'queued'
  | 'completed'
  | 'exhausted'
  | 'unavailable'
  | 'failed'
  | 'not_needed'
  | 'no_verdict';

export interface Document {
  id: number;
  filename: string;
  original_filename: string;
  title: string;
  display_name?: string | null;
  mime_type: string;
  status: DocumentStatus;
  visibility?: DocumentVisibility;
  // Set only when visibility=team (TF-620).
  org_unit_id?: number | null;
  // Resolved OrgUnit.name, for display — set only when org_unit_id is set.
  org_unit_name?: string | null;
  created_at: string;
  processed_at?: string;
  file_size?: number;
  has_vectors: boolean;
  // Owner user id. Backend returns an int (DocumentResponse.user_id: Optional[int]).
  user_id?: number;
  content_preview?: string;
  vector_collection?: string;
  updated_at?: string;
  tags?: DocumentTag[];
  // OCR-/Qualitäts-Eskalation (TF-360/TF-361/TF-365). Backend befüllt diese Felder
  // dateiformat-unabhängig (PDF + gescanntes DOCX) via Document.to_dict.
  processed_with_ocr?: boolean;
  quality?: DocumentQuality | null;
  // OCR-Eskalations-State (TF-365): macht laufende (`queued`) oder fehlgeschlagene
  // (`failed`) OCR-Nachbearbeitung im UI sichtbar. `null`/undefined bei Altrows.
  escalation?: DocumentEscalation | null;
  metadata?: {
    total_chunks?: number;
    embedding_model?: string;
    processing_time?: number;
    error?: string;
    error_code?: string;
    error_details?: { filename?: string; mime_type?: string; [key: string]: any };
    vector_embedding_error?: string;
    [key: string]: any;
  };
}

export interface DocumentTag {
  id: number;
  name: string;
  scope: 'user' | 'institution' | 'global';
  is_own: boolean;
  // TF-399: true when this is a *personal* assignment of the current user
  // (document_personal_tags) rather than a shared institution assignment.
  // Only present on a document's `tags`; absent in the available-tags list.
  is_personal?: boolean;
}

export interface DocumentStats {
  total: number;
  processed: number;
  with_vectors: number;
  in_progress: number;
}

export type DocumentSort =
  | 'created_at_desc' | 'created_at_asc'
  | 'title_asc' | 'title_desc'
  | 'size_desc' | 'size_asc';

export type MimeFamily = 'pdf' | 'word' | 'markdown' | 'text' | 'chat';
export type StatusGroup = 'uploaded' | 'processing' | 'processed' | 'error';
export type VisibilityFilter = 'own' | 'shared';
export type ViewMode = 'cards' | 'list';

export interface DocumentListParams {
  q?: string;
  visibility?: VisibilityFilter;
  status?: StatusGroup[];
  mime_family?: MimeFamily[];
  tag_ids?: number[];
  sort?: DocumentSort;
  page?: number;
  page_size?: number;
}

export interface DocumentListResponse {
  documents: Document[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  stats: DocumentStats;
}

export interface DocumentUploadResponse {
  document_id: number;
  filename: string;
  message: string;
}

export interface DocumentProcessingResponse {
  message: string;
  document_id: number;
  processing_stats?: {
    total_chunks: number;
    embedding_dimension: number;
    model_name: string;
    processing_time: number;
  };
}

export interface AvailableDocumentsResponse {
  total_documents: number;
  processed_documents: number;
  documents_with_vectors: number;
  documents: Document[];
}

export interface RAGExamRequest {
  topic: string;
  document_ids?: number[];
  question_count: number;
  question_types: string[];
  difficulty: string;
  language: string;
  context_chunks_per_question?: number;
  prompt_config?: {
    single_choice?: PromptConfig;
    open_ended?: PromptConfig;
    true_false?: PromptConfig;
  };
  tag_ids?: number[];
  /** TF-400: Kompetenzrahmen-ID; Backend lädt rendered_text, wenn kein Override gesetzt ist. */
  framework_id?: number;
  /** TF-400: Editierter Kompetenzen-Volltext; gewinnt über framework_id (verbatim {{ competencies }}). */
  competencies_override?: string;
}

export interface RAGQuestion {
  question_text: string;
  question_type: string;
  options?: string[];
  correct_answer?: string;
  explanation?: string | string[];
  difficulty: string;
  source_chunks: string[];
  source_documents: string[];
  confidence_score: number;
  bloom_level?: number;
  estimated_time_minutes?: number;
  quality_tier?: string;
  review_status?: string;
  reviewed_by?: string;
  reviewed_at?: string;
}

export interface RAGContextSummary {
  query: string;
  total_chunks: number;
  total_similarity_score: number;
  source_documents: Array<{
    id: number;
    filename: string;
    /** TF-605: Anzeigename aus der Dokumentbibliothek — für die Anzeige dem
     *  `filename` vorziehen. Optional, weil ältere Responses ihn nicht führen. */
    title?: string;
    chunks_used: number;
  }>;
  context_length: number;
}

export interface RAGExamResponse {
  exam_id: string;
  topic: string;
  questions: RAGQuestion[];
  context_summary: RAGContextSummary;
  generation_time: number;
  review_question_ids?: number[];
  persistence_warning?: string;
  quality_metrics: {
    total_questions: number;
    average_confidence: number;
    source_coverage: number;
    question_type_distribution: Record<string, number>;
    context_chunks_used: number;
    total_context_length: number;
    average_similarity_score: number;
    // TF-358: requested_/generated_question_count werden bei jeder
    // RAG-Generierung gesetzt. context_limited(_notice) nur, wenn die
    // Fragenanzahl ans verfügbare Chunk-Material gekoppelt wurde (weniger
    // Fragen erzeugt als angefordert). Alle optional (Backward-Compat).
    requested_question_count?: number;
    generated_question_count?: number;
    context_limited?: boolean;
    context_limited_notice?: string;
  };
}

export interface QuestionTypeInfo {
  type: string;
  name: string;
  description: string;
  example: string;
}

export interface DifficultyLevel {
  level: string;
  name: string;
  description: string;
}

// TF-626: Hiess `SupportedLanguage` und kollidierte damit im Barrel
// (types/index.ts) mit dem gleichnamigen Union-Typ aus auth.ts
// ('de' | 'en' | 'fr' | 'it'). TypeScript loeste die Mehrdeutigkeit auf,
// indem es den Namen aus dem Re-Export ganz herausnahm (TS2308) — beide
// Typen waren ueber `@examcraft/core/types` also gar nicht erreichbar.
// Dieser hier ist ein API-DTO (Eintrag in QuestionTypesResponse), nicht die
// Spracheinstellung des Nutzers.
//
// TF-626-Review (Suggestion): `code` war zuvor `string` — der einzige
// tatsaechliche Erzeuger (core/backend/api/rag_exams.py:supported_languages)
// gibt aber ausschliesslich Werte aus exakt derselben Menge wie
// `SupportedLanguage` aus auth.ts ('de' | 'en' | 'fr' | 'it') zurueck. Ohne
// diese Kopplung wuerde ein Tippfehler im Backend ('deu', 'DE') hier
// stillschweigend durchgehen.
export interface SupportedLanguageOption {
  code: SupportedLanguage;
  name: string;
}

export interface QuestionTypesResponse {
  supported_types: QuestionTypeInfo[];
  difficulty_levels: DifficultyLevel[];
  supported_languages: SupportedLanguageOption[];
}

/** State of a single generation task tracked by GenerationTasksContext */
export interface GenerationTaskState {
  taskId: string;
  status: 'PENDING' | 'STARTED' | 'PROGRESS' | 'SUCCESS' | 'FAILURE' | 'REVOKED' | 'RETRY' | 'UNKNOWN';
  progress: number;
  message: string | null;
  topic: string | null;
  questionCount: number | null;
  createdAt: string;
  result: RAGExamResponse | null;
}

/**
 * Response from GET /api/v1/rag/active-tasks.
 *
 * Enthält seit TF-608 nicht nur laufende, sondern auch kürzlich abgeschlossene
 * Tasks (terminaler `status`), damit eine während eines Seitenwechsels fertig
 * gewordene Generierung erreichbar bleibt. Das Ergebnis reist nicht mit — es
 * wird per `GET /api/v1/rag/tasks/{task_id}/result` nachgeladen.
 */
export interface ActiveTaskInfo {
  task_id: string;
  status: string;
  progress: number;
  message: string | null;
  created_at: string;
  topic: string | null;
  question_count: number | null;
}

export interface ActiveTasksResponse {
  tasks: ActiveTaskInfo[];
}

/**
 * Response from GET /api/v1/rag/tasks/{task_id}/result (TF-608).
 *
 * `result` ist `null`, wenn das Celery-Result-Backend den Eintrag bereits
 * verworfen hat — der Task bleibt dann sichtbar, nur ohne Detailansicht.
 */
export interface TaskResultResponse {
  task_id: string;
  status: string;
  result: RAGExamResponse | null;
  error: string | null;
}

/** Context value exposed by GenerationTasksContext */
export interface GenerationTasksContextType {
  tasks: Record<string, GenerationTaskState>;
  activeTasks: GenerationTaskState[];
  completedTasks: GenerationTaskState[];
  startGeneration: (request: RAGExamRequest) => Promise<string>;
  retryTask: (taskId: string) => Promise<string>;
  dismissTask: (taskId: string) => void;
  getTask: (taskId: string) => GenerationTaskState | undefined;
}
