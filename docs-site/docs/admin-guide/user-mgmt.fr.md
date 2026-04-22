# Gestion des utilisateurs

En tant qu'administrateur, vous gérez tous les utilisateurs de votre institution via le panneau Admin. Allez à `/admin` et sélectionnez l'onglet **Utilisateurs**.

## Créer des utilisateurs

1. Cliquez sur **Nouvel utilisateur**
2. Remplissez le formulaire:

| Champ | Description | Obligatoire |
|------|-------------|:-----------:|
| Prénom et Nom | Nom complet de la personne | ✓ |
| Adresse e-mail | Utilisé comme nom de connexion | ✓ |
| Rôle | ADMIN ou PROFESSEUR (voir ci-dessous) | ✓ |
| Institution | Affectation à l'institution | ✓ |
| Mot de passe temporaire | Premier mot de passe (l'utilisateur peut le modifier) | ✓ |

3. Cliquez sur **Créer un utilisateur**
4. Le nouvel utilisateur reçoit un e-mail de bienvenue avec les identifiants de connexion

!!! tip "Recommander Google OAuth"
    Recommandez aux nouveaux utilisateurs de passer à Google OAuth lors de la première connexion.
    Cela simplifie la gestion des mots de passe et augmente la sécurité.

## Rôles utilisateur

ExamCraft AI a deux rôles:

| Rôle | Permissions |
|-------|---------------|
| **PROFESSEUR** | Télécharger des documents, générer des questions, Review Queue, Exam Composer, Bibliothèque de prompts |
| **ADMIN** | Toutes les permissions PROFESSEUR + gestion des utilisateurs, institutions, panneau Admin |

N'accordez le rôle ADMIN que aux personnes qui doivent réellement gérer les utilisateurs.

## Modifier les utilisateurs

1. Cliquez sur le nom de la personne dans la liste des utilisateurs
2. Adaptez les champs souhaités (nom, e-mail, rôle, institution)
3. Cliquez sur **Enregistrer les modifications**

## Réinitialiser le mot de passe (en tant qu'administrateur)

1. Ouvrez l'utilisateur dans la gestion
2. Cliquez sur **Réinitialiser le mot de passe**
3. Un nouveau mot de passe temporaire est généré et envoyé par e-mail à l'utilisateur
4. L'utilisateur est invité à modifier le mot de passe lors de la prochaine connexion

## Désactiver les utilisateurs

Si un utilisateur quitte l'institution ou n'a plus besoin d'accès:

1. Ouvrez l'utilisateur
2. Cliquez sur **Désactiver l'utilisateur**
3. Confirmez l'action

!!! warning "Désactiver plutôt que de supprimer"
    Désactivez les utilisateurs au lieu de les supprimer. Cela préserve tous les
    questions et examens créés et restent attribuables. Un utilisateur désactivé
    ne peut plus se connecter, mais ses données sont conservées.

## Assigner les utilisateurs à une institution

Vous pouvez modifier l'affectation institutionnelle à tout moment:

1. Ouvrez l'utilisateur
2. Sélectionnez la nouvelle institution dans le champ **Institution**
3. Enregistrez le changement

Pour plus d'informations sur les institutions: [Gérer les institutions](institutions.md)

## Étapes suivantes

- [:octicons-arrow-right-24: Gérer les institutions](institutions.md)
- [:octicons-arrow-right-24: Aperçu de l'utilisation](monitoring.md)
