const LOCALE_MAP: Record<string, string> = {
  de: 'de-CH',
  fr: 'fr-CH',
  it: 'it-CH',
  en: 'en-GB',
};

export function getDateLocale(lang: string): string {
  return LOCALE_MAP[lang] || lang;
}
