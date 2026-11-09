import os

import pandas as pd
import psycopg
from psycopg import sql

from src.settings import PARAMS, path_for

SOURCES = {"movies_metadata": path_for("movies"), "ratings_small": path_for("ratings")}
REPORT_DIR = path_for("reports")
POSTGRES = PARAMS["postgres"]
SCHEMA = POSTGRES["schema"]
TABLES = ("movies_metadata", "ratings_small")


def connect():
    # psycopg lit PGHOST, PGPORT, PGUSER, PGDATABASE et PGPASSWORD.
    if not os.environ.get("PGDATABASE"):
        raise SystemExit("Définissez PGDATABASE avec le nom de la base du projet.")
    return psycopg.connect(
        host=os.environ.get("PGHOST", POSTGRES["host"]),
        port=os.environ.get("PGPORT", POSTGRES["port"]),
        connect_timeout=POSTGRES["connect_timeout"],
    )


def import_csv(cursor, table):
    path = SOURCES[table]
    name = sql.Identifier(SCHEMA, table)
    cursor.execute("SELECT to_regclass(%s)", (f"{SCHEMA}.{table}",))
    if cursor.fetchone()[0] is not None:
        cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(name))
        return f"{table} : 0 ligne ajoutée, table déjà présente ({cursor.fetchone()[0]:,} lignes)."

    columns = pd.read_csv(path, nrows=0).columns
    definitions = sql.SQL(", ").join(sql.SQL("{} TEXT").format(sql.Identifier(col)) for col in columns)
    cursor.execute(sql.SQL("CREATE TABLE {} ({})").format(name, definitions))

    # COPY charge les lignes par blocs et conserve les valeurs en texte.
    imported = 0
    with cursor.copy(sql.SQL("COPY {} FROM STDIN").format(name)) as copy:
        with pd.read_csv(path, dtype=str, keep_default_na=False, chunksize=POSTGRES["chunk_size"]) as chunks:
            for chunk in chunks:
                for row in chunk.itertuples(index=False, name=None):
                    copy.write_row(row)
                imported += len(chunk)
    cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(name))
    if cursor.fetchone()[0] != imported:
        raise RuntimeError(f"Nombre de lignes incohérent pour {table}.")
    return f"{table} : {imported:,} lignes importées et vérifiées."


def main():
    for table in TABLES:
        if not SOURCES[table].is_file():
            raise SystemExit(f"CSV introuvable : {table}.csv")

    # Une transaction charge les deux tables ensemble. Le verrou sérialise les relances.
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (SCHEMA,))
        cursor.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(SCHEMA)))
        messages = [import_csv(cursor, table) for table in TABLES]
    print("\n".join(messages))


if __name__ == "__main__":
    main()
