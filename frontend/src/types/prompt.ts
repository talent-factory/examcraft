/**
 * TypeScript Types for Prompt Management
 *
 * Defines interfaces for Prompt Library, Template Selection,
 * and Prompt Configuration in Question Generation.
 */

/**
 * Prompt Categories
 */
export enum PromptCategory {
  SYSTEM_PROMPT = 'system_prompt',
  USER_PROMPT = 'user_prompt',
  FEW_SHOT_EXAMPLE = 'few_shot_example',
  TEMPLATE = 'template'
}

/**
 * Question Types for Prompt Selection
 */
export enum QuestionType {
  MULTIPLE_CHOICE = 'multiple_choice',
  OPEN_ENDED = 'open_ended',
  TRUE_FALSE = 'true_false'
}

/**
 * Main Prompt Interface
 * Matches backend Prompt model
 */
export interface Prompt {
  id: string;
  name: string;
  content: string;
  description?: string;
  category: PromptCategory;
  tags: string[];
  use_case: string;
  version: number;
  is_active: boolean;
  parent_id?: string;
  author_id?: string;
  created_at: string;
  updated_at: string;
  last_used_at?: string;
  usage_count: number;
  tokens_estimated?: number;
  qdrant_point_id?: string;
}

/**
 * Prompt Template Interface
 * For templates with variables
 */
export interface PromptTemplate {
  id: string;
  name: string;
  template: string;
  description?: string;
  category: PromptCategory;
  variables: string[];
  default_values?: Record<string, any>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/**
 * Template Variable Definition
 * Describes a single variable in a prompt template
 */
export interface TemplateVariable {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'select';
  required: boolean;
  default?: any;
  options?: string[];
  description?: string;
  placeholder?: string;
}

/**
 * Prompt Selection State
 * Tracks selected prompts for each question type
 */
export interface PromptSelection {
  multiple_choice: string | null;  // Prompt ID
  open_ended: string | null;
  true_false: string | null;
}

/**
 * Prompt Configuration
 * Combines prompt ID with template variables
 */
export interface PromptConfig {
  prompt_id: string;
  variables?: Record<string, any>;
}

/**
 * Prompt Configuration per Question Type
 * Used in RAG Exam Request
 */
export interface PromptConfigMap {
  multiple_choice?: PromptConfig;
  open_ended?: PromptConfig;
  true_false?: PromptConfig;
}

/**
 * Prompt Preview Props
 * Props for PromptPreview component
 */
export interface PromptPreviewProps {
  promptId: string | null;
  showMetadata?: boolean;
  showUsageStats?: boolean;
  compact?: boolean;
}

/**
 * Prompt Template Selector Props
 * Props for PromptTemplateSelector component
 */
export interface PromptTemplateSelectorProps {
  questionType: QuestionType;
  selectedPromptId: string | null;
  onPromptSelect: (promptId: string | null) => void;
  onVariablesChange?: (variables: Record<string, any>) => void;
  autoFilledVariables?: Record<string, any>;
  disabled?: boolean;
  showPreview?: boolean;
}

/**
 * Prompt List Response
 * API response for listing prompts
 */
export interface PromptListResponse {
  prompts: Prompt[];
  total: number;
  page?: number;
  page_size?: number;
}

/**
 * Prompt Render Preview Request
 * Request for rendering prompt with variables
 */
export interface PromptRenderRequest {
  prompt_id?: string;
  prompt_content?: string;
  variables: Record<string, any>;
  strict?: boolean;
}

/**
 * Prompt Render Preview Response
 * Response from prompt rendering
 */
export interface PromptRenderResponse {
  rendered_content: string;
  variables_used: string[];
}

/**
 * Template Variables Extraction Response
 * Response from extracting variables from template
 */
export interface TemplateVariablesResponse {
  prompt_id: string;
  variables: string[];  // Array of variable names
  prompt_content_preview: string;
}

/**
 * Prompt Usage Log
 * Tracks prompt usage for analytics
 */
export interface PromptUsageLog {
  id: string;
  prompt_id: string;
  use_case: string;
  user_id?: string;
  success: boolean;
  error_message?: string;
  execution_time_ms?: number;
  tokens_used?: number;
  created_at: string;
}

/**
 * Prompt Search Filters
 * Filters for searching prompts
 */
export interface PromptSearchFilters {
  category?: PromptCategory;
  use_case?: string;
  is_active?: boolean;
  tags?: string[];
  search_query?: string;
}

/**
 * Prompt Metadata Display
 * Formatted metadata for UI display
 */
export interface PromptMetadata {
  name: string;
  version: number;
  category: string;
  use_case: string;
  tags: string[];
  usage_count: number;
  last_used?: string;
  created_at: string;
  author?: string;
}

/**
 * Helper function to format prompt metadata for display
 */
export function formatPromptMetadata(prompt: Prompt): PromptMetadata {
  return {
    name: prompt.name,
    version: prompt.version,
    category: prompt.category,
    use_case: prompt.use_case,
    tags: prompt.tags,
    usage_count: prompt.usage_count,
    last_used: prompt.last_used_at,
    created_at: prompt.created_at,
    author: prompt.author_id
  };
}

/**
 * Helper function to get use case for question type
 */
export function getUseCaseForQuestionType(questionType: QuestionType): string {
  return `question_generation_${questionType}`;
}

/**
 * Helper function to check if prompt is compatible with question type
 */
export function isPromptCompatible(prompt: Prompt, questionType: QuestionType): boolean {
  const expectedUseCase = getUseCaseForQuestionType(questionType);
  return prompt.use_case === expectedUseCase && prompt.is_active;
}
