import pandas as pd
from psycopg import sql

from phase2_ingestion import SCHEMA, TABLES, connect
from phase3_validation import IMPORTANT


DUPLICATE_KEYS = {
    "movies_metadata": [["id"], ["imdb_id"]],
    "ratings_small": [["userId", "movieId"]],
}


def clean_table(cursor, table):
    source = sql.Identifier(SCHEMA, table)
    target = sql.Identifier(SCHEMA, f"{table}_clean")
    cursor.execute("SELECT to_regclass(%s)", (f"{SCHEMA}.{table}_clean",))
    if cursor.fetchone()[0] is not None:
        cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(target))
        return f"{table}_clean : copie déjà présente ({cursor.fetchone()[0]:,} lignes)."

    # Un ordre stable permet de garder la même ligne en cas de doublon.
    cursor.execute(sql.SQL('SELECT * FROM {} AS source ORDER BY to_jsonb(source)::text COLLATE "C"').format(source))
    columns = [column.name for column in cursor.description]
    data = pd.DataFrame(cursor.fetchall(), columns=columns, dtype=object)
    # Normaliser uniquement les valeurs utilisées par les contrôles.
    checked = data[IMPORTANT[table]].fillna("").astype(str).apply(lambda column: column.str.strip())
    complete = checked.loc[checked.ne("").all(axis=1)]
    unique = complete
    for key in DUPLICATE_KEYS[table]:
        unique = unique.drop_duplicates(subset=key)

    # Copier les valeurs originales des lignes retenues dans une nouvelle table.
    cursor.execute(sql.SQL("CREATE TABLE {} AS SELECT * FROM {} WITH NO DATA").format(target, source))
    with cursor.copy(sql.SQL("COPY {} FROM STDIN").format(target)) as copy:
        for row in data.loc[unique.index].itertuples(index=False, name=None):
            copy.write_row(row)

    return (f"{table}_clean : {len(unique):,} lignes conservées, "
            f"{len(data) - len(complete):,} incomplètes et "
            f"{len(complete) - len(unique):,} doublons écartés.")


def main():
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (SCHEMA,))
        messages = [clean_table(cursor, table) for table in TABLES]
    print("\n".join(messages))


if __name__ == "__main__":
    main()
