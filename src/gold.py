from pathlib import Path

import polars as pl

REQUIRED_COLUMNS = frozenset(
    {"name", "capital", "population", "region", "continents", "currencies"}
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "gold_summary.parquet"


def _count_rows_by(
    df: pl.DataFrame,
    column: str,
    metric: str,
) -> pl.DataFrame:
    return (
        df.group_by(column)
        .agg(pl.len().alias("value"))
        .sort(column)
        .rename({column: "category"})
        .with_columns(pl.lit(metric).alias("metric"))
        .select("metric", "category", "value")
    )


def _count_list_values(
    df: pl.DataFrame,
    column: str,
    metric: str,
) -> pl.DataFrame:
    exploded = df.select(column).explode(column, empty_as_null=True).drop_nulls()

    return _count_rows_by(exploded, column, metric)


def summarize(
    cleaned_df: pl.DataFrame,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    """Aggregate Silver country data and write Gold metrics to Parquet."""
    if not isinstance(cleaned_df, pl.DataFrame):
        raise TypeError("cleaned_df must be a Polars DataFrame")

    missing_columns = REQUIRED_COLUMNS.difference(cleaned_df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing required columns: {missing}")

    total_population = (
        cleaned_df.select(pl.col("population").sum()).item()
        if not cleaned_df.is_empty()
        else 0
    )

    totals = pl.DataFrame(
        {
            "metric": ["total_countries", "total_population"],
            "category": ["all", "all"],
            "value": [cleaned_df.height, total_population],
        }
    )

    gold_df = pl.concat(
        [
            totals,
            _count_rows_by(
                cleaned_df,
                "region",
                "countries_by_region",
            ),
            _count_list_values(
                cleaned_df,
                "continents",
                "countries_by_continent",
            ),
            _count_list_values(
                cleaned_df,
                "currencies",
                "countries_by_currency",
            ),
        ],
        how="vertical_relaxed",
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    gold_df.write_parquet(output_path)

    return output_path
