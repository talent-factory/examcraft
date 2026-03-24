/**
 * Empty Module Placeholder
 *
 * This module is used as a replacement for missing Premium/Enterprise packages
 * when they are not available in the deployment (e.g., Core-only deployment).
 *
 * All exports are empty objects/functions that will be caught by the
 * componentLoader's .catch() handlers and replaced with FeatureUnavailable components.
 */

// Export empty objects for all Premium/Enterprise components
export const RAGExamCreator = {};
export const DocumentChatPage = {};
export const PromptLibraryWithUpload = {};
export const PromptTemplateSelector = {};
export const CustomBranding = {};
export const SSOConfiguration = {};
export const RAGService = {};

// Default export (in case someone imports the whole module)
const emptyModule = {};
export default emptyModule;
