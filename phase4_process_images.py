import csv
import random

import numpy as np
from PIL import Image

from phase1_inventory import ROOT, poster_paths


FIELDS = [
    "filename", "image_path", "width", "height", "format", "size_kb",
    "avg_red", "avg_green", "avg_blue",
]


def extract_features(path):
    with Image.open(path) as image:
        width, height = image.size
        image_format = image.format
        # Standardiser les couleurs et les dimensions avant de mesurer les pixels.
        resized = image.convert("RGB").resize((224, 224), Image.Resampling.BILINEAR)
        pixels = np.asarray(resized)
        red, green, blue = pixels.mean(axis=(0, 1))
    return {
        "filename": path.name,
        "image_path": path.relative_to(ROOT).as_posix(),
        "width": width,
        "height": height,
        "format": image_format,
        "size_kb": round(path.stat().st_size / 1024, 3),
        "avg_red": round(float(red), 3),
        "avg_green": round(float(green), 3),
        "avg_blue": round(float(blue), 3),
    }


def main():
    paths = poster_paths()
    if not paths:
        raise SystemExit("Aucune affiche trouvée dans data/images.")
    # La graine fixe produit le même échantillon à chaque relance.
    sample = random.Random(42).sample(paths, min(100, len(paths)))
    rows = []
    for path in sorted(sample):
        try:
            rows.append(extract_features(path))
        except (OSError, ValueError, Image.DecompressionBombError) as error:
            print(f"WARN {path.name} : {error}")
    if not rows:
        raise SystemExit("Aucune image de l’échantillon n’a pu être lue.")

    output = ROOT / "reports" / "poster_features.csv"
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Disponibles : {len(paths):,} | Sélectionnées : {len(sample)} | "
          f"Exportées : {len(rows)} | Ignorées : {len(sample) - len(rows)}")


if __name__ == "__main__":
    main()
