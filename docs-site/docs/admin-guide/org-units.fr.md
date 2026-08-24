# Unités organisationnelles

!!! note "Nouvelle autorisation requise"
    La création, le déplacement, la suppression et la consultation de la liste complète des unités organisationnelles nécessitent la permission `manage_org_units`, attribuée par défaut au rôle ADMIN. Sans cette permission, l'onglet **Unités organisationnelles** n'est pas visible — chaque utilisateur connecté ne voit que ses propres appartenances, par exemple lors du choix d'une visibilité d'équipe.

ExamCraft AI représente la structure interne d'une institution via des unités organisationnelles — des **départements** avec des **équipes** imbriquées en dessous. Accédez à `/admin` et sélectionnez l'onglet **Unités organisationnelles**.

## Créer une unité organisationnelle

1. Accédez à `/admin` → onglet **Unités organisationnelles**
2. Cliquez sur **+ Créer**
3. Indiquez un **nom** et choisissez le **type** (`Département` ou `Équipe`)
4. Sélectionnez éventuellement une **unité parente** — une équipe se situe généralement sous un département
5. Attribuez éventuellement un **rôle accordé** (voir ci-dessous)
6. **Enregistrer**

!!! warning "Type fixe après création"
    Le type (`Département`/`Équipe`) ne peut plus être modifié après la création de l'unité.

    Le nom doit également être unique au sein du même niveau — deux unités portant le même nom et ayant la même unité parente ne sont pas autorisées.

## Déplacer une unité organisationnelle

Ouvrez l'unité via l'icône de modification et sélectionnez une nouvelle unité parente dans le champ **Unité parente**. Une unité ne peut pas être déplacée sous l'une de ses propres sous-unités.

## Supprimer une unité organisationnelle

Si une unité organisationnelle possède des sous-unités, sa suppression entraîne également la suppression définitive de **toutes** les sous-unités. La boîte de dialogue de confirmation indique le nombre de sous-unités concernées.

Si des documents, prompts, questions, examens ou référentiels de compétences en visibilité d'équipe référencent encore l'unité ou l'une de ses sous-unités, la suppression est refusée — retirez ou réattribuez d'abord les ressources concernées.

## Rôle accordé et visibilité d'équipe

La structure organisationnelle n'est pas purement informative — elle peut contrôler deux choses :

- **Rôle accordé** : si un rôle est attribué à une unité organisationnelle, tous les membres **directs** de cette unité reçoivent automatiquement les permissions de ce rôle — en plus de leur propre rôle. Cet héritage ne se propage pas en cascade aux sous-unités.
- **Visibilité d'équipe** : pour les documents, prompts, questions, examens et référentiels de compétences dont la visibilité est réglée sur « Équipe », l'appartenance à l'unité organisationnelle — y compris la hiérarchie — détermine qui peut les voir.

Attribuez des utilisateurs aux unités organisationnelles via le bouton **Unités org.** dans la [gestion des utilisateurs](user-mgmt.md).

## Étapes suivantes

- [:octicons-arrow-right-24: Rôles et autorisations](roles.md)
- [:octicons-arrow-right-24: Gérer les utilisateurs](user-mgmt.md)
