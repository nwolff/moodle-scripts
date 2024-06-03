# Configuration

On suit toutes les étapes expliquées ici :

https://moodle.gymnasedebeaulieu.ch/admin/category.php?category=webservicesettings

## Un rôle spécifique `webservice role`

https://moodle.gymnasedebeaulieu.ch/admin/roles/manage.php

Le rôle webservice doit avoir les capabilités :

- moodle/course:viewhiddencourses pour pouvoir lister les cours cachés et obtenir leur id pour pouvoir les supprimer
- moodle/course:view pour pouvoir supprimer des cours dont l'utilisateur webservice n'est pas membre
- moodle/cohort:view pour voir les cohortes
- moodle/cohort:create pour créer les cohortes
- moodle/cohort:manage pour supprimer les cohortes

## Un utilisateur spécifique `webservice_user`

Cet utilisateur doit avoir la méthode d'authentification "comptes manuels"

On est forcé d'assigner une adresse email unique à cet utilisateur technique

Assigner le rôle `webservice role` à cet utilisateur en utilisant
https://moodle.gymnasedebeaulieu.ch/admin/roles/assign.php?contextid=1

## Un service spécifique `admin_api`

https://moodle.gymnasedebeaulieu.ch/admin/settings.php?section=externalservices

Avec les fonctions dont on a besoin: `core_course_delete_courses, core_course_get_categories, core_course_get_courses_by_field, core_cohort_search_cohorts, core_cohort_create_cohorts, core_cohort_delete_cohorts`

Avec `webservice user` comme seul utilisateur autorisé

## Générer un jeton

Générer un jeton pour l'utilisateur `webservice_user`.
https://moodle.gymnasedebeaulieu.ch/admin/settings.php?section=webservicetokens

- Cliquer sur le bouton "ajouter" en bas à droite
- Chercher l'utilisateur en ordonnant par prénom décroissant pour trouver "webservice" après quelques pages

Exporter une variable d'environnement TOKEN avec la valeur de ce jeton.
Il est aussi possible de créer un fichier .env avec une ligne TOKEN=_la valeur du jeton_. Ce fichier sera automatiquement lu par le programme au démarrage

# Utilisation

## Pour supprimer les cours

**Note** : Le script supprime aussi les backups de cours. Supprimer les cours à la main fait la même chose.

- Aller sur la page https://moodle.gymnasedebeaulieu.ch/course/management.php pour trouver l'id de la catégorie de cours à supprimer (le script supprime récursivement tous les cours dans cette catégorie et ses sous-catégories)

- Lancer le script en passant l'id de la catégorie à supprimer en paramètre

- Le script liste les cours qui vont être supprimés. Confirmer la suppression. Le script tourne pendant plus d'une heure et affiche une barre de progression.
  En juillet 2023 le script a pris 1h20, l'utilisation disque est passée de 139GB a 51GB.

- Vérifier dans Moodle que la catégorie et les sous-catégories ne contiennent plus de cours

- Supprimer manuellement les catégories (choisir supprimer les sous-catégories)

# Technique

## Documentation des webservices

Documentation automatique générée par notre instance
https://moodle.gymnasedebeaulieu.ch/admin/webservice/documentation.php

## Comprendre l'erreur dml_missing_record_exception

Quand on se trompe de nom de fonction webservice on obtient une erreur très bas niveau:

     'exception': 'dml_missing_record_exception', 'errorcode': 'invalidrecord',
     'message': "Can't find data record in database table external_functions."

## Comprendre accessexception

On obtient une **accessexception** si on a soit oublié d'ajouter la _permission_, soit oublié d'ajouter la _fonction_

## Trouver le code source qui traite un appel à une fonction webservice

En utilisant le code source de Moodle sur github:

- En cherchant sa définition . Par exemple : https://github.com/search?q=repo%3Amoodle%2Fmoodle%20core_cohort_create_cohorts&type=code
- Puis en suivant les infos, ici : https://github.com/moodle/moodle/blob/main/cohort/externallib.php#L84

## Obtenir des exceptions plus détaillées

En réglant les messages de déboggage à "Normal":

https://moodle.gymnasedebeaulieu.ch/admin/settings.php?section=debugging

on obtient un champ supplémentaire "debuginfo" dans les exceptions

## Contextes

On passe des contextes un peu partout aux fonctions webservice.
Voici une doc qui aide à comprendre :

https://docs.moodle.org/404/en/Context

On trouve aussi les noms à utiliser dans l'API dans le code source de Moodle : moodle/lib/classes/context/
