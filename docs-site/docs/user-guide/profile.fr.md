# Profil et paramètres de compte

Sur la page de profil, vous pouvez adapter vos données personnelles et modifier votre mot de passe. Tous les changements sont sauvegardés immédiatement et visibles dans toute l'application.

## Ouvrir le profil

Cliquez sur votre nom ou votre avatar en haut à droite et sélectionnez **Profil** dans le menu déroulant. Vous pouvez également naviguer directement vers `/profile`.

La page de profil est divisée en plusieurs sections: Données personnelles, Sécurité et Aperçu du compte.

## Modifier les données personnelles

La section **Données personnelles** contient tous les informations de base de votre compte.

### Adapter le nom

1. Cliquez sur l'icône Modifier à côté de votre nom dans la section **Données personnelles**
2. Entrez le nouveau nom
3. Cliquez sur **Enregistrer**

Le changement est immédiat et s'affiche dans la navigation et dans tous les documents générés. Votre nom sera également visible pour les autres administrateurs si vous collaborez avec eux dans votre espace.

### Modifier l'adresse e-mail

1. Cliquez sur l'icône Modifier à côté de votre adresse e-mail
2. Entrez la nouvelle adresse e-mail
3. Cliquez sur **Enregistrer**
4. Vous recevrez immédiatement un e-mail de confirmation à la nouvelle adresse
5. Confirmez le lien dans l'e-mail pour activer le changement

Tant que vous ne cliquez pas sur le lien de confirmation, la nouvelle adresse e-mail n'est pas complètement activée. Votre ancienne adresse e-mail reste valide jusqu'à ce que vous confirmiez la nouvelle.

!!! warning "E-mail avec Google OAuth"
    Si vous vous connectez via Google OAuth, votre adresse e-mail est gérée par Google.
    Vous ne pouvez pas la modifier directement dans ExamCraft AI. Modifiez-la plutôt dans
    votre compte Google sur [https://myaccount.google.com](https://myaccount.google.com).

!!! warning "E-mail avec Microsoft OAuth"
    Tout comme avec Google, les adresses e-mail des connexions Microsoft OAuth
    sont gérées par Microsoft. Les modifications doivent être faites dans votre compte Microsoft.

## Modifier le mot de passe

Dans la section **Sécurité**, vous pouvez modifier votre mot de passe à tout moment. C'est recommandé si vous soupçonnez que votre mot de passe a été compromis.

### Mettre à jour le mot de passe

1. Cliquez sur **Modifier le mot de passe** dans la section **Sécurité**
2. Entrez votre mot de passe actuel
3. Entrez le nouveau mot de passe
4. Le nouveau mot de passe doit satisfaire aux exigences suivantes:
    - Au minimum 8 caractères long
    - Au minimum une lettre majuscule (A-Z)
    - Au minimum une lettre minuscule (a-z)
    - Au minimum un chiffre (0-9)
5. Répétez le nouveau mot de passe pour confirmation
6. Cliquez sur **Enregistrer le mot de passe**

Après le changement, vous devez vous connecter avec le nouveau mot de passe la prochaine fois. Toutes les sessions actives dans d'autres navigateurs ou appareils sont automatiquement terminées.

!!! note "Mot de passe avec Google OAuth"
    Lors de la connexion via Google OAuth, il n'y a pas d'option de mot de passe dans ExamCraft AI.
    Votre mot de passe est entièrement géré par votre compte Google. Vous pouvez le modifier
    dans les [paramètres du compte Google](https://myaccount.google.com).

!!! note "Mot de passe avec Microsoft OAuth"
    Tout comme avec Google, le mot de passe des connexions Microsoft OAuth
    est géré par votre compte Microsoft.

## Aperçu du compte

Dans la section **Compte**, vous voyez un résumé des détails de votre compte:

| Information | Description |
|-------------|-------------|
| Rôle | Votre rôle utilisateur (ADMIN ou PROFESSEUR) – détermine vos permissions |
| Institution | L'institution à laquelle vous êtes assigné |
| Abonnement | Votre plan d'abonnement actuel et les limites |
| Membre depuis | Date et heure de création du compte |

Ces informations sont en lecture seule et ne peuvent être modifiées que par un administrateur pour votre compte. Si vous devez modifier votre rôle, institution ou plan d'abonnement, contactez votre administrateur.

### Comprendre le rôle

Le rôle détermine les fonctionnalités que vous pouvez utiliser:

- **ADMIN** – Accès complet à toutes les fonctionnalités, gestion des utilisateurs, paramètres institutionnels
- **PROFESSEUR** – Accès à la génération de questions, gestion des prompts, examens RAG

### Institution

Votre institution vous est assignée par votre administrateur. Tous vos documents et examens sont associés à cette institution.

## Meilleures pratiques de sécurité

Pour garder votre compte sécurisé, respectez ces recommandations:

1. **Utiliser un mot de passe fort** – Utilisez au moins 8 caractères avec des majuscules, minuscules, chiffres et caractères spéciaux
2. **Modifier régulièrement le mot de passe** – Modifiez votre mot de passe au moins tous les 90 jours
3. **Connexion sécurisée** – Utilisez ExamCraft AI uniquement via des connexions HTTPS sécurisées
4. **Se déconnecter après utilisation** – Déconnectez-vous lorsque vous utilisez un ordinateur tiers
5. **Authentification à deux facteurs** – Si disponible, activez des mesures de sécurité supplémentaires

## Étapes suivantes

- [:octicons-arrow-right-24: Gérer l'abonnement](subscription.md)
- [:octicons-arrow-right-24: Vers le Dashboard](dashboard.md)
- [:octicons-arrow-right-24: Générer des questions](exam-create.md)
