# Questions fréquemment posées

## Général

**Combien de documents puis-je télécharger?**

Selon votre plan:

- Free: 5 documents
- Starter: 50 documents
- Professional: Illimité

**Quelles langues sont supportées?**

Actuellement l'allemand et l'anglais. D'autres langues sont prévues.

**Puis-je exporter des questions?**

Actuellement uniquement manuellement. L'export PDF/JSON/Moodle XML est en développement.

## Review Queue et Exam Composer

**Qu'est-ce que la Review Queue?**

La Review Queue est le domaine dans lequel les questions générées par l'IA sont vérifiées manuellement et
libérées avant de pouvoir être utilisées dans Exam Composer.
Seules les questions approuvées sont disponibles pour l'assemblage des examens.

→ En savoir plus: [Review Queue](../user-guide/review-queue.md)

**Qu'est-ce qu'Exam Composer?**

Exam Composer permet d'assembler des questions approuvées en un examen complet
et de l'exporter dans différents formats (PDF, Word, JSON).

→ En savoir plus: [Exam Composer](../user-guide/exam-composer.md)

## Abonnement

**Combien de questions puis-je générer par mois?**

Cela dépend de votre plan d'abonnement:

| Plan | Questions par mois |
|------|-----------------|
| Free | 20 |
| Starter | 200 |
| Professional | Illimité |
| Enterprise | Illimité |

→ En savoir plus: [Abonnement](../user-guide/subscription.md)

**Où trouver la Bibliothèque de prompts?**

La Bibliothèque de prompts est accessible via la navigation sous **Prompts** (Route: `/prompts`).
Elle est disponible pour les utilisateurs avec les rôles ADMIN et PROFESSEUR.

→ En savoir plus: [Bibliothèque de prompts](../user-guide/prompt-library.md)

**Que se passe-t-il avec mes données lors d'une rétrogradation d'abonnement?**

Vos données (documents, questions, examens) sont entièrement conservées.
Vous pouvez y accéder, mais ne pouvez pas en créer de nouvelles une fois que les limites du plan
inférieur sont atteintes. Les fonctionnalités premium comme le chat de documents ne sont plus
accessibles jusqu'à ce que vous mettiez à niveau.

## Technique

**Pourquoi le traitement prend-il si longtemps?**

Les gros PDFs (plus de 20 pages) nécessitent plus de temps pour l'extraction de texte et l'indexation. Les PDFs numérisés nécessitent également un traitement OCR supplémentaire.

**Que deviennent mes données?**

Toutes les données sont stockées de manière chiffrée. Les documents téléchargés restent sur les serveurs et ne sont pas partagés avec des tiers.

**Puis-je travailler hors ligne?**

Non, ExamCraft AI nécessite une connexion Internet pour les fonctionnalités AI (calcul d'embeddings et génération de questions).
