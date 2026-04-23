# Exam Composer

Exam Composer permet d'assembler des questions approuvées en un examen complet et de l'exporter dans différents formats.

!!! note "Prérequis"
    Exam Composer ne contient que des questions approuvées dans la [Review Queue](review-queue.md). Générez d'abord des questions et vérifiez-les avant d'assembler un examen.

## Créer un nouvel examen

### Étape 1: Ouvrir Exam Composer

Cliquez sur **Exam Composer** dans la navigation ou sélectionnez la tuile correspondante sur le [Dashboard](dashboard.md). Route: `/exams/compose`.

### Étape 2: Démarrer un nouvel examen

Cliquez sur **Créer un nouvel examen** et remplissez les champs suivants:

| Champ | Description |
|------|-------------|
| Titre | Désignation de l'examen (p. ex. «Algorithmes — Examen du semestre 2026») |
| Description | Informations supplémentaires optionnelles sur l'examen |
| Date | Date prévue de l'examen |

Le titre est l'élément clé qui identifie uniquement votre examen. Choisissez une désignation explicite qui indique clairement la matière, le cours et la période. La description fournit un contexte supplémentaire pour vous et vos collègues — par exemple des informations sur le niveau de difficulté, le groupe cible ou les domaines d'emphasis spéciaux.

### Étape 3: Sélectionner les questions

Sélectionnez des questions dans la liste des questions approuvées:

- Cliquez sur **+ Ajouter** à côté de chaque question souhaitée
- Utilisez les filtres pour trouver directement des questions par **type de question**, **difficulté** ou **document source**
- Le nombre total de questions sélectionnées s'affiche en haut

!!! tip "Assembler un examen équilibré"
    Assurez-vous d'avoir un bon mélange: différents types de questions (Choix multiples et questions ouvertes), différents niveaux de difficulté et si possible différents domaines thématiques. Un examen équilibré favorise une évaluation équitable et une véritable compréhension du contenu.

Les fonctions de filtrage vous aident à trouver efficacement les questions appropriées. Utilisez systématiquement les options de filtrage: Commencez par le type de question souhaité (par ex. uniquement les questions à choix multiples pour les tests rapides ou un mélange de MC et de questions ouvertes pour les examens plus complets). Ensuite, filtrez par difficulté pour obtenir une distribution équilibrée. Enfin, vous pouvez filtrer de manière ciblée par documents sources si vous voulez tester certains chapitres ou domaines thématiques en particulier.

### Étape 4: Définir l'ordre

Arrangez les questions sélectionnées par glisser-déposer dans l'ordre souhaité. Les questions sont numérotées automatiquement. Réfléchissez à la question de savoir si vous voulez commencer par des questions plus faciles pour introduire les examinés au sujet, ou si vous voulez volontairement placer en avant les questions plus difficiles. L'ordre peut aussi avoir du sens thématiquement — groupez les questions connexes pour permettre aux examinés de comprendre les connexions.

### Étape 5: Exporter l'examen

Cliquez sur **Exporter** et sélectionnez le format souhaité:

| Format | Description |
|--------|-------------|
| Markdown (.md) | Format texte, idéal pour une édition ultérieure ou la publication. Les solutions peuvent être incluses en option. |
| JSON (.json) | Format lisible par machine pour un traitement supplémentaire, l'intégration avec des systèmes externes ou l'analyse de données |
| Moodle XML (.xml) | Format directement importable dans le système de gestion de l'apprentissage Moodle |

!!! tip "Inclure les solutions"
    Lors de l'export au format Markdown, vous pouvez inclure les solutions en option. Activez la case **Inclure les solutions** dans la boîte de dialogue d'export — pratique pour créer des feuilles de réponses ou pour une révision interne.

Le format Markdown convient pour une édition ultérieure ou l'intégration dans des systèmes de documentation. Le format JSON est idéal pour l'intégration technique — par exemple, si vous voulez importer des données d'examen dans un système personnalisé ou effectuer des analyses automatisées. Le format Moodle XML permet l'import direct dans Moodle sans post-traitement manuel.

## Gérer les examens existants

Tous les examens créés apparaissent dans une liste de présentation. Vous pouvez:

- **Ouvrir**: Modifier et compléter l'examen
- **Dupliquer**: Utiliser comme base pour un nouvel examen similaire
- **Exporter**: Exporter à nouveau dans n'importe quel format
- **Supprimer**: Supprimer l'examen (non réversible)

La liste de présentation affiche des métadonnées importantes telles que la date de création, le nombre de questions et l'horodatage de la dernière modification. Utilisez la fonction de duplication pour créer rapidement des examens similaires — par ex. pour différentes classes de la même année ou pour un examen de rattrapage. Cette fonction économise du temps lors de l'assemblage d'examens similaires et minimise les erreurs.

!!! warning "Examens supprimés"
    La suppression d'un examen supprime uniquement l'assemblage de l'examen, pas les questions individuelles. Les questions restent dans la Review Queue et peuvent être réutilisées pour les futurs examens.

## Étapes suivantes

- [:octicons-arrow-right-24: Générer plus de questions](exam-create.md)
- [:octicons-arrow-right-24: Examen RAG à partir de documents](rag-exam.md)
- [:octicons-arrow-right-24: Review Queue — Vérifier les questions](review-queue.md)
- [:octicons-arrow-right-24: Meilleures pratiques](best-practices.md)
