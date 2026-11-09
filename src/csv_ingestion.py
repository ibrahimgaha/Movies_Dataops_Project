import pandas as pd

from src.settings import path_for, save_csv, stage_log


def read_csv(path):
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")


def main():
    counts = {}
    for name in ("movies", "ratings"):
        table = read_csv(path_for(name))
        save_csv(table, path_for("interim") / f"{name}_ingested.csv")
        counts[name] = {"rows": len(table), "columns": len(table.columns)}
    stage_log("csv_ingestion", counts)


if __name__ == "__main__":
    main()
