import pandas as pd

from src.csv_ingestion import read_csv
from src.csv_schema import IMPORTANT, valid_date
from src.settings import PARAMS, path_for, save_csv, stage_log


def clean_csv(data, name, quality):
    is_movie = name == "movies"
    table = "movies_metadata" if is_movie else "ratings_small"
    required = IMPORTANT[table]
    absent = set(required) - set(data.columns)
    if absent:
        raise ValueError(f"{name} : colonnes absentes {sorted(absent)}")
    if len(data) < quality[f"min_{name}"]:
        raise ValueError(f"{name} : volume insuffisant ({len(data)})")

    checked = data[required].apply(lambda column: column.str.strip())
    empty = checked.eq("")
    complete = ~empty.any(axis=1)
    keys = [["id"], ["imdb_id"]] if is_movie else [["userId", "movieId"]]
    duplicate_counts = {}
    for key in keys:
        present = ~empty[key].any(axis=1)
        duplicate_counts["+".join(key)] = int(checked.loc[present].duplicated(key).sum())

    rating_column = "vote_average" if is_movie else "rating"
    range_key = "movie_rating_range" if is_movie else "user_rating_range"
    rating = pd.to_numeric(checked[rating_column], errors="coerce")
    bad_rating = ~empty[rating_column] & ~rating.between(*quality[range_key])
    if is_movie:
        valid_id = checked["id"].str.fullmatch(r"[0-9]+")
        valid_imdb = checked["imdb_id"].str.fullmatch(r"tt[0-9]{7,10}")
        valid_dates = checked["release_date"].map(valid_date)
        invalid = (
            (~empty["id"] & ~valid_id)
            | (~empty["imdb_id"] & ~valid_imdb)
            | (~empty["release_date"] & ~valid_dates)
        )
        # Une clé répétée reste ambiguë, même si une seule ligne survit au nettoyage.
        eligible = ~(checked["id"].duplicated(keep=False) | checked["imdb_id"].duplicated(keep=False))
    else:
        valid_types = checked[["userId", "movieId", "timestamp"]].apply(
            lambda column: column.str.fullmatch(r"[0-9]+")
        )
        invalid = (~empty[valid_types.columns] & ~valid_types).any(axis=1)

    selected = checked.loc[complete & ~invalid & ~bad_rating]
    before_dedup = len(selected)
    for key in keys:
        selected = selected.drop_duplicates(key)
    clean = data.loc[selected.index].copy()
    for column in required:
        clean[column] = selected[column]
    clean[rating_column] = rating.loc[selected.index].astype(float)
    if is_movie:
        clean["poster_key_eligible"] = eligible.loc[selected.index]
    else:
        clean["timestamp"] = pd.to_numeric(selected["timestamp"], errors="raise")

    stats = {
        "input_rows": len(data), "valid_rows": len(clean), "rejected_rows": len(data) - len(clean),
        "missing_by_column": {key: int(count) for key, count in empty.sum().items()},
        "rows_with_missing": int((~complete).sum()), "duplicates_by_key": duplicate_counts,
        "duplicates_rejected": before_dedup - len(clean), "invalid_types_or_dates": int(invalid.sum()),
        "invalid_ratings": int(bad_rating.sum()),
    }
    issues = []
    checks = [
        ("valeurs manquantes", max(stats["missing_by_column"].values()), "max_missing_fraction"),
        ("identifiants dupliqués", max(duplicate_counts.values()), "max_duplicate_fraction"),
        ("types ou dates invalides", stats["invalid_types_or_dates"],
         "max_invalid_movie_fraction" if is_movie else "max_invalid_rating_fraction"),
        ("notes invalides", stats["invalid_ratings"], "max_invalid_rating_fraction"),
    ]
    for label, count, limit in checks:
        if count / len(data) > quality[limit]:
            issues.append(f"{name} : {label} ({count}/{len(data)}, seuil {quality[limit]:.2%})")
    if clean.empty:
        issues.append(f"{name} : aucune ligne valide")
    return clean, stats, issues


def main():
    interim = path_for("interim")
    results, stats, issues = {}, {}, []
    for name in ("movies", "ratings"):
        data = read_csv(interim / f"{name}_ingested.csv")
        results[name], stats[name], problems = clean_csv(data, name, PARAMS["quality"])
        issues.extend(problems)
    stats["failures"] = issues
    stage_log("csv_validation", stats)
    if issues:
        raise SystemExit("\n".join(issues))
    for name, data in results.items():
        save_csv(data, interim / f"{name}_valid.csv")


if __name__ == "__main__":
    main()
