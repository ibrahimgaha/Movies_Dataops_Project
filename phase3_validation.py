from datetime import date
import re

import pandas as pd
from psycopg import Error, sql

from phase2_ingestion import REPORT_DIR, SCHEMA, SOURCE_DIR, TABLES, connect


IMPORTANT = {
    "movies_metadata": ["id", "imdb_id", "title", "release_date", "vote_average"],
    "ratings_small": ["userId", "movieId", "rating", "timestamp"],
}


def record(results, check, table, status, details):
    results.append(dict(check=check, table=table, status=status, details=details))
    print(f"{status:4} {table} / {check} : {details}")


def warn_if(results, check, table, count, details):
    record(results, check, table, "WARN" if count else "PASS", f"{count:,} {details}")


def duplicate_groups(data, columns):
    # Un groupe est compté une fois, même si sa clé apparaît plus de deux fois.
    present = data.loc[data[columns].ne("").all(axis=1), columns]
    return len(present[present.duplicated()].drop_duplicates())


def valid_date(value):
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def validate_table(cursor, table, results):
    cursor.execute("SELECT to_regclass(%s)", (f"{SCHEMA}.{table}",))
    exists = cursor.fetchone()[0] is not None
    record(results, "database_table", table, "PASS" if exists else "FAIL",
           "table présente" if exists else "table introuvable")
    path = SOURCE_DIR / f"{table}.csv"
    source_exists = path.is_file()
    record(results, "source_file", table, "PASS" if source_exists else "FAIL", path.name)
    if not exists:
        return

    name = sql.Identifier(SCHEMA, table)
    cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(name))
    database_count = cursor.fetchone()[0]
    if source_exists:
        with pd.read_csv(path, dtype=str, keep_default_na=False, chunksize=10_000) as chunks:
            source_count = sum(len(chunk) for chunk in chunks)
        record(results, "row_count", table, "PASS" if source_count == database_count else "FAIL",
               f"CSV={source_count:,} | PostgreSQL={database_count:,}")

    columns = IMPORTANT[table]
    cursor.execute(sql.SQL("SELECT * FROM {} LIMIT 0").format(name))
    missing = set(columns) - {column.name for column in cursor.description}
    if missing:
        record(results, "required_columns", table, "FAIL", ", ".join(sorted(missing)))
        return
    cursor.execute(sql.SQL("SELECT {} FROM {}").format(sql.SQL(", ").join(map(sql.Identifier, columns)), name))
    data = pd.DataFrame(cursor.fetchall(), columns=columns).fillna("").astype(str)
    for column in columns:
        data[column] = data[column].str.strip()
        warn_if(results, "missing_values", table, data[column].eq("").sum(), f"valeurs vides dans {column}")

    if table == "movies_metadata":
        for column in ("id", "imdb_id"):
            count = duplicate_groups(data, [column])
            warn_if(results, "duplicate_identifiers", table, count, f"groupes en double dans {column}")
        ids = data.loc[data["id"].ne(""), "id"]
        warn_if(results, "identifier_format", table, (~ids.str.fullmatch(r"[0-9]+")).sum(), "identifiants TMDB mal formés")
        dates = data.loc[data["release_date"].ne(""), "release_date"]
        warn_if(results, "release_date_format", table, (~dates.map(valid_date).astype(bool)).sum(), "dates non valides")
        rating_column, minimum, maximum = "vote_average", 0, 10
    else:
        count = duplicate_groups(data, ["userId", "movieId"])
        warn_if(results, "duplicate_identifiers", table, count, "paires utilisateur-film en double")
        rating_column, minimum, maximum = "rating", 0.5, 5

    values = pd.to_numeric(data.loc[data[rating_column].ne(""), rating_column], errors="coerce")
    warn_if(results, "rating_range", table, (~values.between(minimum, maximum)).sum(),
            f"valeurs non numériques ou hors de [{minimum}, {maximum}]")


def main():
    results = []
    try:
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            record(results, "database_connection", SCHEMA, "PASS", "connexion en lecture seule")
            for table in TABLES:
                validate_table(cursor, table, results)
    except (Error, OSError, ValueError, SystemExit) as error:
        record(results, "execution", SCHEMA, "FAIL", str(error))
    pd.DataFrame(results).to_csv(REPORT_DIR / "phase3_quality_report.csv", index=False, encoding="utf-8-sig")
    if any(result["status"] == "FAIL" for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
