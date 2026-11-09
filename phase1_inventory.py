from collections import Counter
import csv
from pathlib import Path
import re

import pandas as pd
from PIL import Image

from src.settings import ROOT, path_for

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}


def poster_paths():
    folder = path_for("posters")
    return sorted(
        path for path in folder.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def poster_imdb_id(filename):
    # La collection locale utilise le format note_identifiant.jpg.
    parts = re.fullmatch(r"[0-9]+(?:\.[0-9]+)?_([0-9]{1,10})", Path(filename).stem)
    return "tt" + parts[1].zfill(7) if parts else None


def main():
    lines = ["# Inventaire des données", "", "## Fichiers CSV", ""]
    for path in (path_for("movies"), path_for("ratings")):
        data = pd.read_csv(path, dtype=str, keep_default_na=False)
        lines.extend([
            f"- `{path.relative_to(ROOT).as_posix()}` — CSV, "
            f"{path.stat().st_size:,} octets, {len(data):,} lignes, {len(data.columns)} colonnes.",
            "  Colonnes : " + ", ".join(f"`{column}`" for column in data.columns) + ".",
        ])

    movies = pd.read_csv(path_for("movies"), dtype=str, keep_default_na=False)
    tmdb_ids = set(movies["id"])
    imdb_ids = set(movies["imdb_id"])
    poster_names = {Path(value).name for value in movies["poster_path"] if value}
    paths = poster_paths()
    formats = Counter()
    suffix_matches = 0
    image_rows = []
    for path in paths:
        # Lire l'en-tête pour identifier le format réel, sans décoder tous les pixels.
        try:
            with Image.open(path) as image:
                image_format = image.format
        except (OSError, ValueError, Image.DecompressionBombError):
            image_format = "illisible"
        formats[image_format] += 1
        image_rows.append((path.name, path.relative_to(ROOT).as_posix(), image_format, path.stat().st_size))
        name_parts = re.fullmatch(r"[0-9]+(?:\.[0-9]+)?_([0-9]+)", path.stem)
        if name_parts and name_parts[1] in tmdb_ids:
            suffix_matches += 1

    lines.extend([
        "", "## Affiches", "",
        f"- `{path_for('posters').relative_to(ROOT).as_posix()}/` — {len(paths):,} fichiers, "
        f"{sum(row[3] for row in image_rows):,} octets.",
        "- Formats détectés : " + ", ".join(f"{name} ({count:,})" for name, count in formats.items()) + ".",
        "- Exemples : " + ", ".join(f"`{path.name}` ({path.stat().st_size:,} octets)" for path in paths[:3]) + ".",
        "- [Liste complète des affiches](poster_inventory.csv) avec le format et la taille de chaque fichier.",
        "", "## Sources et identifiants", "",
        "- [The Movies Dataset](https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset) "
        "documente les métadonnées TMDB et le sous-ensemble de notes MovieLens. "
        "Le nombre et le nom des fichiers locaux concordent avec la collection "
        "[Movie Posters](https://www.kaggle.com/datasets/phiitm/movie-posters).",
        "- `movies_metadata.id` est un identifiant TMDB et `imdb_id` est un identifiant IMDb. "
        "`ratings_small.movieId` appartient à MovieLens. Un fichier de correspondance serait requis "
        "pour joindre les notes aux films.",
        f"- Suffixes numériques présents parmi les ID TMDB : {suffix_matches:,}. "
        "Ces coïncidences ne suffisent pas à établir une correspondance.",
        f"- Suffixes convertis en ID IMDb et présents dans `imdb_id` : "
        f"{sum(poster_imdb_id(path.name) in imdb_ids for path in paths):,}.",
        f"- Noms de fichiers présents dans `poster_path` : "
        f"{sum(path.name in poster_names for path in paths):,}.",
    ])
    with (path_for("reports") / "poster_inventory.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["filename", "image_path", "format", "size_bytes"])
        writer.writerows(image_rows)
    result = "\n".join(lines) + "\n"
    (path_for("reports") / "dataset_inventory.md").write_text(result, encoding="utf-8")
    print(result)


if __name__ == "__main__":
    main()
