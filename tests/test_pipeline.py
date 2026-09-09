"""Unit tests for the pipeline orchestration."""

from pathlib import Path

from src import pipeline


def test_run_pipeline_connects_stages_in_order(monkeypatch):
    """Each stage should receive the output from the previous stage."""
    call_order = []

    raw_data = object()
    bronze_rows = object()
    latest_rows = object()
    cleaned_data = object()
    gold_path = Path("data/gold_summary.parquet")

    def fake_fetch_countries():
        call_order.append("staging")
        return raw_data

    def fake_to_rows(received):
        assert received is raw_data
        call_order.append("to_rows")
        return bronze_rows

    def fake_land_raw(received):
        assert received is bronze_rows
        call_order.append("land_raw")
        return 1

    def fake_latest_batch():
        call_order.append("latest_batch")
        return latest_rows

    def fake_transform_all(received):
        assert received is latest_rows
        call_order.append("silver")
        return cleaned_data

    def fake_summarize(received):
        assert received is cleaned_data
        call_order.append("gold")
        return gold_path

    monkeypatch.setattr(pipeline, "fetch_countries", fake_fetch_countries)
    monkeypatch.setattr(pipeline, "to_rows", fake_to_rows)
    monkeypatch.setattr(pipeline, "land_raw", fake_land_raw)
    monkeypatch.setattr(pipeline, "latest_batch", fake_latest_batch)
    monkeypatch.setattr(pipeline, "transform_all", fake_transform_all)
    monkeypatch.setattr(pipeline, "summarize", fake_summarize)

    result = pipeline.run_pipeline()

    assert result == gold_path
    assert call_order == [
        "staging",
        "to_rows",
        "land_raw",
        "latest_batch",
        "silver",
        "gold",
    ]
