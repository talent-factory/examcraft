# Rôles et autorisations

ExamCraft AI utilise un système d'autorisations basé sur les rôles (RBAC). Chaque utilisateur se voit attribuer un rôle qui détermine les fonctionnalités auxquelles il a accès.

Accédez à `/admin` et sélectionnez l'onglet **Rôles** pour consulter les attributions de rôles de votre institution.

![Admin Rôles et autorisations](../screenshots/admin/admin-roles.png)

## Rôles disponibles

ExamCraft AI connaît deux rôles:

| Rôle | Description |
|------|------------|
| **ENSEIGNANT** | Rôle standard pour les enseignants — accès à toutes les fonctions d'enseignement |
| **ADMIN** | Rôle étendu pour les administrateurs d'institution — accès supplémentaire au panneau d'administration |

## Aperçu des autorisations

| Fonction | ENSEIGNANT | ADMIN |
|----------|:------:|:-----:|
| Télécharger et gérer des documents | ✓ | ✓ |
| Générer des examens IA | ✓ | ✓ |
| Générer des examens RAG | ✓ | ✓ |
| Utiliser la Review Queue | ✓ | ✓ |
| Utiliser Exam Composer | ✓ | ✓ |
| Utiliser la bibliothèque de prompts | ✓ | ✓ |
| Modifier son propre profil | ✓ | ✓ |
| **Gestion des utilisateurs** | — | ✓ |
| **Gérer les institutions** | — | ✓ |
| **Consulter les statistiques d'utilisation** | — | ✓ |
| **Attribuer des rôles** | — | ✓ |
| **Gérer les abonnements et quotas** | — | ✓ |
| Consulter les évaluations (`submissions:read`) | ✓ | ✓ |
| Importer des submissions (`submissions:import`) | ✓ | ✓ |
| Noter des submissions (`submissions:grade`) | ✓ | ✓ |
| Gérer les étudiants (`students:manage`) | — | ✓ |
| Configurer la connexion Moodle (`moodle:configure`) | — | ✓ |
| Gérer les schémas de notation (`grading_schemes:manage`) | — | ✓ (Enterprise) |
| Gérer les unités organisationnelles (`manage_org_units`) | — | ✓ |

## Attribuer ou modifier un rôle

L'attribution des rôles s'effectue dans la [gestion des utilisateurs](user-mgmt.md):

1. Accédez à `/admin` → onglet **Utilisateurs**
2. Ouvrez l'utilisateur souhaité
3. Sélectionnez la nouvelle valeur dans le champ **Rôle** (`ENSEIGNANT` ou `ADMIN`)
4. Cliquez sur **Enregistrer les modifications**

Le nouveau rôle prend effet immédiatement — l'utilisateur voit l'interface mise à jour dès le prochain chargement de page.

!!! warning "Attribuer le rôle ADMIN avec parcimonie"
    N'accordez le rôle ADMIN qu'aux personnes qui doivent effectivement gérer les utilisateurs et les paramètres de l'institution. Un trop grand nombre d'administrateurs augmente le risque de modifications de configuration non intentionnelles.

## Tiers d'abonnement et autorisations

Le rôle (ENSEIGNANT / ADMIN) contrôle **qui** peut accéder à quelles fonctions. Le [tier d'abonnement](subscription.md) (Free, Starter, Professional, Enterprise) contrôle en outre **combien** un utilisateur peut utiliser — par exemple le nombre de documents ou de questions générables par mois.

Les deux mécanismes fonctionnent indépendamment l'un de l'autre: un ADMIN avec le tier Free a accès au panneau d'administration, mais les mêmes limites d'utilisation qu'un ENSEIGNANT avec le tier Free.

## Note de mise à jour v1.4 — Nouvelles permissions

!!! warning "Attribution automatique au rôle Reviewer"
    Avec la mise à jour v1.4, le rôle Reviewer reçoit automatiquement la permission `submissions:grade`. Ceux qui souhaitent séparer la notation (Grading) de la simple activité de révision doivent définir **avant la mise à jour** un rôle personnalisé sans cette permission.

    La permission `grading_schemes:manage` n'est **pas** attribuée automatiquement — elle est exclusivement réservée aux rôles Admin et Institution Owner dans le tier Enterprise.

### Mapping des rôles par défaut (à partir de v1.4)

| Rôle | Nouvelles permissions |
|------|-----------------------|
| ENSEIGNANT | `submissions:read`, `submissions:import`, `submissions:grade` |
| ADMIN | Toutes les précédentes + `students:manage`, `moodle:configure` |
| Institution Owner | En plus `grading_schemes:manage` (Enterprise) |

## Note de mise à jour v1.8 — Nouvelle permission

!!! info "Unités organisationnelles"
    Avec la v1.8, la permission `manage_org_units` a été introduite. Elle est attribuée par défaut au rôle système ADMIN et contrôle la création, le déplacement, la suppression et la consultation de la liste complète des unités organisationnelles (départements/équipes) dans le panneau d'administration. Sans cette permission, l'onglet reste invisible ; chaque utilisateur continue de voir ses propres appartenances.

    Une unité organisationnelle peut en outre accorder automatiquement un rôle à ses membres directs et contrôler qui peut voir les ressources en visibilité d'équipe. Voir [Unités organisationnelles](org-units.md) pour plus de détails.

### Mapping des rôles par défaut (à partir de v1.8)

| Rôle | Nouvelles permissions |
|------|-----------------------|
| ADMIN | `manage_org_units` |
| ENSEIGNANT | — |

## Étapes suivantes

- [:octicons-arrow-right-24: Gérer les utilisateurs](user-mgmt.md)
- [:octicons-arrow-right-24: Gérer les unités organisationnelles](org-units.md)
- [:octicons-arrow-right-24: Abonnement et quotas](subscription.md)
- [:octicons-arrow-right-24: Gérer les institutions](institutions.md)
