from src.bronze import land_raw
from src.gold import summarize
from src.silver import transform_all
from src.staging import fetch_countries


def run_pipeline():
    """Runs the full pipeline: staging -> bronze -> silver -> gold."""
    raw = fetch_countries()
    land_raw(raw)
    cleaned = transform_all(raw)
    return summarize(cleaned)


if __name__ == "__main__":
    output_path = run_pipeline()
    print(f"Gold data written to: {output_path}")
