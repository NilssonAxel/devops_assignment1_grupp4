"""Unit tests for bronze.

Bronze's job is to land the staging payload verbatim with metadata
alongside, so most of these assert that nothing about the source record
changed on the way to disk and back.
"""

from datetime import datetime, timedelta, timezone

import polars as pl
import pytest

from src.bronze import (
    BRONZE_SCHEMA,
    SOURCE_SYSTEM,
    batch_digest,
    land_raw,
    latest_batch,
    load_raw,
    to_records,
    to_rows,
)

RAW = [
    {
        "names": {"common": "Sweden"},
        "codes": {"ccn3": "752"},
        "capitals": [{"name": "Stockholm"}],
        "population": 10500000,
        "region": "Europe",
        "continents": ["Europe"],
        "currencies": [{"code": "SEK", "name": "krona"}],
    },
    # disputed territory: empty nested values, the shape that cannot be
    # written to Parquet if the payload is unpacked into typed columns
    {
        "names": {},
        "codes": {"ccn3": ""},
        "capitals": [],
        "population": 244236,
        "region": "Asia",
        "continents": ["Asia"],
        "currencies": [],
    },
]


@pytest.fixture
def table(tmp_path):
    return str(tmp_path / "countries_bronze.parquet")


def test_schema_matches_contract():
    rows = to_rows(RAW)
    assert dict(rows.schema) == BRONZE_SCHEMA


def test_metadata_columns_are_populated():
    moment = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)
    rows = to_rows(RAW, ingested_at=moment)
    assert rows["ingested_at"].to_list() == [moment, moment]
    assert rows["source_system"].to_list() == [SOURCE_SYSTEM, SOURCE_SYSTEM]


def test_record_index_preserves_source_order():
    rows = to_rows(RAW)
    assert rows["record_index"].to_list() == [0, 1]


def test_payload_is_preserved_verbatim(table):
    """Issue #30: the source data must survive as close to original as possible."""
    land_raw(to_rows(RAW), table)
    assert to_records(load_raw(table)) == RAW


def test_empty_nested_objects_survive(table):
    """The record that crashes a typed-column Parquet write."""
    land_raw(to_rows(RAW), table)
    recovered = to_records(load_raw(table))
    assert recovered[1]["names"] == {}
    assert recovered[1]["capitals"] == []


def test_land_raw_appends_across_batches(table):
    t0 = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)
    land_raw(to_rows(RAW, ingested_at=t0), table)
    land_raw(to_rows(RAW[:1], ingested_at=t0 + timedelta(hours=1)), table)
    assert load_raw(table).height == 3


def test_latest_batch_returns_only_the_newest(table):
    t0 = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)
    land_raw(to_rows(RAW, ingested_at=t0), table)
    land_raw(to_rows(RAW[:1], ingested_at=t0 + timedelta(hours=1)), table)
    batch = latest_batch(table)
    assert batch.height == 1
    assert to_records(batch) == RAW[:1]


def test_schema_drift_between_batches_is_tolerated(table):
    """A field the API adds later must not break the append."""
    t0 = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)
    land_raw(to_rows(RAW, ingested_at=t0), table)
    drifted = [{**RAW[0], "landlocked": False, "newField": {"nested": 1}}]
    land_raw(to_rows(drifted, ingested_at=t0 + timedelta(hours=1)), table)
    assert to_records(latest_batch(table)) == drifted


def test_load_raw_on_missing_table_returns_empty(table):
    result = load_raw(table)
    assert result.is_empty()
    assert dict(result.schema) == BRONZE_SCHEMA


def test_failed_write_leaves_the_existing_table_intact(table, monkeypatch, tmp_path):
    """A crash mid-write must not truncate what was already landed."""
    land_raw(to_rows(RAW), table)
    before = to_records(load_raw(table))

    def exploding_write(self, *args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(pl.DataFrame, "write_parquet", exploding_write)
    with pytest.raises(OSError):
        land_raw(to_rows([{"names": {"common": "Norway"}}]), table)

    monkeypatch.undo()
    assert to_records(load_raw(table)) == before
    assert not list(tmp_path.glob("*.tmp"))


def test_unicode_survives_the_round_trip(table):
    records = [{"names": {"common": "Åland"}, "symbol": "₽", "cjk": "日本"}]
    land_raw(to_rows(records), table)
    assert to_records(load_raw(table)) == records


def test_unchanged_batch_is_not_appended_again(table):
    t0 = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)
    assert land_raw(to_rows(RAW, ingested_at=t0), table) == 2
    assert land_raw(to_rows(RAW, ingested_at=t0 + timedelta(hours=1)), table) == 0
    assert load_raw(table).height == 2


def test_changed_batch_is_appended(table):
    t0 = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)
    land_raw(to_rows(RAW, ingested_at=t0), table)
    changed = [{**RAW[0], "population": 999}]
    assert land_raw(to_rows(changed, ingested_at=t0 + timedelta(hours=1)), table) == 1


def test_source_reverting_counts_as_a_change(table):
    """A -> B -> A must land A again, so latest_batch reflects the source."""
    t0 = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)
    other = [{"names": {"common": "Norway"}, "population": 5}]
    land_raw(to_rows(RAW, ingested_at=t0), table)
    land_raw(to_rows(other, ingested_at=t0 + timedelta(hours=1)), table)
    assert land_raw(to_rows(RAW, ingested_at=t0 + timedelta(hours=2)), table) == 2
    assert to_records(latest_batch(table)) == RAW


def test_batch_digest_is_order_sensitive_and_stable():
    assert batch_digest(RAW) == batch_digest(list(RAW))
    assert batch_digest(RAW) != batch_digest(list(reversed(RAW)))


def test_key_order_does_not_change_the_digest():
    """sort_keys makes serialisation canonical, so an unchanged source
    that returns its keys in a different order still deduplicates."""
    assert batch_digest([{"a": 1, "b": 2}]) == batch_digest([{"b": 2, "a": 1}])


def test_unicode_is_stored_unescaped():
    """ensure_ascii=False keeps the raw column readable and stable."""
    rows = to_rows([{"name": "Åland"}])
    assert "Åland" in rows["raw"][0]
    assert "\\u" not in rows["raw"][0]


def test_latest_batch_is_ordered_by_record_index(table):
    land_raw(to_rows([{"n": i} for i in range(5)]), table)
    assert latest_batch(table)["record_index"].to_list() == [0, 1, 2, 3, 4]


def test_batches_sharing_a_timestamp_are_treated_as_one(table):
    """Known behaviour: latest_batch selects on ingested_at, so two writes
    with the same timestamp come back together."""
    t0 = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)
    land_raw(to_rows([{"a": 1}], ingested_at=t0), table)
    land_raw(to_rows([{"b": 2}], ingested_at=t0), table)
    assert latest_batch(table).height == 2


def test_latest_batch_on_a_missing_table_is_empty(table):
    result = latest_batch(table)
    assert result.is_empty()
    assert dict(result.schema) == BRONZE_SCHEMA


def test_to_records_on_an_empty_frame(table):
    assert to_records(load_raw(table)) == []
