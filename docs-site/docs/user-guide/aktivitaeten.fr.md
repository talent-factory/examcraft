# Activités

!!! note "Toutes les activités en un coup d'œil"
    La page Activités affiche tous les événements de votre institution en ordre chronologique — avec pagination, filtres par puces et un commutateur entre ses propres activités et toutes les activités.

Route : `/aktivitaeten`

## Vue d'ensemble des activités

![Activités — Vue d'ensemble](../screenshots/aktivitaeten/aktivitaeten-overview.png)

La page liste toutes les activités avec horodatage, type, description et utilisateur ayant effectué l'action. Par défaut, seules ses propres activités sont visibles.

### Commutateur : Les miennes / Toutes

Avec le commutateur **Les miennes / Toutes** en haut à droite, vous basculez entre :

| Mode | Activités visibles |
|------|--------------------|
| **Les miennes** | Uniquement vos propres actions (par défaut) |
| **Toutes** | Toutes les activités de l'institution (nécessite l'autorisation correspondante) |

Le widget du tableau de bord affiche toujours uniquement ses propres activités — la page Activités est le seul endroit pour la vue institutionnelle.

## Filtres par puces

![Activités — Filtres](../screenshots/aktivitaeten/aktivitaeten-filter.png)

Sept filtres par puces restreignent la vue par type d'activité :

| Filtre | Événements inclus |
|--------|-------------------|
| **Documents** | Upload, traitement, suppression de documents |
| **Examens** | Création, modification, archivage d'examens |
| **Questions** | Génération, révision, modifications de questions |
| **Évaluations** | Import CSV, évaluation LLM, clôture de révision |
| **Export** | Export de notes (CSV, CSV Moodle, PDF) |
| **Classes** | Création de classes, affectation de membres |
| **Utilisateurs** | Connexion, déconnexion, modifications de profil |

Plusieurs filtres peuvent être actifs simultanément. Un clic sur une puce active la désactive.

## Pagination

La liste des activités est divisée en pages. Sélectionnez la taille de page via le menu déroulant en bas à droite :

- **25** entrées par page (par défaut)
- **50** entrées par page
- **100** entrées par page

Utilisez les flèches Précédent/Suivant pour naviguer entre les pages.

## État vide

Si aucune activité ne correspond aux filtres actifs, un état vide apparaît avec un message sur les filtres actifs et un bouton **Réinitialiser les filtres**.

## Qu'est-ce qui compte comme activité ?

Les activités sont enregistrées côté serveur — chaque action qui modifie des données ou consomme une ressource importante génère une entrée. Les opérations de lecture seule (p. ex. ouvrir un document, consulter un examen) n'apparaissent pas dans la liste.

## Note sur la protection des données

En mode **Les miennes**, vous voyez exclusivement vos propres activités. Le mode **Toutes** affiche les noms et les actions de tous les utilisateurs de l'institution — utilisez cette vue de manière responsable.

## Prochaines étapes

- [:octicons-arrow-right-24: Tableau de bord](dashboard.md)
- [:octicons-arrow-right-24: Évaluations](auswertungen.md)
- [:octicons-arrow-right-24: Quotas d'abonnement](subscription.md)
