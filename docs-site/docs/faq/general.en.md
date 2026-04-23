# Frequently Asked Questions

## General

**How many documents can I upload?**

Depending on your plan:

- Free: 5 documents
- Starter: 50 documents
- Professional: Unlimited

**Which languages are supported?**

Currently German and English. More languages are planned.

**Can I export questions?**

Currently only manually. PDF/JSON/Moodle XML export is in development.

## Review Queue and Exam Composer

**What is the Review Queue?**

The Review Queue is the area where AI-generated questions are manually reviewed and
approved before they can be used in the Exam Composer.
Only approved questions are available for exam composition.

→ More details: [Review Queue](../user-guide/review-queue.md)

**What is the Exam Composer?**

The Exam Composer allows you to assemble approved questions into a complete exam
and export it in various formats (PDF, Word, JSON).

→ More details: [Exam Composer](../user-guide/exam-composer.md)

## Subscription

**How many questions can I generate per month?**

That depends on your subscription plan:

| Plan | Questions per month |
|------|-------------------|
| Free | 20 |
| Starter | 200 |
| Professional | Unlimited |
| Enterprise | Unlimited |

→ More details: [Subscription](../user-guide/subscription.md)

**Where do I find the Prompt Library?**

The Prompt Library is accessible via the navigation under **Prompts** (route: `/prompts`).
It is available to users with the ADMIN and DOZENT roles.

→ More details: [Prompt Library](../user-guide/prompt-library.md)

**What happens to my data if I downgrade my subscription?**

Your data (documents, questions, exams) is fully retained.
You can access it, but cannot create new items once the limits of the
lower plan are reached. Premium features like Document Chat are no longer
accessible until you upgrade again.

## Technical

**Why does processing take so long?**

Large PDFs (over 20 pages) require more time for text extraction and indexing. Scanned PDFs require additional OCR processing.

**What happens to my data?**

All data is stored encrypted. Uploaded documents remain on the servers and are not shared with third parties.

**Can I work offline?**

No, ExamCraft AI requires an internet connection for all AI features (embedding calculation and question generation).
