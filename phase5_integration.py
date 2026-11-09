from collections import Counter
from hashlib import sha256
from pathlib import PurePosixPath
import re

import pandas as pd
from psycopg import sql

from phase1_inventory import poster_imdb_id
from phase2_ingestion import REPORT_DIR, SCHEMA, TABLES, connect
from phase4_process_images import FIELDS
from src.settings import PARAMS


def table_fingerprint(cursor, table):
    name = sql.Identifier(SCHEMA, table)
    cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(name))
    count = cursor.fetchone()[0]
    digest = sha256()
    # Trier la représentation complète des lignes pour comparer aussi leur contenu.
    query = sql.SQL("COPY (SELECT to_jsonb(source)::text FROM {} AS source ORDER BY 1) TO STDOUT")
    with cursor.copy(query.format(name)) as copy:
        for block in copy:
            digest.update(block)
    return count, digest.hexdigest()


def movie_lookup(cursor):
    cursor.execute(sql.SQL("SELECT id, imdb_id FROM {}").format(sql.Identifier(SCHEMA, "movies_metadata")))
    rows = cursor.fetchall()
    tmdb_counts = Counter(movie_id for movie_id, imdb_id in rows)
    imdb_counts = Counter(imdb_id for movie_id, imdb_id in rows)
    # Garder uniquement les correspondances qui pointent vers un film unique.
    return {
        imdb_id: movie_id for movie_id, imdb_id in rows
        if movie_id and re.fullmatch(r"[0-9]+", movie_id) and tmdb_counts[movie_id] == 1
        and imdb_id and imdb_counts[imdb_id] == 1
    }


def stored_paths(cursor, name, current_paths):
    # Une affiche déjà importée peut encore porter son ancien chemin PostgreSQL.
    folder = PurePosixPath(PARAMS["paths"]["posters"])
    legacy = PurePosixPath(PARAMS["paths"]["legacy_posters"])
    aliases = {
        path: (legacy / PurePosixPath(path).relative_to(folder)).as_posix()
        for path in current_paths if PurePosixPath(path).is_relative_to(folder)
    }
    cursor.execute(sql.SQL("SELECT image_path FROM {} WHERE image_path = ANY(%s)").format(name),
                   ([*current_paths, *aliases.values()],))
    existing = {row[0] for row in cursor.fetchall()}
    return {
        path: aliases[path] for path in aliases
        if path not in existing and aliases[path] in existing
    }


def main():
    features = pd.read_csv(REPORT_DIR / "poster_features.csv", dtype=str, keep_default_na=False)
    if list(features.columns) != FIELDS or features.empty:
        raise SystemExit("Le CSV des affiches doit contenir les colonnes et les lignes de la phase 4.")
    if features["image_path"].eq("").any() or features["image_path"].duplicated().any():
        raise SystemExit("Chaque affiche du CSV doit avoir un chemin distinct et renseigné.")

    with connect() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (SCHEMA,))
        # Le verrou partagé permet les lectures et bloque les écritures concurrentes.
        for table in TABLES:
            cursor.execute(sql.SQL("LOCK TABLE {} IN SHARE MODE").format(sql.Identifier(SCHEMA, table)))
        before = {table: table_fingerprint(cursor, table) for table in TABLES}
        lookup = movie_lookup(cursor)
        name = sql.Identifier(SCHEMA, "movie_posters")
        cursor.execute(sql.SQL("""
            CREATE TABLE IF NOT EXISTS {} (
                poster_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                movie_id TEXT,
                imdb_id TEXT,
                match_status TEXT NOT NULL,
                filename TEXT NOT NULL,
                image_path TEXT NOT NULL UNIQUE,
                width INTEGER NOT NULL CHECK (width > 0),
                height INTEGER NOT NULL CHECK (height > 0),
                format TEXT NOT NULL,
                size_kb NUMERIC NOT NULL CHECK (size_kb >= 0),
                avg_red NUMERIC NOT NULL CHECK (avg_red BETWEEN 0 AND 255),
                avg_green NUMERIC NOT NULL CHECK (avg_green BETWEEN 0 AND 255),
                avg_blue NUMERIC NOT NULL CHECK (avg_blue BETWEEN 0 AND 255),
                CHECK ((match_status = 'matched' AND movie_id IS NOT NULL AND imdb_id IS NOT NULL)
                    OR (match_status = 'unmatched' AND movie_id IS NULL))
            )
        """).format(name))
        aliases = stored_paths(cursor, name, features["image_path"].tolist())
        features["image_path"] = features["image_path"].replace(aliases)
        rows = []
        for feature in features.itertuples(index=False, name=None):
            imdb_id = poster_imdb_id(feature[0])
            movie_id = lookup.get(imdb_id)
            status = "matched" if movie_id is not None else "unmatched"
            rows.append((movie_id, imdb_id, status, *feature))
        cursor.executemany(sql.SQL("""
            INSERT INTO {} (movie_id, imdb_id, match_status, filename, image_path,
                width, height, format, size_kb, avg_red, avg_green, avg_blue)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (image_path) DO NOTHING
        """).format(name), rows)
        inserted = cursor.rowcount
        cursor.execute(sql.SQL("""
            SELECT COUNT(*), COUNT(*) FILTER (WHERE match_status = 'matched')
            FROM {} WHERE image_path = ANY(%s)
        """).format(name), (features["image_path"].tolist(),))
        total, matched = cursor.fetchone()
        if total != len(features):
            raise RuntimeError("Le nombre d’affiches en base diffère du CSV.")
        for table in TABLES:
            if table_fingerprint(cursor, table) != before[table]:
                raise RuntimeError(f"Les données sources de {table} ont changé.")

    print(f"Affiches du CSV en base : {total} | Ajoutées : {inserted} | "
          f"Liées : {matched} | Non liées : {total - matched}")
    for table, (count, _) in before.items():
        print(f"{table} : {count:,} lignes, empreinte SHA-256 identique avant et après.")


if __name__ == "__main__":
    main()
