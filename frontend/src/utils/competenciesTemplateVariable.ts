/**
 * The prompt-template variable the competency full text is injected into.
 *
 * Must match the backend syntax exactly: prompt templates are rendered with
 * Jinja2 (premium/backend/services/prompt_service.py,
 * `render_prompt_with_jinja2`), and the seeded default templates reference the
 * variable as `{{ competencies }}` (premium/backend/scripts/seed_prompts.py).
 */
export const COMPETENCIES_TEMPLATE_VARIABLE = '{{ competencies }}';

/**
 * i18next options for help texts that show the template variable literally
 * (`… als {{ competencies }} in die Generierung …`).
 *
 * i18next reads `{{ competencies }}` in a translation as its own placeholder.
 * Without a value, the output depends on the global config: with the default
 * `skipOnVariables: true` the braces happen to survive, with `false` they are
 * blanked and i18next logs "missed to pass in variable". Passing the literal
 * as the value makes the text explicit; pinning `skipOnVariables` per call
 * keeps i18next from re-scanning the inserted value, whatever the global
 * config says.
 */
export const COMPETENCIES_HELPER_I18N_OPTIONS = {
  competencies: COMPETENCIES_TEMPLATE_VARIABLE,
  interpolation: { skipOnVariables: true },
};
