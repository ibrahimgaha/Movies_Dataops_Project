# Inventaire des données

## Fichiers CSV

- `data/Raw/movies_metadata.csv` — CSV, 34,445,126 octets, 45,466 lignes, 24 colonnes.
  Colonnes : `adult`, `belongs_to_collection`, `budget`, `genres`, `homepage`, `id`, `imdb_id`, `original_language`, `original_title`, `overview`, `popularity`, `poster_path`, `production_companies`, `production_countries`, `release_date`, `revenue`, `runtime`, `spoken_languages`, `status`, `tagline`, `title`, `video`, `vote_average`, `vote_count`.
- `data/Raw/ratings_small.csv` — CSV, 2,438,266 octets, 100,004 lignes, 4 colonnes.
  Colonnes : `userId`, `movieId`, `rating`, `timestamp`.

## Affiches

- `data/images/poster_downloads/` — 8,252 fichiers, 121,008,933 octets.
- Formats détectés : JPEG (8,252).
- Exemples : `1.6_245943.jpg` (14,636 octets), `1.6_56415.jpg` (17,426 octets), `1.9_270846.jpg` (19,112 octets).
- [Liste complète des affiches](poster_inventory.csv) avec le format et la taille de chaque fichier.

## Sources et identifiants

- [The Movies Dataset](https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset) documente les métadonnées TMDB et le sous-ensemble de notes MovieLens. Le nombre et le nom des fichiers locaux concordent avec la collection [Movie Posters](https://www.kaggle.com/datasets/phiitm/movie-posters).
- `movies_metadata.id` est un identifiant TMDB et `imdb_id` est un identifiant IMDb. `ratings_small.movieId` appartient à MovieLens. Un fichier de correspondance serait requis pour joindre les notes aux films.
- Suffixes numériques présents parmi les ID TMDB : 1,191. Ces coïncidences ne suffisent pas à établir une correspondance.
- Suffixes convertis en ID IMDb et présents dans `imdb_id` : 8,193.
- Noms de fichiers présents dans `poster_path` : 0.
