# Abonnement

Sur la page d'abonnement, vous voyez votre plan actuel, votre utilisation et pouvez gérer votre abonnement. ExamCraft AI offre quatre plans d'abonnement flexibles et évolutifs pour différents besoins.

## Plans disponibles

ExamCraft AI offre quatre plans d'abonnement avec des fonctionnalités croissantes et des limites plus élevées:

| Fonctionnalité | Free | Starter | Professional | Enterprise |
|---------|:----:|:-------:|:------------:|:----------:|
| Documents | 5 | 50 | Illimité | Illimité |
| Questions par mois | 20 | 200 | Illimité | Illimité |
| Types de questions | MC + Ouvert | MC + Ouvert | MC + Ouvert + Appariement | MC + Ouvert + Appariement |
| Chat de documents | — | ✓ | ✓ | ✓ |
| Téléchargement de prompts | — | — | ✓ | ✓ |
| Examens RAG | — | ✓ | ✓ | ✓ |
| Export d'examen | PDF | PDF + Word | PDF + Word + Excel | PDF + Word + Excel + LMS |
| Support | Communauté | E-mail | Priorité | Dédié |
| SLA | — | — | 99,5% | 99,9% |

### Détails des plans

**Free** – Gratuit, pour l'évaluation et les petits projets. Base optimale pour découvrir la plateforme.

**Starter** – EUR 49/mois, pour les enseignants avec utilisation régulière. Inclut les examens RAG et le chat de documents.

**Professional** – EUR 149/mois, pour les institutions à haut volume. Ressources illimitées et gestion des prompts.

**Enterprise** – Sur demande, pour les grandes organisations. Support dédié et SLA personnalisé.

## Consulter votre abonnement actuel

Allez à `/subscription` ou cliquez sur **Abonnement** dans le menu principal. Vous voyez:

- **Votre plan actuel** avec un aperçu complet des fonctionnalités
- **Votre utilisation** (par ex. documents utilisés, questions générées)
- **La date de facturation suivante** et le statut de l'abonnement
- **Le badge d'abonnement** – également visible en haut à gauche du Dashboard

Les métriques d'utilisation sont mises à jour en temps réel et affichent:

| Métrique | Description |
|--------|-------------|
| Documents téléchargés | Nombre de documents actifs vs limite |
| Questions ce mois | Questions générées vs limite mensuelle |
| Espace utilisé | Taille du document vs disponible |
| Requêtes RAG | Recherches effectuées dans cette facturation |

## Mettre à niveau le plan

Vous pouvez à tout moment passer à un plan supérieur. Le nouveau plan est activé immédiatement.

### Effectuer une mise à niveau d'abonnement

1. Allez à `/subscription`
2. Cliquez sur **Mettre à niveau** ou sélectionnez le plan souhaité
3. Vous êtes redirigé vers le paiement Stripe
4. Entrez vos informations de paiement:
    - Carte de crédit (VISA, Mastercard, American Express)
    - Prélèvement SEPA
5. Après le paiement réussi, votre plan est activé immédiatement

La facturation se fait le même jour du mois suivant. Pour les plans mensuels, vous payez tous les 30 jours, pour les plans annuels avec réduction.

!!! tip "Abonnement annuel"
    Avec un abonnement annuel, vous économisez jusqu'à 20% par rapport à la
    facturation mensuelle. L'économie exacte est affichée lors du paiement. Les abonnements
    annuels sont facturés une seule fois.

!!! note "Frais de mise à niveau"
    Lors d'une mise à niveau d'un plan mensuel, la nouvelle prime du plan vous est facturée
    au prorata pour les jours restants. Vous ne payez pas deux fois.

## Factures et détails de paiement

Gérez votre mode de paiement et téléchargez les factures.

### Ouvrir le portail de paiement

1. Cliquez sur **Ouvrir le portail Stripe** ou **Gérer les factures**
2. Vous êtes redirigé vers un tableau de bord client sécurisé
3. Vous pouvez:
    - **Télécharger les factures passées** – Fichiers PDF pour votre comptabilité
    - **Modifier le mode de paiement** – Ajouter/mettre à jour une carte de crédit ou SEPA
    - **Modifier l'adresse de facturation** – Pour des factures correctes
    - **Annuler l'abonnement** – Si souhaité

Les factures contiennent toutes les informations nécessaires pour votre comptabilité et votre numéro de TVA, s'il est enregistré.

### Mettre à jour le mode de paiement

1. Ouvrez le portail de paiement
2. Cliquez sur **Mode de paiement**
3. Sélectionnez **Ajouter une nouvelle carte** ou **Modifier existante**
4. Entrez les données ou sélectionnez une méthode enregistrée
5. Enregistrez les modifications

Vos données de paiement sont gérées de manière chiffrée via Stripe et enregistrées de manière sécurisée.

## Changer de plan ou passer à un plan inférieur

Vous pouvez à tout moment passer à un plan inférieur ou annuler votre abonnement.

### Que se passe-t-il en cas de passage à un plan inférieur?

Lorsque vous passez d'un plan supérieur à un plan inférieur, votre compte est immédiatement limité au nouveau plan:

- **Vos données restent intactes** – Tous les documents, questions et examens sont toujours accessibles
- **Les nouvelles fonctionnalités sont désactivées** – Les fonctionnalités premium de l'ancien niveau ne fonctionnent plus
- **Les limites s'appliquent immédiatement** – Si vous avez dépassé la limite de documents, vous ne pouvez pas télécharger de nouveaux documents jusqu'à ce que vous en supprimiez certains

### Que se passe-t-il à l'expiration?

Si vous annulez ou que votre abonnement expire:

- **Votre compte est rétrogradé en Free** – Automatiquement après le dernier jour payé
- **Vos données sont conservées pendant 90 jours** – Vous pouvez toujours les consulter et exporter
- **Après 90 jours, les données sont supprimées** – Si vous ne réabonnez pas
- **Vous pouvez à tout moment réabonner** – Vos données seront restaurées si vous revenez dans les 90 jours

!!! note "Les données restent intactes"
    Lors du passage à un plan inférieur, vos données ne sont pas supprimées.
    Vous pouvez les utiliser complètement à nouveau après une mise à niveau ultérieure.
    Si vous avez besoin d'une sauvegarde, exportez d'abord tous les examens.

## Comprendre les quotas et les limites

Chaque plan a des limites spécifiques pour le stockage, les requêtes et les fonctionnalités.

### Limites par plan

**Plan Free:**
- 5 documents téléchargeables
- 20 questions par mois
- Pas de chat de documents
- Pas d'examens RAG

**Plan Starter:**
- 50 documents téléchargeables
- 200 questions par mois
- Requêtes RAG illimitées
- Chat de documents avec jusqu'à 100 paires de messages par mois

**Plans Professional et Enterprise:**
- Documents et questions illimitées
- Gamme complète de toutes les fonctionnalités

### Que se passe-t-il en cas de dépassement de limite?

Lorsque vous atteignez vos limites:

1. **Limite de documents** – Vous ne pouvez plus télécharger de nouveaux documents
2. **Limite de questions** – La génération de questions est désactivée jusqu'à la facturation suivante
3. **Limite RAG** – La recherche sémantique ne fonctionne plus

Vous pouvez mettre à niveau immédiatement pour augmenter les limites.

## Étapes suivantes

- [:octicons-arrow-right-24: Retour au Dashboard](dashboard.md)
- [:octicons-arrow-right-24: Profil et compte](profile.md)
- [:octicons-arrow-right-24: Télécharger des documents](documents.md)
