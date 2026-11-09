from datetime import date
import re


IMPORTANT = {
    "movies_metadata": ["id", "imdb_id", "title", "release_date", "vote_average"],
    "ratings_small": ["userId", "movieId", "rating", "timestamp"],
}


def valid_date(value):
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False
