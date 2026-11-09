import json

import pandas as pd

from src.csv_ingestion import read_csv
from src.settings import path_for, save_csv, stage_log


def join_movies(movies, aligned):
    matched = aligned.loc[aligned["match_status"].eq("matched")]
    # Si plusieurs affiches existent, garder le premier chemin par ordre alphabétique.
    first = matched.sort_values("image_path").drop_duplicates("movie_id")
    features = first.drop(columns=["imdb_id", "match_status", "match_reason"])
    features = features.rename(columns={column: f"poster_{column}" for column in features if column != "movie_id"})
    result = movies.merge(features, left_on="id", right_on="movie_id", how="left", validate="one_to_one")
    result["has_poster"] = result["movie_id"].notna()
    return result.drop(columns=["movie_id"])


def main():
    interim, processed = path_for("interim"), path_for("processed")
    movies = read_csv(interim / "movies_valid.csv")
    ratings = read_csv(interim / "ratings_valid.csv")
    aligned = read_csv(interim / "posters_aligned.csv")
    result = join_movies(movies, aligned)
    save_csv(result, processed / "movies_multimodal.csv")
    save_csv(aligned, processed / "poster_features.csv")
    save_csv(ratings, processed / "ratings_prepared.csv")
    stages = ["csv_ingestion", "csv_validation", "image_preprocessing", "image_validation", "alignment"]
    summary = {
        stage: json.loads((interim / f"{stage}.json").read_text(encoding="utf-8"))
        for stage in stages
    }
    summary["export"] = {
        "movies": len(result), "movies_with_poster": int(result["has_poster"].sum()),
        "movies_without_poster": int((~result["has_poster"]).sum()),
        "ratings": len(ratings), "posters": len(aligned),
        "rating_distribution": ratings["rating"].value_counts().sort_index().to_dict(),
        "mean_rgb": {
            color: round(float(pd.to_numeric(aligned[f"avg_{color}"]).mean()), 3)
            for color in ("red", "green", "blue")
        },
    }
    stage_log("export", summary["export"])
    (processed / "statistics.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
