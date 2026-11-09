# Étapes réservées aux prochaines tâches

| Étape | Entrée prévue | Sortie prévue |
| --- | --- | --- |
| Extraction de caractéristiques | Métadonnées préparées et chemins des affiches | Représentations par film et indicateur de modalité disponible |
| Fusion multimodale | Représentations alignées | Représentation multimodale |
| Entraînement | Données préparées et découpages par film | Modèle et paramètres |
| Évaluation | Modèle et ensemble de test séparé | Mesures de performance |
| Suivi MLflow | Paramètres, version DVC et résultats | Historique des expériences |

Ces étapes pourront être déclarées après `export` dans `dvc.yaml`. Le test de découpage vérifiera qu’un identifiant de film est présent dans un seul ensemble.
