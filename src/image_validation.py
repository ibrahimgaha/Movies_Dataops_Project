import pandas as pd

from src.csv_ingestion import read_csv
from src.image_preprocessing import FEATURE_FIELDS
from src.settings import PARAMS, path_for, save_csv, stage_log


def valid_image_rows(data, width, height):
    if list(data.columns) != FEATURE_FIELDS:
        raise ValueError("Le schéma des caractéristiques d’image est invalide.")
    colors = ["avg_red", "avg_green", "avg_blue"]
    numbers = data[colors + ["width", "height", "processed_width", "processed_height", "channels", "size_kb"]]
    numbers = numbers.apply(pd.to_numeric, errors="coerce")
    return (
        numbers["processed_width"].eq(width) & numbers["processed_height"].eq(height)
        & numbers["channels"].eq(3) & numbers["width"].gt(0) & numbers["height"].gt(0)
        & numbers["width"].mod(1).eq(0) & numbers["height"].mod(1).eq(0)
        & numbers["size_kb"].ge(0) & numbers["size_kb"].lt(float("inf")) & numbers[colors].ge(0).all(axis=1)
        & numbers[colors].le(255).all(axis=1)
        & data["image_path"].str.strip().ne("") & data["filename"].str.strip().ne("")
        & data["format"].str.strip().ne("") & ~data["image_path"].duplicated(keep=False)
    )


def main():
    interim = path_for("interim")
    data = read_csv(interim / "posters_preprocessed.csv")
    unreadable = read_csv(interim / "posters_unreadable.csv")
    mask = valid_image_rows(data, PARAMS["images"]["width"], PARAMS["images"]["height"])
    valid = data.loc[mask]
    invalid = data.loc[~mask, ["image_path"]].assign(reason="invalid_features")
    rejected = pd.concat([unreadable, invalid], ignore_index=True)
    total = len(data) + len(unreadable)
    quality = PARAMS["quality"]
    fraction = len(rejected) / total if total else 0
    stage_log("image_validation", {
        "selected": total, "valid": len(valid), "rejected": len(rejected),
        "invalid_features": len(invalid), "unreadable": len(unreadable), "rejected_fraction": fraction,
    })
    if len(valid) < quality["min_valid_images"] or fraction > quality["max_invalid_image_fraction"]:
        raise SystemExit("Qualité des affiches insuffisante. Consulter image_validation.json.")
    save_csv(valid, interim / "posters_valid.csv")
    save_csv(rejected, interim / "posters_rejected.csv")


if __name__ == "__main__":
    main()
