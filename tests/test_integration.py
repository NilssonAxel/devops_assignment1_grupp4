"""Integration test for the full pipeline: staging -> bronze -> silver -> gold.

The network is stubbed the same way test_staging.py does, patching the
session factory rather than requests itself, so this needs no API key
and no connectivity. It runs the real land_raw, latest_batch,
transform_all, and summarize functions against tmp_path, proving the
four stages fit together end to end rather than testing any one in
isolation.
"""

import types

import polars as pl

from src import bronze, gold, staging
from src.silver import transform_all

SAMPLE_COUNTRIES = [
    {
        "names": {"common": "Sweden"},
        "codes": {"ccn3": "752"},
        "capitals": [{"name": "Stockholm"}],
        "population": 10500000,
        "region": "Europe",
        "continents": ["Europe"],
        "currencies": [{"code": "SEK", "name": "krona"}],
    },
    {
        "names": {"common": "Norway"},
        "codes": {"ccn3": "578"},
        "capitals": [{"name": "Oslo"}],
        "population": 5400000,
        "region": "Europe",
        "continents": ["Europe"],
        "currencies": [{"code": "NOK", "name": "krone"}],
    },
]


class FakeResponse:
    """Stands in for a requests.Response, without touching the network."""

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        pass


def test_pipeline_runs_end_to_end(monkeypatch, tmp_path):
    monkeypatch.setattr(staging, "API_KEY", "test-key")
    session = types.SimpleNamespace(
        get=lambda *a, **k: FakeResponse(
            {
                "data": {
                    "objects": SAMPLE_COUNTRIES,
                    "meta": {"more": False, "total": len(SAMPLE_COUNTRIES)},
                }
            }
        )
    )
    monkeypatch.setattr(staging, "_session", lambda: session)

    raw = staging.fetch_countries()
    bronze_table = tmp_path / "countries_bronze.parquet"
    gold_table = tmp_path / "gold_summary.parquet"

    bronze.land_raw(bronze.to_rows(raw), str(bronze_table))
    cleaned = transform_all(bronze.latest_batch(str(bronze_table)))
    output_path = gold.summarize(cleaned, gold_table)

    assert output_path == gold_table
    assert output_path.exists()

    result = pl.read_parquet(output_path)
    totals = result.filter(pl.col("metric") == "total_countries")
    assert totals["value"].item() == len(SAMPLE_COUNTRIES)
