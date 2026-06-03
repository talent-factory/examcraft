# Schémas de notation

!!! note "Fonctionnalité Enterprise"
    La création de schémas de notation personnalisés requiert la permission `grading_schemes:manage`, attribuée par défaut aux rôles Admin et Institution Owner dans le tier Enterprise.

ExamCraft AI contient huit schémas système préinstallés (en lecture seule) et permet aux institutions de définir leurs propres schémas. Route: `/admin/grading-schemes`.

## Schémas système vs. schémas institution

| Type | Origine | Modifiable? |
|------|---------|------------|
| Schéma système | ExamCraft AI (préinstallé) | Non |
| Schéma institution | Créé par vous | Oui — modifiable et supprimable |

Les schémas système couvrent les systèmes de notation nationaux les plus courants (Swiss, German, Austrian, French, Dutch, ECTS, Pourcentage, Réussite/Échec). Les schémas personnalisés étendent cette liste.

## Types de configuration

### `linear`

Conversion linéaire du pourcentage en note entre `min_score` et `max_score`.

```yaml
type: linear
min_score: 1.0
max_score: 6.0
passing_percentage: 60
```

### `linear_segments`

Deux segments linéaires avec un point d'inflexion à `passing_percentage`. Les notes en dessous du seuil de réussite évoluent moins vite qu'au-dessus.

```yaml
type: linear_segments
min_score: 1.0
max_score: 6.0
passing_percentage: 60
passing_score: 4.0
```

### `stepped`

Notes par paliers fixes. Chaque palier définit une plage de pourcentage et la note correspondante.

```yaml
type: stepped
steps:
  - { min_percent: 0,  max_percent: 49,  grade: "F" }
  - { min_percent: 50, max_percent: 64,  grade: "D" }
  - { min_percent: 65, max_percent: 79,  grade: "C" }
  - { min_percent: 80, max_percent: 89,  grade: "B" }
  - { min_percent: 90, max_percent: 100, grade: "A" }
```

## Créer un schéma personnalisé

1. Accédez à `/admin/grading-schemes`
2. Cliquez sur **Nouveau schéma**
3. Choisissez le type de configuration
4. Remplissez les paramètres
5. L'**aperçu en direct** montre immédiatement quelle note est attribuée pour quel pourcentage
6. **Enregistrer** — le schéma est alors disponible pour les enseignants lors de l'export des notes

## Définir le standard de l'institution

Cliquez sur l'icône étoile à côté d'un schéma pour le définir comme standard de votre institution. Cette valeur apparaît présélectionnée lors de l'export des notes. Les enseignants peuvent modifier ce choix pour chaque export.

## Étapes suivantes

- [:octicons-arrow-right-24: Connexion Moodle](moodle.md)
- [:octicons-arrow-right-24: Rôles et autorisations](roles.md)
- [:octicons-arrow-right-24: Export des notes (guide utilisateur)](../user-guide/notenexport.md)
