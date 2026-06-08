# Intégration Moodle

!!! note "Prérequis pour l'import API"
    Pour l'import API, un administrateur doit d'abord configurer une connexion Moodle sous `/admin/integrations/moodle`. L'import CSV fonctionne sans ce prérequis sur tous les niveaux. Détails : [Configurer Moodle (Guide Admin)](../admin-guide/moodle.md).

Les résultats d'examens peuvent être importés de deux façons : en tant que fichier CSV (tous les niveaux) ou directement via l'API du service web Moodle (Professional et Enterprise). L'import API récupère les données en un clic — sans export manuel depuis Moodle.

## Import CSV vs. Import API

| Propriété | Import CSV | Import API |
|-----------|-----------|-----------|
| Disponibilité | Tous les niveaux | Professional / Enterprise |
| Configuration | Aucune | L'admin configure la connexion une seule fois |
| Actualité | Instantané lors de l'export | État actuel depuis Moodle |
| Association des questions | Mappage manuel des colonnes | Automatique via les IDs de questions Moodle |

## Effectuer un import API

![Import API — Sélection de la source](../screenshots/moodle/moodle-import-api.png)

1. Ouvrez **Importer les résultats** pour l'examen souhaité
2. Sélectionnez **API Moodle** comme source
3. Sélectionnez le cours Moodle et le quiz dans la liste
4. Cliquez sur **Récupérer les résultats**

L'association entre les questions Moodle et les questions ExamCraft s'effectue automatiquement via les IDs de questions Moodle enregistrés. Si aucun ID n'est enregistré, la fenêtre de mappage manuel des colonnes s'ouvre.

## Enregistrer les IDs de questions Moodle (Round-Trip des ID de questions)

Pour activer l'association automatique lors de l'import API, les IDs de questions Moodle doivent être saisis une fois dans ExamCraft :

![Synchroniser les IDs Moodle](../screenshots/moodle/moodle-sync-question-ids.png)

1. Ouvrez l'examen dans le [Compositeur d'examen](exam-composer.md)
2. Cliquez sur **Synchroniser les IDs Moodle**
3. La boîte de dialogue affiche vos questions ExamCraft à côté des correspondances Moodle
4. Confirmez l'association — les IDs sont enregistrés de manière permanente

Après cette étape, l'import API s'exécute entièrement de façon automatique sans mappage manuel — même après de nouveaux exports depuis Moodle.

## Limites de quota

| Niveau | Méthode d'import | Examens/mois | Max. soumissions |
|--------|-----------------|--------------|-----------------|
| Free | CSV uniquement | 3 | 30 |
| Starter | CSV uniquement | Illimité | 50 |
| Professional | CSV + API | Illimité | Illimité |
| Enterprise | CSV + API + Bulk | Illimité | Illimité |

## Prochaines étapes

- [:octicons-arrow-right-24: Admin : Configurer la connexion Moodle](../admin-guide/moodle.md)
- [:octicons-arrow-right-24: Évaluations](auswertungen.md)
- [:octicons-arrow-right-24: Classes et étudiants](klassen.md)
- [:octicons-arrow-right-24: Quotas d'abonnement](subscription.md)
