# Institutions

Les institutions organisent les utilisateurs en groupes — par exemple une école, une université ou un département. Chaque utilisateur appartient à exactement une institution.

Allez à `/admin` et sélectionnez l'onglet **Institutions**.

## Créer une institution

1. Cliquez sur **Nouvelle institution**
2. Entrez les informations suivantes:

| Champ | Description | Obligatoire |
|------|-------------|:-----------:|
| Nom | Désignation de l'institution (p. ex. «Lycée de Zurich») | ✓ |
| Description | Information supplémentaire optionnelle | — |

3. Cliquez sur **Créer une institution**

La nouvelle institution s'affiche immédiatement dans la liste et peut être sélectionnée dans la gestion des utilisateurs.

## Assigner des utilisateurs à une institution

Vous pouvez assigner des utilisateurs à une institution de deux façons:

**Lors de la création d'un nouvel utilisateur**: Sélectionnez l'institution directement dans le formulaire de création. Voir [Gestion des utilisateurs](user-mgmt.md).

**Via les détails de l'institution**:

1. Cliquez sur l'institution
2. Allez à l'onglet **Utilisateurs**
3. Cliquez sur **Ajouter un utilisateur**
4. Sélectionnez l'utilisateur dans la liste

## Modifier une institution

1. Cliquez sur le nom dans la liste des institutions
2. Adaptez le nom ou la description
3. Cliquez sur **Enregistrer les modifications**

## Paramètres spécifiques à l'institution

Selon la configuration de votre installation ExamCraft, vous pouvez faire les paramètres spécifiques à l'institution suivants:

- **Abonnement par défaut**: Quel plan est assigné par défaut aux nouveaux utilisateurs de cette institution
- **Méthodes de connexion autorisées**: E-mail/mot de passe et/ou Google OAuth

!!! note "Paramètres dépendant de votre installation"
    Les paramètres disponibles peuvent varier selon votre version d'ExamCraft.
    Contactez votre administrateur informatique si vous avez des questions.

## Supprimer une institution

!!! warning "Attention: Non réversible"
    La suppression d'une institution supprime l'institution et toutes les affectations.
    Les utilisateurs de l'institution ne sont pas supprimés, mais perdent leur affectation institutionnelle.
    Réfléchissez bien à savoir si la suppression est vraiment la bonne mesure — souvent, renommer l'institution suffit.

1. Cliquez sur l'institution
2. Cliquez sur **Supprimer l'institution**
3. Confirmez l'action en entrant le nom de l'institution

## Étapes suivantes

- [:octicons-arrow-right-24: Gérer les utilisateurs](user-mgmt.md)
- [:octicons-arrow-right-24: Aperçu de l'utilisation](monitoring.md)
