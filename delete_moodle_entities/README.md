# Configuration

On suit toutes les étapes expliquées ici : 

https://moodle.gymnasedebeaulieu.ch/admin/category.php?category=webservicesettings


## Un rôle spécifique `webservice role`

https://moodle.gymnasedebeaulieu.ch/admin/roles/manage.php

Le rôle webservice doit avoir les capabilités :
* moodle/course:viewhiddencourses pour pouvoir lister les cours cachés et obtenir leur id pour pouvoir les supprimer
* moodle/course:view pour pouvoir supprimer des cours dont l'utilisateur webservice n'est pas membre 
* moodle/cohort:view pour voir les cohortes systèmes
* moodle/cohort:manage pour supprimer les cohortes



## Un utilisateur spécifique `webservice user`

Cet utilisateur doit avoir la méthode d'authentification "comptes manuels"

On est forcé d'assigner une adresse email unique à cet utilisateur technique

Assigner le rôle `webservice role` à cet utilisateur

##  Un service spécifique `admin_api` 

https://moodle.gymnasedebeaulieu.ch/admin/settings.php?section=externalservices

Avec juste les fonctions dont on a besoin: `core_course_delete_courses, core_course_get_categories, core_course_get_courses_by_field, core_cohort_search_cohorts, core_cohort_delete_cohorts`

Avec `webservice user` comme seul utilisateur autorisé

## Technique 

Documentation automatique générée par notre instance
https://moodle.gymnasedebeaulieu.ch/admin/webservice/documentation.php

Quand on se trompe de nom de fonction webservice on obtient une erreur très bas niveau: 

     'exception': 'dml_missing_record_exception', 'errorcode': 'invalidrecord', 
     'message': "Can't find data record in database table external_functions."


# Utilisation

**Note** : Le script supprime les backups de cours (supprimer les cours à la main fait la même chose).

- Générer un jeton pour l'utilisateur `webservice user`. 
  https://moodle.gymnasedebeaulieu.ch/admin/settings.php?section=webservicetokens

- Exporter une variable d'environnement TOKEN avec la valeur de ce jeton. Il est aussi possible de créer un fichier .env avec une ligne TOKEN=_la valeur du jeton_. Ce fichier sera automatiquement lu par le programme au démarrage

- Aller sur la page https://moodle.gymnasedebeaulieu.ch/course/management.php pour trouver l'id de la catégorie à supprimer (le script supprime récursivement tous les cours dans cette catégorie et ses sous-catégories)

- Lancer le script en passant l'id de la catégorie à supprimer en paramètre

- Le script liste les cours qui vont être supprimés. Confirmer la suppression. Le script tourne pendant plus d'une heure et affiche une barre de progression

- Vérifier dans moodle que la catégorie et les sous-catégories ne contiennent plus de cours

- Supprimer manuellement les catégories (choisir supprimer les sous-catégories)


# Journal

En juillet 2023 le script a pris 1h20.

L'utilisation disque est passée de 139GB a 51GB.

