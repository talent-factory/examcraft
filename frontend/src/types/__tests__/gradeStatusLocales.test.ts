import de from "../../locales/de/translation.json";
import en from "../../locales/en/translation.json";
import fr from "../../locales/fr/translation.json";
import itLocale from "../../locales/it/translation.json";
import { GRADE_STATUSES, SUBMISSION_GRADE_STATUSES } from "../submission";

const LOCALES = { de, en, fr, it: itLocale } as const;

describe("auswertungen.exam.gradeStatus locales", () => {
  const expected = [...GRADE_STATUSES, ...SUBMISSION_GRADE_STATUSES];

  it.each(Object.entries(LOCALES))(
    "defines every grade status in %s",
    (_lang, translation) => {
      const labels = (
        translation as unknown as {
          auswertungen?: { exam?: { gradeStatus?: Record<string, string> } };
        }
      ).auswertungen?.exam?.gradeStatus as Record<string, string>;
      expect(labels).toBeDefined();
      for (const status of expected) {
        expect(labels).toHaveProperty([status]);
        expect(labels[status]).toBeTruthy();
      }
    },
  );
});
