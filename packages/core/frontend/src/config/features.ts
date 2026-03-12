/**
 * Feature Configuration for ExamCraft AI
 * Defines features per subscription tier matching backend config/features.py
 */

export enum SubscriptionTier {
  FREE = 'free',
  STARTER = 'starter',
  PROFESSIONAL = 'professional',
  ENTERPRISE = 'enterprise',
}

export enum Feature {
  // Core Features (Free Tier)
  DOCUMENT_UPLOAD = 'document_upload',
  BASIC_QUESTION_GENERATION = 'basic_question_generation',
  DOCUMENT_LIBRARY = 'document_library',

  // Starter Tier Features
  RAG_GENERATION = 'rag_generation',
  PROMPT_TEMPLATES = 'prompt_templates',
  BATCH_PROCESSING = 'batch_processing',

  // Professional Tier Features
  DOCUMENT_CHATBOT = 'document_chatbot',
  ADVANCED_PROMPT_MANAGEMENT = 'advanced_prompt_management',
  ANALYTICS_DASHBOARD = 'analytics_dashboard',
  QUESTION_REVIEW_WORKFLOW = 'question_review_workflow',
  EXPORT_FORMATS = 'export_formats',

  // Enterprise Tier Features
  SSO_INTEGRATION = 'sso_integration',
  CUSTOM_BRANDING = 'custom_branding',
  API_ACCESS = 'api_access',
  ADVANCED_ANALYTICS = 'advanced_analytics',
  PRIORITY_SUPPORT = 'priority_support',
  LDAP_INTEGRATION = 'ldap_integration',
  AUDIT_LOGS = 'audit_logs',
  MULTI_ORGANIZATION = 'multi_organization',
}

/**
 * Feature to Tier Mapping
 * Matches backend config/features.py TIER_FEATURES
 */
const TIER_FEATURES: Record<SubscriptionTier, Feature[]> = {
  [SubscriptionTier.FREE]: [
    Feature.DOCUMENT_UPLOAD,
    Feature.BASIC_QUESTION_GENERATION,
    Feature.DOCUMENT_LIBRARY,
  ],
  [SubscriptionTier.STARTER]: [
    Feature.DOCUMENT_UPLOAD,
    Feature.BASIC_QUESTION_GENERATION,
    Feature.DOCUMENT_LIBRARY,
    Feature.RAG_GENERATION,
    Feature.PROMPT_TEMPLATES,
    Feature.BATCH_PROCESSING,
  ],
  [SubscriptionTier.PROFESSIONAL]: [
    Feature.DOCUMENT_UPLOAD,
    Feature.BASIC_QUESTION_GENERATION,
    Feature.DOCUMENT_LIBRARY,
    Feature.RAG_GENERATION,
    Feature.PROMPT_TEMPLATES,
    Feature.BATCH_PROCESSING,
    Feature.DOCUMENT_CHATBOT,
    Feature.ADVANCED_PROMPT_MANAGEMENT,
    Feature.ANALYTICS_DASHBOARD,
    Feature.QUESTION_REVIEW_WORKFLOW,
    Feature.EXPORT_FORMATS,
  ],
  [SubscriptionTier.ENTERPRISE]: [
    Feature.DOCUMENT_UPLOAD,
    Feature.BASIC_QUESTION_GENERATION,
    Feature.DOCUMENT_LIBRARY,
    Feature.RAG_GENERATION,
    Feature.PROMPT_TEMPLATES,
    Feature.BATCH_PROCESSING,
    Feature.DOCUMENT_CHATBOT,
    Feature.ADVANCED_PROMPT_MANAGEMENT,
    Feature.ANALYTICS_DASHBOARD,
    Feature.QUESTION_REVIEW_WORKFLOW,
    Feature.EXPORT_FORMATS,
    Feature.SSO_INTEGRATION,
    Feature.CUSTOM_BRANDING,
    Feature.API_ACCESS,
    Feature.ADVANCED_ANALYTICS,
    Feature.PRIORITY_SUPPORT,
    Feature.LDAP_INTEGRATION,
    Feature.AUDIT_LOGS,
    Feature.MULTI_ORGANIZATION,
  ],
};

/**
 * Get all features available for a subscription tier
 */
export const getTierFeatures = (tier: SubscriptionTier): Feature[] => {
  return TIER_FEATURES[tier] || TIER_FEATURES[SubscriptionTier.FREE];
};

/**
 * Check if a subscription tier has a specific feature
 */
export const hasFeature = (tier: SubscriptionTier, feature: Feature | string): boolean => {
  const features = getTierFeatures(tier);
  return features.includes(feature as Feature);
};

/**
 * Check if a feature string matches a known Feature enum value
 */
export const isFeatureName = (featureName: string): boolean => {
  return Object.values(Feature).includes(featureName as Feature);
};
