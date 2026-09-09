"""Post-deploy smoke check for the scheduled pipeline run.

Unlike tests/test_integration.py, this runs against the real Gold output
produced by the live pipeline (data/gold_summary.parquet), not stubbed
data in a temp directory. It only checks that the output exists and looks
plausible -- not that every value is correct -- so it stays fast and
catches gross breakage such as the source going away or changing shape.
"""

from pathlib import Path

import polars as pl

from src.gold import DEFAULT_OUTPUT_PATH

GOLD_COLUMNS = frozenset({"metric", "category", "value"})


def check(output_path: Path = DEFAULT_OUTPUT_PATH) -> None:
    if not output_path.exists():
        raise SystemExit(f"Smoke check failed: {output_path} does not exist")

    gold_df = pl.read_parquet(output_path)

    if gold_df.is_empty():
        raise SystemExit(f"Smoke check failed: {output_path} has no rows")

    missing_columns = GOLD_COLUMNS.difference(gold_df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise SystemExit(f"Smoke check failed: missing columns {missing}")

    totals = gold_df.filter(
        (pl.col("metric") == "total_countries") & (pl.col("category") == "all")
    )
    total_countries = totals["value"].item() if not totals.is_empty() else 0

    if total_countries <= 0:
        raise SystemExit("Smoke check failed: total_countries is missing or zero")

    print(f"Smoke check passed: {output_path} reports {total_countries} countries")


if __name__ == "__main__":
    check()
