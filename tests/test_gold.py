"""Unit tests for the Gold layer.

Gold aggregates cleaned Silver data into business metrics and writes
the result to a Parquet file.
"""

import polars as pl
import pytest

from src.gold import summarize


@pytest.fixture
def silver_data():
    """Small Silver dataset with known aggregation results."""
    return pl.DataFrame(
        {
            "name": ["Sweden", "Japan", "Russia"],
            "capital": ["Stockholm", "Tokyo", "Moscow"],
            "population": [10_500_000, 125_000_000, 145_000_000],
            "region": ["Europe", "Asia", "Europe"],
            "continents": [
                ["Europe"],
                ["Asia"],
                ["Europe", "Asia"],
            ],
            "currencies": [
                ["SEK"],
                ["JPY"],
                ["RUB"],
            ],
        }
    )


def _run_and_read(silver_data, tmp_path):
    """Run Gold without writing test files into the project's data folder."""
    output_path = tmp_path / "gold_summary.parquet"
    result_path = summarize(silver_data, output_path)

    return result_path, pl.read_parquet(result_path)


def _metric_values(gold_data, metric):
    """Return category and value pairs for one Gold metric."""
    rows = gold_data.filter(pl.col("metric") == metric)

    return {
        row["category"]: row["value"]
        for row in rows.iter_rows(named=True)
    }


def test_summarize_writes_parquet_and_returns_path(silver_data, tmp_path):
    output_path = tmp_path / "nested" / "gold_summary.parquet"

    result_path = summarize(silver_data, output_path)

    assert result_path == output_path
    assert result_path.is_file()


def test_summarize_calculates_totals(silver_data, tmp_path):
    _, gold_data = _run_and_read(silver_data, tmp_path)

    assert _metric_values(gold_data, "total_countries") == {"all": 3}
    assert _metric_values(gold_data, "total_population") == {
        "all": 280_500_000
    }


def test_summarize_counts_countries_by_region(silver_data, tmp_path):
    _, gold_data = _run_and_read(silver_data, tmp_path)

    assert _metric_values(gold_data, "countries_by_region") == {
        "Asia": 1,
        "Europe": 2,
    }


def test_summarize_counts_countries_by_continent(silver_data, tmp_path):
    _, gold_data = _run_and_read(silver_data, tmp_path)

    assert _metric_values(gold_data, "countries_by_continent") == {
        "Asia": 2,
        "Europe": 2,
    }


def test_summarize_counts_countries_by_currency(silver_data, tmp_path):
    _, gold_data = _run_and_read(silver_data, tmp_path)

    assert _metric_values(gold_data, "countries_by_currency") == {
        "JPY": 1,
        "RUB": 1,
        "SEK": 1,
    }


def test_summarize_handles_empty_dataframe(silver_data, tmp_path):
    empty_data = silver_data.clear()

    _, gold_data = _run_and_read(empty_data, tmp_path)

    assert _metric_values(gold_data, "total_countries") == {"all": 0}
    assert _metric_values(gold_data, "total_population") == {"all": 0}
    assert gold_data.height == 2


def test_summarize_rejects_non_dataframe(tmp_path):
    output_path = tmp_path / "gold_summary.parquet"

    with pytest.raises(
        TypeError,
        match="cleaned_df must be a Polars DataFrame",
    ):
        summarize([], output_path)


def test_summarize_rejects_missing_columns(silver_data, tmp_path):
    incomplete_data = silver_data.drop(["capital", "currencies"])
    output_path = tmp_path / "gold_summary.parquet"

    with pytest.raises(
        ValueError,
        match="Missing required columns: capital, currencies",
    ):
        summarize(incomplete_data, output_path)