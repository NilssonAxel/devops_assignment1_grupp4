"""Unit tests for the Silver layer."""

import json
from datetime import datetime, timezone

import polars as pl

from src.silver import transform_all


def _bronze_rows(records):
    moment = datetime(2026, 1, 1, tzinfo=timezone.utc)

    return pl.DataFrame(
        {
            "ingested_at": [moment] * len(records),
            "source_system": ["restcountries-v5"] * len(records),
            "raw": [json.dumps(record) for record in records],
        }
    )


def test_missing_population_becomes_zero():
    record = {
        "names": {"common": "Testland"},
        "codes": {"ccn3": "123"},
        "capitals": [{"name": "Test City"}],
        "population": None,
        "region": "Europe",
        "continents": ["Europe"],
        "currencies": [{"code": "EUR"}],
    }

    result = transform_all(_bronze_rows([record]))

    assert result["population"][0] == 0


def test_missing_region_becomes_unknown():
    record = {
        "names": {"common": "Testland"},
        "codes": {"ccn3": "123"},
        "capitals": [{"name": "Test City"}],
        "population": 1000,
        "region": None,
        "continents": ["Europe"],
        "currencies": [{"code": "EUR"}],
    }

    result = transform_all(_bronze_rows([record]))

    assert result["region"][0] == "Unknown"


def test_record_without_name_is_filtered_out():
    record = {
        "names": {"common": None},
        "codes": {"ccn3": "123"},
        "capitals": [{"name": "Test City"}],
        "population": 1000,
        "region": "Europe",
        "continents": ["Europe"],
        "currencies": [{"code": "EUR"}],
    }

    result = transform_all(_bronze_rows([record]))

    assert result.is_empty()


def test_country_name_whitespace_is_removed():
    record = {
        "names": {"common": "  Sweden  "},
        "codes": {"ccn3": "752"},
        "capitals": [{"name": "Stockholm"}],
        "population": 10_500_000,
        "region": "Europe",
        "continents": ["Europe"],
        "currencies": [{"code": "SEK"}],
    }

    result = transform_all(_bronze_rows([record]))

    assert result["name"][0] == "Sweden"


def test_currency_codes_are_extracted():
    record = {
        "names": {"common": "Testland"},
        "codes": {"ccn3": "123"},
        "capitals": [{"name": "Test City"}],
        "population": 1000,
        "region": "Europe",
        "continents": ["Europe"],
        "currencies": [
            {"code": "EUR"},
            {"code": "USD"},
        ],
    }

    result = transform_all(_bronze_rows([record]))

    assert result["currencies"].to_list()[0] == ["EUR", "USD"]


def test_empty_input_returns_empty_dataframe():
    bronze = pl.DataFrame(
        schema={
            "ingested_at": pl.Datetime("us", "UTC"),
            "source_system": pl.Utf8,
            "raw": pl.Utf8,
        }
    )

    result = transform_all(bronze)

    assert result.is_empty()
    assert result.columns == [
        "name",
        "capital",
        "population",
        "region",
        "continents",
        "currencies",
        "ccn3",
        "ingested_at",
        "source_system",
    ]
