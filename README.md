# Films et affiches · Pipeline DataOps

La Partie A prépare des métadonnées de films et des affiches pour un futur projet multimodal. Une commande DVC valide les données, calcule les caractéristiques RGB et relie les modalités par identifiant IMDb. PostgreSQL reste disponible pour les exercices de la Tâche 2.

## Installation sous PowerShell

Ouvrir PowerShell à la racine du dépôt avec Python 3.14 et Git installés.

```powershell
python -m venv .venv
$env:Path = "$(Join-Path $PWD '.venv/Scripts');$env:Path"
python -m pip install -r requirements.txt
```

Les versions directes sont fixées dans `requirements.txt`. Réexécuter la ligne qui modifie `Path` à l’ouverture d’une nouvelle session PowerShell.

## Récupérer les données

Sur la machine du projet, les données sont déjà dans `data/raw/` et le stockage de démonstration est `.dvc-storage/`. Après réception de la révision Partie A par Git et obtention de l’accès au stockage de données, un autre étudiant peut cloner la version publiée, installer les dépendances puis récupérer les fichiers.

```powershell
git clone --depth 1 --branch task3-partie-a https://github.com/ibrahimgaha/Movies_Dataops_Project.git
Set-Location Movies_Dataops_Project
# Exécuter les commandes d’installation ci-dessus.
dvc remote add --local -d partage '\\serveur\equipe\movies-dvc'
dvc pull
```

Remplacer le chemin UNC par le dossier DVC autorisé de l’équipe. Pour un partage local, on peut aussi copier le dossier de démonstration `.dvc-storage/` à la racine du nouveau clone et exécuter `dvc pull -r demonstration`. Un stockage partagé reçoit les objets par `dvc push -r partage` quand l’équipe dispose des droits de diffusion. Les identifiants du stockage restent dans la configuration locale.

En l’absence de stockage partagé, récupérer les versions exactes des deux CSV et des affiches indiquées dans la [fiche de données](DATA_CARD.md), les placer selon l’arborescence ci-dessous et contrôler leur identité avec `dvc status data/raw.dvc`. Les archives d’origine peuvent avoir un nom ou une structure de dossiers différents.

La révision Partie A et son tag sont locaux en attendant l’autorisation de publication. Le stockage de démonstration est local. Le commit Git initial contient encore les anciennes données dans son historique, tandis que la révision Partie A suit les données brutes et préparées avec DVC. Un clone superficiel du tag, une fois publié, évite de télécharger l’ancien commit.

## Exécuter la préparation

```powershell
$env:DVC_SITE_CACHE_DIR = Join-Path $PWD '.dvc/tmp/site-cache'
dvc repro
dvc status
dvc repro
```

La dernière commande doit indiquer que le pipeline est à jour. Dans `configs/params.yaml`, `images.sample_size: 0` traite toutes les affiches. Une valeur positive tire un échantillon reproductible avec la graine 42. Pour déplacer une entrée ou une sortie, mettre à jour son chemin dans le YAML des paramètres et dans `dvc.yaml`.

| Étape | Entrée | Résultat |
| --- | --- | --- |
| Ingestion CSV | Deux CSV bruts | Copies tabulaires et volumes |
| Validation CSV | Copies tabulaires | Films et notes valides, statistiques et seuils |
| Prétraitement des affiches | Fichiers JPEG | Dimensions originales, dimensions RGB 224 × 224 et moyennes par canal |
| Validation des affiches | Caractéristiques et erreurs de lecture | Affiches valides et liste des rejets |
| Alignement | Films et affiches valides | Identifiants IMDb uniques, état et motif du rapprochement |
| Export | Modalités alignées et journaux | Quatre fichiers dans `data/processed/` |

Le traitement garde les fichiers d’origine. Les anomalies tolérées sont écartées des sorties préparées. Une colonne obligatoire absente, un volume insuffisant ou un seuil dépassé fait échouer DVC. Les fichiers `data/interim/*.json` sont les journaux des étapes et `data/processed/statistics.json` les rassemble avec des distributions.

## Tester et démontrer

```powershell
$pythonFiles = (Get-ChildItem -File -Filter '*.py').Name
python -m ruff check --select E9,F src tests $pythonFiles
python -m pytest -q
python -m tests.demo_pipeline
```

La démonstration crée une copie temporaire avec trois films, deux notes et quatre images. Elle exécute DVC, vérifie que la relance est à jour, change uniquement la largeur des images et vérifie que les étapes CSV sont ignorées. Elle injecte ensuite une note de 9 sur 5, vérifie l’arrêt du pipeline et restaure les entrées valides. Le workflow GitHub Actions reprend ces contrôles sur un jeu synthétique sans PostgreSQL.

## Consulter les sorties

- `movies_multimodal.csv` contient une ligne par film préparé, les caractéristiques de l’affiche retenue et le booléen `has_poster`. Si plusieurs affiches valides correspondent, le premier chemin par ordre alphabétique est retenu.
- `poster_features.csv` conserve toutes les affiches valides et leur statut `matched` ou `unmatched`, avec un motif. Un rapprochement exige un identifiant IMDb non ambigu dans le CSV brut.
- `ratings_prepared.csv` contient les notes MovieLens validées. Leurs identifiants appartiennent à MovieLens et restent distincts des identifiants TMDB.
- `statistics.json` résume les volumes, champs manquants, doublons, rejets, images et liens. Les chemins d’images dans les CSV sont relatifs au dépôt.

## PostgreSQL pour la Tâche 2

Le pipeline DVC utilise les fichiers. Pour reprendre les exercices PostgreSQL, utiliser une base existante et renseigner les valeurs du serveur dans PowerShell. Le schéma, le port par défaut et la taille des blocs sont dans `configs/params.yaml`.

```powershell
$env:PGHOST = 'localhost'
$env:PGPORT = '5432'
$env:PGDATABASE = 'movies_dataops'
$env:PGUSER = 'postgres'
```

Utiliser un fichier `PGPASSFILE` hors du dépôt ou saisir le mot de passe avec la commande suivante, à exécuter seule.

```powershell
$password = Read-Host 'Mot de passe PostgreSQL' -AsSecureString
```

```powershell
$env:PGPASSWORD = [System.Net.NetworkCredential]::new('', $password).Password
python phase2_ingestion.py
python phase3_validation.py
python phase3_cleaning.py
python phase4_process_images.py
python phase5_integration.py
Remove-Item Env:PGPASSWORD
```

Ces scripts restent indépendants de DVC et régénèrent les rapports CSV de la Tâche 2. Leur intégration d’affiches porte sur l’échantillon historique de 100. Pour consulter l’intégralité du nouveau jeu préparé, utiliser les sorties DVC.

## Arborescence

```text
configs/params.yaml
data/
  raw.dvc
  raw/
    movies_metadata.csv
    ratings_small.csv
    posters/
  interim/
  processed/
src/
  settings.py
  csv_schema.py
  csv_ingestion.py
  csv_validation.py
  image_preprocessing.py
  image_validation.py
  alignment.py
  export_dataset.py
  future/README.md
tests/
reports/
.github/workflows/ci.yml
.dvc/config
dvc.yaml
dvc.lock
requirements.txt
DATA_CARD.md
```

Les scripts des phases précédentes restent à la racine et leurs rapports restent dans `reports/`. Le [plan des futures étapes](src/future/README.md) réserve les interfaces d’extraction, de fusion, d’entraînement, d’évaluation et de suivi MLflow. Les découpages train, validation et test seront définis avec la tâche d’apprentissage.
