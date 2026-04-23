# Meilleures pratiques

## Téléchargement de documents

### Préparation optimale

1. Structurez les documents avec des titres clairs
2. Utilisez un formatage cohérent
3. Ajoutez des métadonnées (titre, auteur, date)
4. Évitez les filigranes et les images de fond

### Téléchargement par lots

Téléchargez les documents connexes ensemble (par ex. tous les chapitres d'un manuel). Cela facilite les futurs examens RAG.

## Création de questions

### Formulation du sujet

- Spécifique plutôt que général
- Donner du contexte
- Garder le niveau de Bloom à l'esprit

!!! example "Exemples"
    **Bon:**

    - "Python Listes – Méthodes append(), extend(), insert()"
    - "Algorithmes – Complexité temporelle des procédures de tri"

    **Mauvais:**

    - "Python" (trop large)
    - "Programmation" (trop général)

### Contrôle de qualité

- Vérifiez toujours les questions générées
- Prêtez attention aux indices de confiance
- Adaptez le niveau de difficulté
- Utilisez les références pour la vérification

## Examens RAG

- Sélectionnez 3–5 documents pertinents (optimal)
- Spécifiez un domaine précis
- Trop de documents conduisent à une qualité inférieure

## Utilisation du ChatBot

Commencez par des questions générales et approfondissez progressivement:

```text
Utilisateur: "Qu'est-ce que Heapsort?"
Bot: [Explique Heapsort]

Utilisateur: "Comment cela diffère-t-il de Quicksort?"
Bot: [Compare les deux algorithmes]

Utilisateur: "Lequel est plus efficace pour les grandes quantités de données?"
Bot: [Analyse la complexité]
```

## Utiliser efficacement la Review Queue

- Révisez les questions peu de temps après la génération — le contexte est plus frais
- Utilisez les options de filtrage (statut, difficulté, type de question) pour garder la Queue claire
- **Rejeter est mieux que d'accepter les mauvaises questions**: La qualité avant la quantité
- Si beaucoup de questions sont rejetées: Ajustez le prompt, améliorez le document source ou précisez le sujet
- N'approuvez que les questions que vous poseriez vous-même

## Exam Composer

- Planifiez la structure de l'examen avant de sélectionner les questions: Combien de questions? Quels types? Quelle distribution de difficulté?
- Mélangez les types de questions (Choix multiples + questions ouvertes) pour des examens variés
- Exportez une version test et lisez-la complètement avant de créer la version finale
- Vérifiez la numérotation automatique et le formatage dans le document exporté
