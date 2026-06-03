# Classes et étudiants

!!! note "Note sur les niveaux"
    Les classes, la statistique d'évolution des étudiants et les évaluations croisées entre examens sont des fonctionnalités Enterprise. Cependant, les étudiants sont automatiquement créés lors de l'import CSV dans tous les niveaux et peuvent être consultés.

Avec les classes, vous regroupez les étudiants et obtenez une vue d'ensemble transversale de leur évolution de performances. Routes : `/auswertungen/klassen`, `/auswertungen/klassen/:classId`, `/auswertungen/studierende`, `/auswertungen/studierende/:studentId`.

![Classes — Vue d'ensemble](../screenshots/klassen/klassen-liste.png)

## Créer une classe

1. Naviguez vers **Évaluations → Classes**
2. Cliquez sur **Créer une classe**
3. Attribuez un nom (p. ex. « Informatique B 2026 »)
4. Optionnel : saisir une description et l'année scolaire
5. **Enregistrer** — la classe est maintenant vide

## Affecter des étudiants

Sélectionnez la classe dans la liste et cliquez sur **Affecter des étudiants**. Dans la boîte de dialogue, vous pouvez ajouter des étudiants individuels par recherche ou reprendre tous les candidats d'un examen importé.

!!! tip "Affectation automatique lors de l'import CSV"
    Si le CSV d'import contient une colonne `class_hint`, les étudiants sont automatiquement affectés à la classe correspondante — sans étape manuelle. Les classes qui n'existent pas encore sont également créées automatiquement.

## Détail de la classe et évolution

![Classes — Détail avec graphiques d'évolution](../screenshots/klassen/klassen-detail.png)

Dans le détail de la classe, vous voyez pour tous les examens passés jusqu'à présent :

| Vue | Contenu |
|-----|---------|
| Graphique d'évolution | Valeur moyenne par examen de façon chronologique |
| Liste des examens | Tous les examens avec date, moyenne et taux de réussite |
| Liste des membres | Tous les étudiants avec leur dernier résultat |

## Vue d'ensemble des étudiants

![Étudiants — Liste des données de base](../screenshots/klassen/studierende-liste.png)

Naviguez vers **Évaluations → Étudiants** pour une vue d'ensemble institutionnelle de tous les candidats avec nom, e-mail, classe(s) et date du dernier examen.

## Détail d'un étudiant

![Étudiants — Détail d'évolution](../screenshots/klassen/studierende-detail.png)

Le détail d'un étudiant montre :

- **Toutes les soumissions** chronologiquement avec le score obtenu et la note
- **Graphique d'évolution** sur tous les examens
- **Mix de taxonomie de Bloom** des questions traitées (si des tags ont été attribués)
- **Carte thermique des forces/faiblesses** par domaine thématique (si des tags ont été attribués)

## Prochaines étapes

- [:octicons-arrow-right-24: Intégration Moodle](moodle-integration.md)
- [:octicons-arrow-right-24: Évaluations](auswertungen.md)
- [:octicons-arrow-right-24: Statistiques](statistik.md)
- [:octicons-arrow-right-24: Quotas d'abonnement](subscription.md)
