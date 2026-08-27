import polars as pl

REQUIRED_COLUMNS = frozenset(
    {"name", "capital", "population", "region", "continents", "currencies"}
)


def _count_rows_by(df: pl.DataFrame, column: str) -> dict[str, int]:
    counts = df.group_by(column).agg(pl.len().alias("count")).sort(column)
    return dict(counts.select(column, "count").iter_rows())


def _count_list_values(df: pl.DataFrame, column: str) -> dict[str, int]:
    exploded = df.select(column).explode(column, empty_as_null=True).drop_nulls()
    return _count_rows_by(exploded, column)


def summarize(cleaned_df: pl.DataFrame) -> dict[str, object]:
    """Aggregate Silver country data into Gold metrics."""
    if not isinstance(cleaned_df, pl.DataFrame):
        raise TypeError("cleaned_df must be a Polars DataFrame")

    missing_columns = REQUIRED_COLUMNS.difference(cleaned_df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing required columns: {missing}")

    if cleaned_df.is_empty():
        return {
            "total_countries": 0,
            "total_population": 0,
            "regions": {},
            "continents": {},
            "currencies": {},
        }

    return {
        "total_countries": cleaned_df.height,
        "total_population": cleaned_df.select(pl.col("population").sum()).item(),
        "regions": _count_rows_by(cleaned_df, "region"),
        "continents": _count_list_values(cleaned_df, "continents"),
        "currencies": _count_list_values(cleaned_df, "currencies"),
    }
