# Créer des examens AI

Générez des questions d'examen sur n'importe quel sujet — sans documents téléchargés.

## Configuration

### 1. Entrer le sujet de l'examen

Entrez un sujet spécifique:

!!! tip "Bonne formulation du sujet"
    - "Programmation Python – Listes et Dictionnaires"
    - "Structures de données – Algorithme Heapsort"

!!! warning "À éviter"
    - "Informatique" (trop général)
    - "Programmer" (trop large)

### 2. Choisir le niveau de difficulté

| Niveau | Description | Taxonomie de Bloom |
|----|-------|---------|
| Facile | Compréhension fondamentale | Remember, Understand |
| Moyen | Application et analyse | Apply, Analyze |
| Difficile | Évaluation et création | Evaluate, Create |

### 3. Définir le nombre de questions

- Minimum: 1 question
- Maximum: 20 questions
- Recommandé: 5–10 questions par cycle

### 4. Sélectionner les types de questions

- **Choix multiples** – 4 options de réponse, 1 correcte
- **Questions ouvertes** – Réponses en texte libre

### 5. Choisir la langue

- **Deutsch** – Questions et réponses en allemand
- **English** – Questions and answers in English

## Démarrer la génération

1. Cliquez sur **Générer l'examen**
2. Attendez 10–30 secondes
3. Indicateur de progression: «Génération de l'examen...»

## Résultat

Chaque question générée contient:

- Numéro et texte de la question
- Options de réponse (pour choix multiples)
- Réponse correcte (marquée en vert)
- Explication/justification
- Niveau de Bloom
- Niveau de difficulté (1–5)

## Après la génération

Les questions générées apparaissent automatiquement dans la **[Review Queue](review-queue.md)**.

Là, vous pouvez:
- Vérifier chaque question individuellement
- Approuver les questions (elles sont libérées pour Exam Composer) ou les rejeter
- Après vérification, assembler un examen complet dans **[Exam Composer](exam-composer.md)**

!!! tip "Conseil: D'abord réviser, puis assembler"
    Prenez du temps pour la Review Queue. Les questions bien vérifiées
    rendent Exam Composer plus efficace.

## Questions fréquentes sur les examens AI

**Comment les examens AI diffèrent-ils des examens basés sur RAG?**

Les examens AI sont générés sur n'importe quel sujet sans qu'il soit nécessaire de télécharger des documents. Les examens RAG utilisent vos matériels de cours téléchargés comme source. Choisissez les examens AI pour les thèmes généraux, les examens RAG pour les contenus directement inclus dans vos documents.

**Quel niveau de difficulté est optimal?**

Cela dépend du niveau de votre groupe d'apprentissage. Pour les débutants: Facile. Pour les avancés: Moyen à Difficile. Un mélange est également possible — générez plusieurs ensembles avec différents niveaux de difficulté et combinez-les plus tard dans Exam Composer.

**Puis-je modifier les questions générées après?**

Oui! Dans la Review Queue, vous pouvez vérifier chaque question. Avant de l'approuver, vous pouvez ajuster le texte de la question ou les options de réponse. L'édition se fait directement dans la Queue.

**Combien de temps prend la génération?**

Généralement 10–30 secondes pour 5–10 questions, selon le sujet, le niveau de difficulté et la charge du serveur. L'indicateur de progression vous informe en temps réel.

**Puis-je générer plus de 20 questions?**

Le nombre maximum par cycle est 20 questions. Pour plus de questions: Lancez plusieurs générations successives. Les nouvelles questions sont ajoutées à la Review Queue existante.

## Conseils pour de meilleurs résultats

- **Sujets spécifiques**: Plus la formulation est spécifique, meilleure est la qualité. «Python Listes et Dictionnaires» est meilleur que simplement «Python».
- **Niveaux de difficulté appropriés**: Choisissez des niveaux de difficulté qui correspondent au niveau d'apprentissage de vos apprenants.
- **Révision régulière**: Vérifiez les questions rapidement pour assurer la qualité. Plus vite vous donnez des retours, mieux l'IA s'adapte.
- **Obtenir de la variété**: Générez plusieurs cycles avec différents niveaux de difficulté et types de questions.
