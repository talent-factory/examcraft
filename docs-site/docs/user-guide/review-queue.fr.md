# Review Queue

La Review Queue est le lieu central pour vérifier manuellement et approuver les questions générées par l'IA. Ce n'est qu'après approbation dans la Review Queue que les questions sont disponibles dans [Exam Composer](exam-composer.md).

!!! note "Pourquoi une Review Queue?"
    Les questions générées par l'IA sont un point de départ, pas un produit fini. La Review Queue
    vous donne le contrôle de la qualité de vos examens — vous décidez quelles questions sont assez bonnes.

<!-- screenshot: review-queue-overview.png -->

## Aperçu des statuts

Chaque question a l'un des quatre statuts possibles:

| Statut | Couleur | Signification |
|--------|-------|-----------|
| En attente | Orange | Nouvellement générée, pas encore vérifiée |
| En révision | Bleu | Actuellement en cours de vérification |
| Approuvée | Vert | Publiée pour Exam Composer |
| Rejetée | Rouge | Non utilisable, archivée |

## Filtrer et rechercher des questions

Utilisez les options de filtre pour garder la Queue claire:

- **Statut**: En attente / En révision / Approuvée / Rejetée
- **Difficulté**: Facile / Moyen / Difficile
- **Type de question**: Choix multiples / Question ouverte
- **Période**: Filtrer par date de génération

## Vérifier une question — Étape par étape

### Étape 1: Ouvrir la question

Cliquez sur une question avec le statut «En attente» dans la vue liste.
La question passe automatiquement au statut «En révision».

<!-- screenshot: review-queue-detail.png -->

### Étape 2: Vérifier le contenu

Dans la vue détaillée, vous voyez:

| Champ | Description |
|------|-------------|
| Texte de la question | La question d'examen réelle |
| Type de question | Choix multiples ou question ouverte |
| Difficulté | Facile / Moyen / Difficile |
| Options de réponse | Pour choix multiples: toutes les options y compris la réponse correcte |
| Explication | Justification de la réponse correcte |
| Source | Passage textuel du document source |
| Indice de confiance | Évaluation de la confiance de l'IA (0–1) |

Vérifiez particulièrement:
- Le texte de la question est-il clair et sans ambiguïté?
- La réponse correcte est-elle vraiment correcte?
- L'explication est-elle compréhensible et instructive?
- La source indiquée correspond-elle au contenu de la question?

### Étape 3: Décider

**Approuver la question**: Cliquez sur **Approuver**. La question passe au statut «Approuvée»
et est immédiatement disponible dans Exam Composer.

**Rejeter la question**: Cliquez sur **Rejeter**. La question est archivée et ne peut plus être utilisée. Vous pouvez également entrer une raison de rejet.

!!! tip "Quand rejeter?"
    Rejetez les questions si: le texte est flou ou ambigu, la réponse correcte est fausse, la question
    ne correspond pas au sujet, ou plusieurs options de réponse pourraient être correctes.

## Vue détaillée des questions individuelles

Chaque question a sa propre URL: `/questions/review/:id`

Vous pouvez partager cette URL pour attirer l'attention d'un collègue sur une question spécifique.

## Étapes suivantes

Les questions approuvées sont immédiatement disponibles dans [Exam Composer](exam-composer.md).
De là, vous pouvez assembler et exporter un examen complet.

- [:octicons-arrow-right-24: Assembler un examen](exam-composer.md)
- [:octicons-arrow-right-24: Générer plus de questions](exam-create.md)
- [:octicons-arrow-right-24: Meilleures pratiques](best-practices.md)
