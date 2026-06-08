# Configurer la connexion Moodle

!!! warning "Configuration obligatoire pour la production"
    Le token d'accès Moodle est stocké chiffré avec Fernet. Pour la production, la variable d'environnement `MOODLE_TOKEN_ENCRYPTION_KEY` **doit** être définie avec une clé Fernet de 44 caractères. En son absence, l'application revient à un mécanisme par défaut inadapté à la production.

La connexion Moodle permet aux enseignants d'importer directement les résultats d'examens via API sans export CSV manuel. Cette configuration s'effectue une seule fois par institution, par un administrateur.

## Prérequis dans Moodle

1. **Administration du site → Plugins → Services web → Vue d'ensemble**: Activer les services web
2. Activer le protocole REST
3. Créer un service externe et lui assigner les fonctions suivantes:
   - `mod_quiz_get_quizzes_by_courses`
   - `mod_quiz_get_user_attempts`
   - `mod_quiz_get_attempt_review`
   - `core_webservice_get_site_info` (pour le bouton de test)
4. Générer un token pour un utilisateur système disposant des autorisations nécessaires

## Générer la clé de chiffrement

Exécutez la commande suivante sur le serveur et saisissez le résultat comme valeur de `MOODLE_TOKEN_ENCRYPTION_KEY` dans le fichier `.env`:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

La clé fait exactement 44 caractères et doit rester secrète. En cas de perte, tous les tokens enregistrés devront être ressaisis.

## Configurer la connexion

![Moodle — Formulaire de connexion](../screenshots/moodle/moodle-connection-form.png)

1. Accédez en tant qu'admin à `/admin/integrations/moodle`
2. Cliquez sur **Nouvelle connexion**
3. Remplissez les champs:

| Champ | Exemple | Remarque |
|-------|---------|----------|
| Nom | «Moodle Haute école de Berne» | Nom d'affichage pour les enseignants |
| URL de base | `https://moodle.example.ch` | Sans `/` final |
| Token | `abc123...` | Copié depuis Moodle |

4. Cliquez sur **Tester la connexion** — ExamCraft appelle `core_webservice_get_site_info`. En cas de succès, le nom du site Moodle s'affiche en confirmation.
5. **Enregistrer**

## Fonctionnement interne de l'import API

Lors de l'import, la séquence de requêtes suivante est exécutée:

1. `mod_quiz_get_quizzes_by_courses` — lister tous les quiz du cours
2. `mod_quiz_get_user_attempts` — récupérer toutes les tentatives par étudiant
3. `mod_quiz_get_attempt_review` — obtenir les réponses détaillées par tentative

La correspondance des questions s'effectue sur la base des ID de questions Moodle, que les enseignants saisissent une seule fois lors du [Question-ID-Round-Trip](../user-guide/moodle-integration.md).

## Isolation multi-tenant

Chaque institution gère ses propres connexions. Les tokens et données de connexion ne sont pas accessibles d'une institution à l'autre.

## Étapes suivantes

- [:octicons-arrow-right-24: Guide enseignant Moodle](../user-guide/moodle-integration.md)
- [:octicons-arrow-right-24: Schémas de notation](grading-schemes.md)
- [:octicons-arrow-right-24: Rôles et autorisations](roles.md)
