from phase1_inventory import poster_imdb_id
from src.csv_ingestion import read_csv
from src.settings import path_for, save_csv, stage_log


def align_posters(movies, posters):
    eligible = movies.loc[movies["poster_key_eligible"].eq("True")]
    lookup = eligible.set_index("imdb_id")["id"]
    aligned = posters.copy()
    aligned["imdb_id"] = aligned["filename"].map(poster_imdb_id).fillna("")
    aligned["movie_id"] = aligned["imdb_id"].map(lookup).fillna("")
    aligned["match_status"] = "unmatched"
    aligned["match_reason"] = "no_unique_movie"
    aligned.loc[aligned["imdb_id"].eq(""), "match_reason"] = "unrecognized_filename"
    matched = aligned["movie_id"].ne("")
    aligned.loc[matched, ["match_status", "match_reason"]] = ["matched", "unique_imdb_id"]
    return aligned


def main():
    interim = path_for("interim")
    movies = read_csv(interim / "movies_valid.csv")
    posters = read_csv(interim / "posters_valid.csv")
    aligned = align_posters(movies, posters)
    save_csv(aligned, interim / "posters_aligned.csv")
    matched = aligned["match_status"].eq("matched")
    stage_log("alignment", {
        "movies": len(movies), "posters": len(aligned), "matched_posters": int(matched.sum()),
        "unmatched_posters": int((~matched).sum()), "movies_with_poster": aligned.loc[matched, "movie_id"].nunique(),
        "by_reason": aligned["match_reason"].value_counts().to_dict(),
    })


if __name__ == "__main__":
    main()
