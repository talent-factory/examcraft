# Évaluations

!!! note "Prérequis"
    Pour évaluer les résultats d'examens, vous avez besoin d'un examen finalisé dans le [Compositeur d'examen](exam-composer.md). Les résultats sont exportés en tant que fichier CSV depuis votre plateforme d'apprentissage (p. ex. Moodle) et importés ici.

Le pipeline d'évaluation mène de la soumission à la liste de notes en cinq étapes : **Import → Évaluation automatique → Révision des questions ouvertes → Statistiques → Export des notes**. Route : `/auswertungen`.

![Évaluations — Vue d'ensemble](../screenshots/auswertungen/auswertungen-overview.png)

## Démarrer le pipeline d'évaluation

Naviguez vers **Évaluations** dans la navigation principale. Le tableau liste tous vos examens. Cliquez sur **Importer les résultats** pour l'examen souhaité.

## Importer les résultats d'examen

La boîte de dialogue d'import vous guide à travers l'import CSV en deux étapes.

### Étape 1 : Télécharger le fichier CSV

![Boîte de dialogue d'import — Sélectionner la source](../screenshots/auswertungen/auswertungen-import-dialog.png)

Sélectionnez **Fichier CSV** comme source et téléchargez le fichier d'export de votre plateforme d'apprentissage. Les exports Moodle (locales DE et EN) sont reconnus directement. Pour l'import direct via l'API Moodle, consultez la section [Intégration Moodle](moodle-integration.md).

### Étape 2 : Vérifier le mappage des colonnes

![Import — Aperçu du mappage](../screenshots/auswertungen/auswertungen-import-preview.png)

Le système assigne automatiquement les colonnes CSV aux questions de votre examen. Vérifiez le mappage :

| Colonne | Signification |
|---------|---------------|
| Étudiants | Nom ou e-mail du candidat |
| Colonnes de questions | Réponse par question — affectation basée sur l'ID de question Moodle ou la position de la colonne |
| Points totaux | Calculé à partir des évaluations individuelles, non repris de la colonne CSV |

Des avertissements apparaissent si une question ne peut pas être associée. Vous pouvez néanmoins finaliser l'import — les questions non associées seront ignorées.

!!! note "Import idempotent"
    Un second import du même fichier CSV ne crée pas de doublons. Les soumissions déjà importées sont mises à jour, les manquantes sont créées.

Cliquez sur **Importer** pour terminer l'opération.

## Vue d'ensemble des soumissions

![Soumissions — Liste](../screenshots/auswertungen/auswertungen-submissions-tab.png)

Après l'import, toutes les soumissions apparaissent dans l'onglet **Soumissions**. La liste affiche :

| Colonne | Description |
|---------|-------------|
| Étudiants | Nom et e-mail |
| Points | Points obtenus / points maximaux possibles |
| Pourcentage | Part en pourcentage |
| Statut | Statut d'évaluation (voir ci-dessous) |

### Badges de statut

| Badge | Signification |
|-------|---------------|
| `pending_review` | Des questions ouvertes attendent encore une révision |
| `partially_reviewed` | Certaines questions ouvertes sont révisées, d'autres pas encore |
| `fully_reviewed` | Toutes les questions ouvertes évaluées — export des notes possible |

## Détail d'une soumission

![Détail de soumission — Tiroir](../screenshots/auswertungen/auswertungen-submission-drawer.png)

Cliquez sur une ligne pour ouvrir le tiroir de détails. Il affiche toutes les réponses avec le texte de la question, le type de réponse (QCM, Vrai/Faux, Ouverte), la réponse soumise, le statut d'évaluation et les points obtenus. Pour les questions ouvertes : suggestion IA avec badge de confiance.

## Prochaines étapes

- [:octicons-arrow-right-24: Réviser les questions ouvertes](review-grading.md)
- [:octicons-arrow-right-24: Consulter les statistiques](statistik.md)
- [:octicons-arrow-right-24: Exporter les notes](notenexport.md)
- [:octicons-arrow-right-24: Intégration Moodle](moodle-integration.md)
- [:octicons-arrow-right-24: Quotas d'abonnement](subscription.md)
