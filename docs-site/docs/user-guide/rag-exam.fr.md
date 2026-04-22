# Examens basés sur RAG

!!! note "Prérequis"
    Pour les examens RAG, vous devez d'abord télécharger et traiter des documents.
    Voir [Gérer les documents](documents.md).

## Qu'est-ce que RAG?

**RAG** (Retrieval-Augmented Generation) combine:

- **Retrieval**: Recherche sémantique dans vos documents
- **Generation**: Création de questions basée sur l'IA

L'avantage: Les questions sont directement dérivées de vos matériels de cours et incluent des références sources.

## Prérequis

- Au moins 1 document téléchargé et traité
- Document sélectionné dans la bibliothèque

## Étape par étape

### 1. Sélectionner les documents

Dans la bibliothèque de documents:

1. Sélectionnez 1–10 documents
2. Cliquez sur **Créer un examen à partir de la sélection**

!!! tip "Nombre optimal de documents"
    3–5 documents offrent la meilleure qualité. Trop de documents peuvent diluer les résultats.

### 2. Configuration RAG

- **Sujet/Domaine**: Domaine spécifique (p. ex. «Complexité des algorithmes de tri»). Laissez vide pour des questions générales.
- **Nombre de questions**: 1–20, recommandé 5–10
- **Types de questions**: Choix multiples, Questions ouvertes, Vrai/Faux
- **Niveau de difficulté**: Facile / Moyen / Difficile
- **Modèle de prompt**: Choisissez un modèle de prompt avec aperçu en direct

### 3. Démarrer la génération

Cliquez sur **Générer l'examen RAG**. Temps d'attente: 20–60 secondes.

### 4. Vérifier les résultats

Chaque question contient:

- Texte et options de réponse
- Réponse correcte avec explication
- **Documents sources** (avec numéro de page)
- **Indice de confiance** (0–1)

## Indicateurs de qualité

| Indice de confiance | Évaluation |
|---------|------|
| 0.9–1.0 | Très haute qualité |
| 0.7–0.9 | Bonne qualité |
| 0.5–0.7 | Acceptable – Vérifier |
| < 0.5 | Révision recommandée |

## Après la génération

Les questions générées apparaissent automatiquement dans la **[Review Queue](review-queue.md)**.
Vérifiez et approuvez chaque question avant de l'assembler dans
**[Exam Composer](exam-composer.md)** pour créer un examen.

!!! tip "Qualité des questions RAG"
    La qualité des questions générées dépend fortement de la qualité des documents sources.
    Les documents bien structurés avec des titres clairs donnent de meilleurs résultats.
    Voir [Meilleures pratiques](best-practices.md).

## Questions fréquentes sur les examens RAG

**Quelle est la différence entre l'indice de confiance et la qualité?**

L'indice de confiance (0–1) montre à quel point l'IA est sûre que la question et la réponse sont correctement dérivées des documents. Un score élevé (0.9+) signifie une haute pertinence et exactitude. Les questions avec un score faible (< 0.5) doivent être révisées ou rejetées dans la Review Queue.

**Quels types de documents fonctionnent le mieux?**

Les fichiers PDF et Markdown avec une structure claire fonctionnent mieux:
- PDFs avec texte consultable (pas de scans)
- Documents avec des titres et sous-titres
- Contenu textuel structuré plutôt que du texte sans formatage
- Évitez les très longs paragraphes sans structure

**L'IA peut-elle inventer du contenu qui n'est pas dans les documents?**

C'est rare, mais possible. Une question générée pourrait être logique mais ne pas apparaître exactement dans les documents sources. C'est la raison principale pour laquelle la vérification et la vérification des sources sont importantes. Vérifiez les documents sources indiqués et les numéros de page lors de chaque révision.

**Combien de documents dois-je sélectionner?**

**Optimal: 3–5 documents.** Trop peu de documents (1–2) peuvent donner des informations contextuelles insuffisantes. Trop de documents (10+) peuvent conduire à des questions diluées ou inexactes. Expérimentez et observez les indices de confiance.

**Puis-je utiliser RAG avec des images dans les documents?**

Actuellement, RAG est principalement optimisé pour le contenu textuel. Les images ne sont pas utilisées comme source. Si vos documents contiennent principalement des diagrammes ou des images, utilisez plutôt des examens AI (sans RAG) et décrivez le sujet dans l'entrée.

**Comment mettre à jour les documents pour de meilleurs résultats RAG?**

1. Téléchargez une nouvelle version du document
2. Sélectionnez la nouvelle version dans la bibliothèque de documents
3. La génération RAG suivante utilise automatiquement la nouvelle version
4. Les versions antérieures peuvent être supprimées (voir [Gérer les documents](documents.md))

## Structure optimale des documents pour RAG

Pour de meilleurs résultats avec RAG, les documents doivent avoir la structure suivante:

```
# Sujet principal

## Section 1
Texte explicatif avec des concepts et définitions clairs.

### Sous-section 1.1
Plus de détails sur le sujet.

## Section 2
Autres contenus connexes.

- Points de liste pour les résumés
- Listes numérotées pour les processus
```

Évitez les textes non structurés. Une bonne documentation avec des titres clairs améliore considérablement la qualité de RAG.
