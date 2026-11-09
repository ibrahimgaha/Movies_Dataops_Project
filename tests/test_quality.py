from io import StringIO

import pandas as pd
from PIL import Image
import pytest

import phase4_process_images
from phase4_process_images import extract_features
from src.alignment import align_posters
from src.csv_validation import clean_csv
from src.export_dataset import join_movies
from src.image_validation import valid_image_rows
from src.settings import PARAMS
from tests.demo_pipeline import MOVIES, RATINGS


QUALITY = {**PARAMS["quality"], "min_movies": 1, "min_ratings": 1}


def csv_data(value):
    return pd.read_csv(StringIO(value), dtype=str, keep_default_na=False)


def test_schema_and_types():
    movies, _, issues = clean_csv(csv_data(MOVIES), "movies", QUALITY)
    ratings, _, rating_issues = clean_csv(csv_data(RATINGS), "ratings", QUALITY)
    assert not issues and not rating_issues
    assert movies["id"].tolist() == ["1", "2", "3"]
    assert pd.api.types.is_float_dtype(movies["vote_average"])
    assert pd.api.types.is_float_dtype(ratings["rating"])
    assert pd.api.types.is_integer_dtype(ratings["timestamp"])
    with pytest.raises(ValueError, match="colonnes absentes"):
        clean_csv(csv_data(MOVIES).drop(columns="imdb_id"), "movies", QUALITY)


def test_missing_values_and_duplicate_ids():
    source = MOVIES + "1,tt0000011,Copie,2001-01-01,7.5\n4,tt0000044, ,2004-01-01,5.0\n"
    clean, stats, issues = clean_csv(csv_data(source), "movies", QUALITY)
    assert stats["missing_by_column"]["title"] == 1
    assert stats["duplicates_by_key"] == {"id": 1, "imdb_id": 1}
    assert stats["rejected_rows"] == 2
    assert clean["id"].is_unique and clean["imdb_id"].is_unique
    assert not bool(clean.loc[clean["id"].eq("1"), "poster_key_eligible"].iloc[0])
    assert any("valeurs manquantes" in issue for issue in issues)
    assert any("identifiants dupliqués" in issue for issue in issues)


def test_duplicate_ratings_keep_different_users():
    ratings = csv_data(RATINGS + "1,11,4.0,1002\n")
    cleaned, stats, issues = clean_csv(ratings, "ratings", QUALITY)
    assert stats["duplicates_rejected"] == 1
    assert cleaned["userId"].tolist() == ["1", "2"]
    assert issues


def test_invalid_date_is_counted_even_if_other_field_is_missing():
    source = MOVIES + "4,tt0000044,,2004-02-30,5.0\n"
    _, stats, issues = clean_csv(csv_data(source), "movies", QUALITY)
    assert stats["invalid_types_or_dates"] == 1
    assert stats["rows_with_missing"] == stats["rejected_rows"] == 1
    assert any("types ou dates invalides" in issue for issue in issues)


@pytest.mark.parametrize("invalid", ["9", "-1", "non numérique"])
def test_invalid_ratings(invalid):
    _, stats, issues = clean_csv(csv_data(RATINGS.replace("4.5", invalid)), "ratings", QUALITY)
    assert stats["invalid_ratings"] == 1
    assert any("notes invalides" in issue for issue in issues)


def test_image_decoding_and_dimensions(tmp_path, monkeypatch):
    monkeypatch.setattr(phase4_process_images, "ROOT", tmp_path)
    path = tmp_path / "valid.png"
    Image.new("L", (9, 17), 80).save(path)
    feature = extract_features(path)
    assert (feature["width"], feature["height"]) == (9, 17)
    assert (feature["processed_width"], feature["processed_height"], feature["channels"]) == (224, 224, 3)
    assert [feature["avg_red"], feature["avg_green"], feature["avg_blue"]] == [80, 80, 80]
    data = pd.DataFrame([feature])
    assert valid_image_rows(data, 224, 224).tolist() == [True]
    data.loc[0, "processed_width"] = 223
    assert valid_image_rows(data, 224, 224).tolist() == [False]
    path.write_bytes(b"not an image")
    with pytest.raises(OSError):
        extract_features(path)


def test_alignment_preserves_unmatched_movies_and_posters():
    movies = csv_data(MOVIES).assign(poster_key_eligible=["True", "False", "True"])
    filenames = ["8.0_11.png", "7.0_11.png", "7.0_22.png", "7.0_99.png", "unknown.png"]
    posters = pd.DataFrame({"filename": filenames, "image_path": filenames})
    aligned = align_posters(movies, posters)
    assert aligned["movie_id"].tolist() == ["1", "1", "", "", ""]
    assert aligned["match_status"].tolist() == ["matched", "matched", "unmatched", "unmatched", "unmatched"]
    assert aligned["match_reason"].iloc[-1] == "unrecognized_filename"
    result = join_movies(movies, aligned)
    assert result["has_poster"].tolist() == [True, False, False]
    assert result.loc[0, "poster_image_path"] == "7.0_11.png"
    assert pd.isna(result.loc[1, "poster_image_path"])
