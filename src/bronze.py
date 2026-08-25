import json
import os

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
)
RAW_PATH = os.path.join(DATA_DIR, "raw_countries.json")


def land_raw(raw_list, path=RAW_PATH):
    """Persists the raw fetched records to disk. Step 2 in the pipeline.

    Decouples the network fetch from transform/aggregate so those
    steps (and their tests) can run offline against a landed file.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(raw_list, f, ensure_ascii=False, indent=2)
    return path


def load_raw(path=RAW_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)
