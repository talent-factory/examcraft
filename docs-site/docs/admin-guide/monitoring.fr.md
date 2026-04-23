# Aperçu de l'utilisation

L'aperçu de l'utilisation dans le panneau Admin vous donne un aperçu des activités et de la consommation de ressources de votre institution.

Allez à `/admin` et sélectionnez l'onglet **Utilisation**.

## Métriques disponibles

| Métrique | Description |
|--------|-------------|
| Utilisateurs actifs | Nombre d'utilisateurs ayant au moins une activité au cours de la période sélectionnée |
| Questions générées | Nombre total de questions créées par l'IA |
| Questions validées | Nombre de questions approuvées dans la Review Queue |
| Documents téléchargés | Nombre et taille totale des documents traités |
| Appels API | Nombre de demandes à l'API Claude (pertinent pour le contrôle des coûts) |

## Sélectionner une période

Filtrez l'affichage selon la période:

- **Aujourd'hui** — Activités du jour courant
- **Cette semaine** — Semaine courante (lundi à aujourd'hui)
- **Ce mois** — Mois calendaire courant
- **Personnalisé** — Choisir une période personnalisée via le sélecteur de date

## Utilisation par utilisateur

Dans la vue détaillée, vous voyez la ventilation par utilisateur:

| Colonne | Description |
|--------|-------------|
| Utilisateur | Nom et e-mail |
| Questions générées | Nombre au cours de la période sélectionnée |
| Documents | Nombre de documents téléchargés |
| Dernière activité | Date de la dernière action |

Cliquez sur une ligne du tableau pour voir les détails d'un utilisateur individuel.

## Surveiller les contingents d'abonnement

Prêtez une attention particulière à l'utilisation des contingents:

!!! warning "Observer les limites de contingent"
    Avec les abonnements Free et Starter, il y a des limites mensuelles pour les questions et les documents.
    Si les utilisateurs atteignent régulièrement les limites, vous devriez envisager une mise à niveau.
    Voir [Abonnement](../user-guide/subscription.md).

## Remarque: Monitoring technique de l'infrastructure

L'aperçu de l'utilisation dans le panneau Admin montre les **métriques d'application** (qui utilise quoi). Pour le **monitoring technique de l'infrastructure** (charge du serveur, logs, taux d'erreur), contactez votre administrateur informatique ou responsable DevOps — ces informations ne font pas partie du panneau Admin.

## Questions fréquentes sur l'aperçu de l'utilisation

**À quelle fréquence les chiffres sont-ils mis à jour?**

Les métriques sont mises à jour en temps réel. Après chaque action (génération de questions, téléchargement de documents, révision), les métriques sont mises à jour en quelques secondes.

**Puis-je exporter les données?**

Actuellement, aucune exportation de données directe du panneau Admin n'est possible. Vous pouvez cependant faire une capture d'écran de l'aperçu de l'utilisation dans le navigateur ou documenter manuellement les chiffres. Un export CSV/PDF est prévu pour les futures versions.

**Que signifie «Appels API»?**

Chaque génération de questions AI compte comme un ou plusieurs appels API à l'API Claude. Par exemple, si vous générez 10 questions, cela peut être 1–3 appels API (selon la taille du batch). Cette information est pertinente pour le contrôle des coûts avec les plans Professional et Enterprise, car vous devez gérer votre budget API.

**Y a-t-il une différence dans les appels API entre les examens AI et RAG?**

Les examens RAG peuvent nécessiter plus d'appels API car l'IA effectue d'abord la recherche sémantique puis génère les questions. Les examens AI sont généralement plus rapides. La différence exacte est mesurée dans la métrique d'appel API.

**Puis-je voir les utilisateurs ayant une utilisation élevée?**

Oui! Dans la vue détaillée «Utilisation par utilisateur», vous pouvez voir quels utilisateurs ont généré combien de questions et combien de documents ils utilisent. Cela aide à identifier les utilisateurs puissants et à planifier les ressources.

## Étapes suivantes

- [:octicons-arrow-right-24: Gérer les utilisateurs](user-mgmt.md)
- [:octicons-arrow-right-24: Gérer les institutions](institutions.md)
