# Bibliothèque de prompts

La Bibliothèque de prompts permet la gestion des prompts AI réutilisables pour la génération de questions. Au lieu de taper le même prompt chaque fois, vous sauvegardez les prompts éprouvés de façon centralisée et les utilisez directement lors de la création d'examens.

!!! note "Accès"
    La Bibliothèque de prompts est disponible pour les utilisateurs ayant les rôles **ADMIN** et **PROFESSEUR**.
    Route: `/prompts`

## Aperçu

- **Versioning** – Toutes les modifications sont suivies
- **Rollback** – Revenir aux versions antérieures
- **Recherche sémantique** – Trouver des prompts par signification
- **Analytics** – Superviser les performances et les coûts
- **Système de modèles** – Prompts réutilisables avec variables
- **Interface Web** – Pas de modifications de code nécessaires

## Vue Prompt

La Bibliothèque de prompts affiche tous les prompts disponibles dans une mise en page de grille avec:

- Nom et description du prompt
- Catégorie (Système / Utilisateur / Modèle)
- Cas d'utilisation, version et statut
- Tags et compteurs d'utilisation

### Actions

Vous pouvez gérer chaque prompt avec les actions suivantes:

- **Modifier** – Ouvrir le prompt dans l'éditeur
- **Versions** – Afficher l'historique des versions
- **Supprimer** – Supprimer le prompt

## Créer un nouveau prompt

1. Cliquez sur **Nouveau prompt**
2. Remplissez les champs suivants:

| Champ | Description |
|---|-------|
| Nom | Identifiant unique (p. ex. `system_prompt_question_generation`) |
| Description | Explication brève du but |
| Catégorie | Prompt système / Prompt utilisateur / Exemple peu / Modèle |
| Cas d'utilisation | Objectif d'utilisation (p. ex. `question_generation`) |
| Contenu | Texte du prompt (Markdown supporté) |
| Tags | Mots-clés pour une recherche plus facile |
| Actif | Activer immédiatement? |

3. Cliquez sur **Enregistrer**

Le nouveau prompt est immédiatement disponible dans la bibliothèque et peut être utilisé lors de la génération de questions.

## Variables de modèle

Avec les variables de modèle, vous créez des prompts dynamiques qui s'adaptent automatiquement à vos entrées.

### Syntaxe

Utilisez les accolades: `{variable_name}`

Exemple:
```
Générez {count} questions sur le sujet {topic} au niveau de difficulté {difficulty}
```

### Variables disponibles pour les examens RAG

Les variables suivantes sont automatiquement disponibles:

- `topic` – Sujet de l'examen
- `difficulty` – Niveau de difficulté (easy, medium, hard)
- `language` – Langue des questions
- `context` – Contenus de documents automatiquement extraits

Ces variables sont remplacées à l'exécution par vos entrées ou les données du document.

## Contrôle des versions

La Bibliothèque de prompts gère automatiquement toutes les versions de vos prompts.

### Gestion des versions

- Numérotation des versions automatiques (v1, v2, v3...)
- Une seule version peut être active à la fois
- Les versions anciennes sont conservées (illimitées)

### Revenir à une version antérieure

1. Ouvrez le prompt et cliquez sur **Versions**
2. Sélectionnez la version souhaitée dans la liste
3. Cliquez sur **Activer**
4. Confirmez le rollback

La version plus ancienne est ensuite à nouveau active pour les nouvelles générations de questions.

## Analytics d'utilisation

Supervisez les performances de vos prompts avec des métriques détaillées:

| Métrique | Description |
|----|-------|
| Utilisations | Nombre d'appels depuis la création |
| Taux de succès | % de générations réussies |
| Latence moyenne | Temps de réponse moyen en secondes |
| Jetons totaux | Consommation totale de jetons |

Ces métriques vous aident à évaluer et à optimiser l'efficacité de vos prompts.

## Recherche sémantique

Trouvez des prompts par signification et pas seulement par mots-clés.

### Effectuer une recherche sémantique

1. Allez à l'onglet **Recherche sémantique**
2. Entrez une requête de recherche (p. ex. «Générer des questions à choix multiples»)
3. Filtrez si nécessaire par:
    - **Catégorie** – Affiner le type de prompt
    - **Cas d'utilisation** – Sélectionner un cas d'utilisation spécifique
    - **Seuil de similarité** – Définir la pertinence minimale
4. Les résultats sont automatiquement triés par pertinence

La recherche sémantique comprend le sens de votre requête et trouve également des prompts qui ne correspondent pas exactement textuellement.

## Utiliser un prompt dans la génération de questions

1. Ouvrez [Créer un examen](exam-create.md) ou [Créer un examen RAG](rag-exam.md)
2. Dans la section **Configuration du prompt**, cliquez sur **Sélectionner dans la bibliothèque**
3. Sélectionnez le prompt souhaité dans la liste
4. Les variables de modèle sont automatiquement remplies avec vos entrées
5. Cliquez sur **Générer**

!!! tip "Premium: Prompt Upload"
    À partir de l'abonnement **Professional**, vous pouvez télécharger vos propres fichiers de prompt et
    les importer dans la bibliothèque. Voir [Abonnement](subscription.md).

## Étapes suivantes

- [:octicons-arrow-right-24: Générer des questions](exam-create.md)
- [:octicons-arrow-right-24: Créer un examen RAG](rag-exam.md)
- [:octicons-arrow-right-24: Gérer l'abonnement](subscription.md)
