from src.bronze import land_raw, latest_batch, to_rows
from src.gold import summarize
from src.silver import transform_all
from src.staging import fetch_countries


def run_pipeline():
    """Runs the full pipeline: staging -> bronze -> silver -> gold."""
    raw = fetch_countries()
    land_raw(to_rows(raw))
    bronze_data = latest_batch()
    cleaned = transform_all(bronze_data)
    return summarize(cleaned)


if __name__ == "__main__":
    output_path = run_pipeline()
    print(f"Gold data written to: {output_path}")
