# Révision et évaluation

!!! note "Uniquement pour les questions ouvertes"
    Les questions à choix multiples et les questions Vrai/Faux sont évaluées de manière déterministe — aucune révision n'est nécessaire. Cette section concerne exclusivement les questions ouvertes avec des suggestions IA.

La file d'attente de révision affiche toutes les suggestions d'évaluation IA pour les questions ouvertes, triées par confiance croissante — les cas les plus incertains en premier. Route : onglet **Révision** dans `/auswertungen/:examId/submissions`.

![File de révision — Vue d'ensemble](../screenshots/review-grading/review-queue-overview.png)

## Comment fonctionne l'évaluation IA

Pour chaque question ouverte, l'IA analyse la réponse par rapport à la solution modèle et attribue des points (0 jusqu'au maximum), un niveau de confiance (0–100 %) ainsi qu'une liste des aspects satisfaits et manquants. Une confiance de 0 % indique que l'évaluation IA a échoué — le cas doit être évalué manuellement.

## Filtres

| Filtre | Options |
|--------|---------|
| Question | Uniquement les soumissions pour une question spécifique |
| Étudiants | Uniquement les soumissions d'une personne spécifique |
| Confiance | Plage de–à, p. ex. 0–50 % pour les cas incertains |

![File d'examen — Filtres](../screenshots/review-grading/review-queue-filter.png)

## Carte d'évaluation

![Révision — Carte individuelle](../screenshots/review-grading/review-queue-card.png)

Chaque carte affiche :

| Élément | Description |
|---------|-------------|
| Question | Texte de la question |
| Solution modèle | Réponse attendue |
| Réponse soumise | Ce que le candidat a répondu |
| Suggestion IA | Points + badge de confiance (vert ≥ 80 %, jaune 50–79 %, rouge < 50 %) |
| Aspects correspondants | Aspects satisfaits de la solution modèle (puces vertes) |
| Aspects manquants | Aspects manquants (puces rouges) |

### Actions par carte

| Action | Comportement |
|--------|--------------|
| **Accepter** | La suggestion IA est enregistrée comme évaluation finale |
| **Ajuster** | Un éditeur inline s'ouvre — saisir les points et une note optionnelle |
| **Ouvrir dans le contexte** | Ouvrir la soumission complète dans le tiroir |

![Remplacement — Éditeur inline](../screenshots/review-grading/review-queue-override.png)

## Approbation groupée

![Approbation groupée — Boîte de dialogue](../screenshots/review-grading/review-queue-bulk.png)

Cliquez sur **Tout accepter** ou sélectionnez plusieurs cartes via la case à cocher et utilisez **Accepter la sélection**. Dans la boîte de dialogue, un seuil de confiance peut être défini — seules les suggestions atteignant ce seuil sont acceptées, les cas incertains restent pour examen manuel.

## Remplacement manuel pour QCM et Vrai/Faux

Les réponses à choix multiples et Vrai/Faux évaluées automatiquement peuvent également être remplacées. Ouvrez le tiroir de détails de la soumission et cliquez sur **Remplacer** pour la question souhaitée. Saisissez le nouveau score et une justification optionnelle.

## Piste d'audit

Chaque modification d'évaluation — acceptation, ajustement, remplacement — est enregistrée avec un horodatage et l'utilisateur. Les journaux sont consultables par les administrateurs dans les logs du backend.

## Prochaines étapes

- [:octicons-arrow-right-24: Retour à la liste des soumissions](auswertungen.md)
- [:octicons-arrow-right-24: Afficher les statistiques](statistik.md)
- [:octicons-arrow-right-24: Exporter les notes](notenexport.md)
