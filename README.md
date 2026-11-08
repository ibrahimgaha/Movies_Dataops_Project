# Projet DataOps sur les films

Le pipeline part de deux CSV et d’une collection d’affiches JPEG. Il charge les valeurs brutes dans PostgreSQL, contrôle leur qualité, extrait trois moyennes de couleur par affiche et rattache les affiches aux films grâce aux identifiants IMDb.

## Relancer sous PowerShell

Depuis le dossier du projet, exécuter les commandes ci-dessous. Elles utilisent l’instance PostgreSQL locale créée pour le projet. Le fichier d’authentification est conservé dans le profil Windows, hors du dossier du projet.

```powershell
python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Installation des bibliothèques interrompue.' }

$instance = Join-Path $env:LOCALAPPDATA 'MovieDataOps-01a1bcdc'
pg_ctl -D "$instance/pgdata" status
if ($LASTEXITCODE -ne 0) {
    pg_ctl -D "$instance/pgdata" -l "$instance/postgresql.log" -o "-h 127.0.0.1 -p 55432" -w start
    if ($LASTEXITCODE -ne 0) { throw 'Démarrage de PostgreSQL interrompu.' }
}
$env:PGHOST = '127.0.0.1'
$env:PGPORT = '55432'
$env:PGUSER = 'dataops'
$env:PGDATABASE = 'movies_dataops'
$env:PGPASSFILE = Join-Path $instance 'pgpass.conf'
Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue

foreach ($script in 'phase1_inventory.py', 'phase2_ingestion.py', 'phase3_validation.py',
                    'phase3_cleaning.py', 'phase4_process_images.py', 'phase5_integration.py') {
    python $script
    if ($LASTEXITCODE -ne 0) { throw "Échec de $script" }
}
```

Sur une autre machine, utiliser une base PostgreSQL déjà créée et un compte autorisé à y créer le schéma `movie_dataops`. Adapter `PGHOST`, `PGPORT`, `PGUSER`, `PGDATABASE` et `PGPASSFILE` ou fournir `PGPASSWORD` dans la session PowerShell, puis exécuter les mêmes scripts.

## Nettoyer les données après la validation

Exécuter `python phase3_cleaning.py` après `python phase3_validation.py`, dans la même session PowerShell. Le nettoyage crée `movie_dataops.movies_metadata_clean` et `movie_dataops.ratings_small_clean` et conserve les tables brutes.

Le script écarte les lignes contenant une valeur vide dans une colonne contrôlée en phase 3. Il conserve une seule ligne par identifiant TMDB puis par identifiant IMDb, et une seule note par paire utilisateur-film. Les copies déjà présentes sont conservées lors d’une relance.

## Lire les résultats

| Phase | Opération | Résultat vérifié |
| --- | --- | --- |
| 1 | Recenser les fichiers CSV et identifier le format des affiches. | 2 CSV et 8 252 JPEG. |
| 2 | Copier les CSV par blocs de 10 000 lignes vers PostgreSQL. | 45 466 métadonnées et 100 004 notes. |
| 3 | Comparer les volumes et contrôler les valeurs en lecture seule. | 15 PASS, 8 WARN et 0 FAIL. |
| 4 | Convertir 100 affiches en RGB, les redimensionner à 224 × 224 et calculer les moyennes. | 100 lignes exportées et 0 image illisible dans l’échantillon. |
| 5 | Insérer les caractéristiques et rapprocher les identifiants IMDb. | 99 affiches liées et 1 non liée sur 100. |

La phase 2 conserve les tables déjà chargées. Pour importer une autre version des CSV, exécuter la phase 2 dans une nouvelle base dédiée. La phase 5 conserve une seule ligne par chemin d’image. Elle laisse `movie_id` à `NULL` si le rapprochement est absent ou ambigu. Les rapports Word documentent l’exécution vérifiée et les scripts régénèrent les inventaires et les CSV de résultats.

Pour vérifier les volumes directement dans PostgreSQL, exécuter les requêtes suivantes avec les mêmes variables d’environnement.

```powershell
@'
SELECT COUNT(*) FROM movie_dataops.movies_metadata;
SELECT COUNT(*) FROM movie_dataops.ratings_small;
SELECT match_status, COUNT(*)
FROM movie_dataops.movie_posters
GROUP BY match_status
ORDER BY match_status;
'@ | psql -w -v ON_ERROR_STOP=1
```

## Structure du projet

```text
Movies_DB/
├── README.md
├── requirements.txt
├── phase1_inventory.py
├── phase2_ingestion.py
├── phase3_validation.py
├── phase3_cleaning.py
├── phase4_process_images.py
├── phase5_integration.py
├── load_data.py                  ancien point d’entrée de la phase 2
├── validate_Data.py              ancien point d’entrée de la phase 3
├── data/
│   ├── Raw/
│   │   ├── movies_metadata.csv
│   │   └── ratings_small.csv
│   └── images/
│       └── poster_downloads/     8 252 fichiers JPG
└── reports/
    ├── dataset_inventory.md
    ├── poster_inventory.csv
    ├── phase3_quality_report.csv
    ├── poster_features.csv
    ├── Phase1_Data_Collection.docx
    ├── Phase2_Data_Ingestion.docx
    ├── Phase3_Data_Quality.docx
    ├── Phase4_Image_Processing.docx
    ├── Phase5_Data_Integration.docx
    └── legacy/                  rapports de validation précédents
```
