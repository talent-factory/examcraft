# Exporter des examens

L'export d'examens vous permet d'utiliser les questions générées et vérifiées dans différents formats ou de les importer dans des systèmes externes.

## Options d'export actuelles

### Copie manuelle (actuellement disponible)

Les questions générées peuvent être copiées directement depuis la Review Queue ou Exam Composer:

1. **Depuis la Review Queue**:
   - Sélectionnez les questions approuvées
   - Cliquez sur «Copier»
   - Collez dans Word, Google Docs, ou un éditeur de texte

2. **Depuis Exam Composer**:
   - Cliquez sur l'examen terminé
   - Utilisez la fonction de navigateur «Enregistrer la page» (Ctrl+S / Cmd+S)
   - Enregistrez en tant que fichier HTML pour édition ultérieure

### Fonction d'impression du navigateur

La meilleure option actuelle pour l'export PDF:

1. Ouvrez l'examen dans Exam Composer
2. Appuyez sur `Ctrl+P` (Windows) ou `Cmd+P` (Mac)
3. Sélectionnez «Enregistrer en tant que PDF»
4. Configurez la mise en page, les marges et autres options
5. Enregistrez le fichier PDF

Cette méthode est gratuite et fonctionne dans tous les navigateurs.

## Formats d'export prévus (Feuille de route)

Les fonctions d'export suivantes sont prévues pour les futures versions:

### Export PDF (Q2/Q3 2026)

**Export PDF automatique avec formatage**

- Examen prêt à imprimer avec mise en page professionnelle
- Page de titre automatique avec métadonnées (cours, date, enseignant)
- Mise en page configurable (A4/Lettre)
- Optionnel: Feuille de réponses avec clé et explications
- Numéros de page et en-têtes
- Police et formatage professionnels

**Exemple d'utilisation:**
```
Examen: Algorithmes de tri
Cours: Informatique 2 (Hiver 2025)
Date: 15.01.2026
Enseignant: Dr. Müller
```

### Export JSON (Q2/Q3 2026)

**Format lisible par machine pour intégration**

```json
{
  "exam": {
    "title": "Algorithmes de tri",
    "created": "2026-01-15",
    "questions": [
      {
        "id": "q1",
        "text": "Quelle est la complexité temporelle de...",
        "type": "multiple_choice",
        "options": ["A) O(n)", "B) O(n log n)", "C) O(n²)"],
        "correct_answer": "B",
        "explanation": "Quicksort a...",
        "difficulty": 3,
        "bloom_level": "Apply",
        "source_documents": ["Script_Chapitre_5.pdf"]
      }
    ]
  }
}
```

**Cas d'utilisation:**
- Intégration dans des systèmes de test personnalisés
- Téléchargement en masse dans d'autres plateformes LMS
- Traitement automatisé des données
- Workflows basés sur les API

### Export Moodle XML (Q3/Q4 2026)

**Import direct dans Moodle LMS**

- Compatible avec Moodle 4.0+
- Conversion automatique au format de questions Moodle
- Support pour choix multiples, réponse courte, essai
- Catégorisation et étiquetage
- Niveau de difficulté et points repris

**Workflow:**
```
ExamCraft → Export Moodle XML → Moodle Question Bank → Examen
```

### Export Microsoft Word (Q3 2026)

**Format d'export pour édition basée sur Word**

- Format `.docx` avec modèle professionnel
- Formatage modifiable
- Tableau de réponses optionnel et champ d'édition
- Compatible avec MS Office et LibreOffice

### Export Google Forms (Q4 2026)

**Import automatique dans Google Forms**

- Crée un nouveau formulaire avec toutes les questions
- Vérification automatique des réponses
- Partage et collaboration possibles
- Évaluation et statistiques intégrées

## Comparer les options d'export

| Format | Disponible | Sélection | Formatage | Intégration | Édition |
|--------|-----------|---------|-------------|-------------|------------|
| Copie manuelle | ✅ Maintenant | Individuel | Minimal | Non | Facile |
| PDF navigateur | ✅ Maintenant | Tous | Bon | Non | Non |
| **Export PDF** | Q2/Q3 2026 | Tous | Professionnel | Non | Non |
| **JSON** | Q2/Q3 2026 | Tous | Aucun | Oui | Oui |
| **Moodle XML** | Q3/Q4 2026 | Tous | Automatique | Oui (Moodle) | Oui |
| **Word** | Q3 2026 | Tous | Modifiable | Partielle | Oui |
| **Google Forms** | Q4 2026 | Tous | Automatique | Oui (Google) | Oui |

## Meilleures pratiques pour l'export

1. **Vérifier avant d'exporter**: Assurez-vous que toutes les questions sont approuvées dans la Review Queue
2. **Noter les métadonnées**: Documentez le cours, la date et l'enseignant
3. **Créer une sauvegarde**: Conservez une copie dans ExamCraft au cas où vous voudriez l'ajuster plus tard
4. **Choisir le format**: Utilisez le format qui convient le mieux à votre flux de travail
5. **Tester avant utilisation**: Vérifiez l'examen exporté avant de le donner aux apprenants

## Questions fréquentes sur l'export

**Puis-je exporter un examen partiellement?**

Avec la copie manuelle ou l'export PDF du navigateur, vous pouvez sélectionner des questions individuellement. Les formats prévus supporteront également les options de sélection.

**Les références sources sont-elles réexportées?**

Oui! Les documents sources (numéros de page) sont exportés avec Moodle XML, JSON et PDF.

**Mon contenu exporté est-il protégé?**

L'export est une copie. Après l'export, d'autres peuvent modifier et partager librement le fichier. Utilisez la protection du système d'exploitation si nécessaire (p. ex. mot de passe PDF).

**Puis-je mettre à jour les examens déjà exportés?**

Non, mais vous pouvez régénérer les questions dans Exam Composer et exporter à nouveau. L'ancienne version est remplacée par la nouvelle.
