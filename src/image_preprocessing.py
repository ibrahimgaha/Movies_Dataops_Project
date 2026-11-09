import random

import pandas as pd
from PIL import Image

from phase1_inventory import poster_paths
from phase4_process_images import FIELDS, extract_features
from src.settings import PARAMS, ROOT, path_for, save_csv, stage_log


FEATURE_FIELDS = FIELDS + ["processed_width", "processed_height", "channels"]


def main():
    paths = poster_paths()
    images = PARAMS["images"]
    count = images["sample_size"]
    if count < 0:
        raise SystemExit("La taille de l’échantillon doit être positive ou nulle.")
    selected = sorted(random.Random(images["seed"]).sample(paths, min(count, len(paths)))) if count else paths
    features, rejected = [], []
    for path in selected:
        try:
            features.append(extract_features(path))
        except (OSError, ValueError, Image.DecompressionBombError):
            rejected.append({"image_path": path.relative_to(ROOT).as_posix(), "reason": "unreadable"})

    interim = path_for("interim")
    save_csv(pd.DataFrame(features, columns=FEATURE_FIELDS), interim / "posters_preprocessed.csv")
    save_csv(pd.DataFrame(rejected, columns=["image_path", "reason"]), interim / "posters_unreadable.csv")
    stage_log("image_preprocessing", {
        "available": len(paths), "selected": len(selected), "readable": len(features), "unreadable": len(rejected),
    })


if __name__ == "__main__":
    main()
