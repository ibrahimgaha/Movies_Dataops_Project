import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

from PIL import Image
import yaml


ROOT = Path(__file__).resolve().parents[1]
MOVIES = (
    "id,imdb_id,title,release_date,vote_average\n"
    "1,tt0000011,Film A,2001-01-01,7.5\n"
    "2,tt0000022,Film B,2002-01-01,8.0\n"
    "3,tt0000033,Film C,2003-01-01,6.0\n"
)
RATINGS = "userId,movieId,rating,timestamp\n1,11,4.5,1000\n2,11,3.0,1010\n"


def prepare_fixture(workspace):
    shutil.copytree(ROOT / "src", workspace / "src", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "configs", workspace / "configs")
    for name in (
        "dvc.yaml", ".dvcignore", "requirements.txt", "phase1_inventory.py", "phase2_ingestion.py",
        "phase3_validation.py", "phase4_process_images.py",
    ):
        shutil.copy2(ROOT / name, workspace / name)
    config = workspace / "configs/params.yaml"
    params = yaml.safe_load(config.read_text(encoding="utf-8"))
    params["images"]["sample_size"] = params["images"]["test_sample_size"]
    params["quality"].update(min_movies=1, min_ratings=1)
    config.write_text(yaml.safe_dump(params), encoding="utf-8")
    posters = workspace / "data/raw/posters"
    posters.mkdir(parents=True)
    (posters.parent / "movies_metadata.csv").write_text(MOVIES, encoding="utf-8")
    (posters.parent / "ratings_small.csv").write_text(RATINGS, encoding="utf-8")
    for name in ("7.0_11.png", "8.0_22.png", "5.0_99.png", "inconnu.png"):
        Image.new("RGB", (12, 18), (100, 80, 50)).save(posters / name)
    return config


def run_dvc(workspace, *arguments, show=True):
    env = {
        **os.environ, "DVC_NO_ANALYTICS": "1", "PYTHONUTF8": "1",
        "DVC_SITE_CACHE_DIR": str(workspace / ".dvc-site-cache"),
    }
    result = subprocess.run(
        [sys.executable, "-m", "dvc", *arguments], cwd=workspace, env=env,
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    if show:
        print(result.stdout + result.stderr, end="")
    return result


def main():
    with TemporaryDirectory(prefix=".movies-demo-", dir=ROOT) as folder:
        workspace = Path(folder)
        config = prepare_fixture(workspace)
        run_dvc(workspace, "init", "--no-scm").check_returncode()
        run_dvc(workspace, "repro").check_returncode()
        statistics = workspace / "data/processed/statistics.json"
        summary = json.loads(statistics.read_text(encoding="utf-8"))
        assert summary["export"]["movies_with_poster"] == 2
        assert summary["export"]["movies_without_poster"] == 1
        assert summary["alignment"]["unmatched_posters"] == 2
        assert json.loads(run_dvc(workspace, "status", "--json", show=False).stdout) == {}

        unchanged = run_dvc(workspace, "repro")
        unchanged.check_returncode()
        assert "Running stage" not in unchanged.stdout + unchanged.stderr

        params = yaml.safe_load(config.read_text(encoding="utf-8"))
        original_width = params["images"]["width"]
        params["images"]["width"] = 32
        config.write_text(yaml.safe_dump(params), encoding="utf-8")
        changed = run_dvc(workspace, "repro")
        changed.check_returncode()
        output = changed.stdout + changed.stderr
        assert "Running stage 'image_preprocessing'" in output
        assert "Running stage 'csv_ingestion'" not in output
        assert "Running stage 'csv_validation'" not in output

        # Introduire une note hors plage uniquement dans la copie temporaire.
        ratings = workspace / "data/raw/ratings_small.csv"
        try:
            ratings.write_text(RATINGS.replace("4.5", "9.0"), encoding="utf-8")
            failure = run_dvc(workspace, "repro")
            assert failure.returncode != 0 and "notes invalides" in failure.stdout + failure.stderr
        finally:
            ratings.write_text(RATINGS, encoding="utf-8")
            params["images"]["width"] = original_width
            config.write_text(yaml.safe_dump(params), encoding="utf-8")
        run_dvc(workspace, "repro").check_returncode()
        assert json.loads(run_dvc(workspace, "status", "--json", show=False).stdout) == {}
        assert json.loads(statistics.read_text(encoding="utf-8")) == summary
        print("Démo réussie : exécution, relance, changement ciblé, échec contrôlé et restauration.")


if __name__ == "__main__":
    main()
