import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
with (ROOT / "configs/params.yaml").open(encoding="utf-8") as file:
    PARAMS = yaml.safe_load(file)


def path_for(name):
    return ROOT / PARAMS["paths"][name]


def save_csv(data, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")


def stage_log(stage, stats):
    output = path_for("interim") / f"{stage}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    message = json.dumps(stats, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    output.write_text(message, encoding="utf-8")
    print(f"{stage} {json.dumps(stats, ensure_ascii=True, sort_keys=True)}")
