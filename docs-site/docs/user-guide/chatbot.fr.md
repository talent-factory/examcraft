# ChatBot Dokument

Le ChatBot permet des conversations interactives avec vos documents téléchargés.

!!! warning "Fonctionnalité Premium"
    Le chat de documents est disponible à partir de l'abonnement **Starter** et nécessite
    la permission `document_chatbot`. Avec l'abonnement Free, cette fonctionnalité n'est pas accessible.
    Voir [Abonnement](subscription.md).

## Sélectionner un document

1. Cliquez sur **ChatBot Dokument** dans la navigation
2. Sélectionnez un document dans le menu déroulant
3. Le ChatBot charge le contexte (2–5 secondes)

## Démarrer le chat

Posez des questions sur votre document:

- "Explique-moi l'algorithme Heapsort"
- "Quelles sont les différences entre Quicksort et Mergesort?"
- "Résume le chapitre 3"

!!! tip "Conseils pour de bonnes questions"
    - Formulé de manière spécifique et claire
    - En relation avec le contenu du document
    - Utilisez les questions de suivi pour une compréhension plus profonde

## Comprendre les réponses

Chaque réponse contient:

- **Texte principal** – Réponse générée par l'IA
- **Sources** – Passages textuels pertinents du document
- **Confiance** – Fiabilité (0–1)

| Confiance | Signification |
|------|------|
| > 0.8 | Très fiable |
| 0.6–0.8 | Fiable |
| < 0.6 | À utiliser avec prudence |

## Historique du chat

- Tous les messages sont sauvegardés au cours de la session
- Le contexte est conservé (Multi-Tour)
- Sélectionnez un autre document pour démarrer une nouvelle conversation

## Limitations

- **Uniquement documents téléchargés** comme source de connaissances — pas d'accès Internet
- **Pas d'accès** aux contenus non téléchargés en tant que document
- **Lié à la session** — l'historique de conversation n'est pas sauvegardé entre les sessions
- Démarrez une nouvelle conversation en sélectionnant un autre document

## Exemples de prompts

Formulez vos questions précisément pour obtenir de meilleures réponses:

| Au lieu de... | Mieux... |
|----------|-----------|
| «Explique le document» | «Résume le chapitre 3 sur les algorithmes de tri en trois points» |
| «Qu'y a-t-il dedans?» | «Quelles sont selon ce document les différences entre Quicksort et Mergesort?» |
| «Comment ça marche?» | «Explique l'algorithme Heapsort étape par étape en utilisant le document» |

!!! tip "Utiliser les questions de suivi"
    Le chat comprend le contexte de la conversation. Utilisez des questions de suivi comme
    «Explique cela plus en détail» ou «Donne-moi un exemple».

## Étapes suivantes

- [:octicons-arrow-right-24: Gérer les documents](documents.md)
- [:octicons-arrow-right-24: Générer des questions à partir de documents](rag-exam.md)
- [:octicons-arrow-right-24: Gérer l'abonnement](subscription.md)
