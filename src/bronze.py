"""Bronze: land the raw staging payload in a Parquet table.

Each record is stored as its original JSON text in a string column rather
than unpacked into typed columns. Unpacking loses fidelity: an empty
nested object such as {"names": {}} cannot be written to Parquet at all,
and one that does write comes back with its missing fields filled in as
nulls. Parsing belongs in Silver, against a schema Silver declares.

A batch carries a hash of its payload, so re-running the pipeline against
an unchanged source appends nothing instead of duplicating every country.
"""

import hashlib
import json
import os
from datetime import datetime, timezone

import polars as pl

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
)
TABLE_PATH = os.path.join(DATA_DIR, "countries_bronze.parquet")
SOURCE_SYSTEM = "restcountries-v5"

BRONZE_SCHEMA = {
    "ingested_at": pl.Datetime(time_unit="us", time_zone="UTC"),
    "source_system": pl.String,
    "batch_sha256": pl.String,
    "record_index": pl.Int32,
    "raw": pl.String,
}


def _serialise(record):
    """Deterministic JSON, so an unchanged record always hashes the same."""
    return json.dumps(record, ensure_ascii=False, sort_keys=True)


def batch_digest(raw_list):
    """Hash of the whole batch, used to recognise an unchanged source."""
    payload = "\n".join(_serialise(record) for record in raw_list)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def to_rows(raw_list, source_system=SOURCE_SYSTEM, ingested_at=None):
    """Wraps each staging record as a row: payload verbatim, metadata alongside."""
    moment = ingested_at or datetime.now(timezone.utc)
    digest = batch_digest(raw_list)
    return pl.DataFrame(
        {
            "ingested_at": [moment] * len(raw_list),
            "source_system": [source_system] * len(raw_list),
            "batch_sha256": [digest] * len(raw_list),
            "record_index": list(range(len(raw_list))),
            "raw": [_serialise(record) for record in raw_list],
        },
        schema=BRONZE_SCHEMA,
    )


def land_raw(rows, path=TABLE_PATH):
    """Appends a batch unless it matches the most recent one. Returns rows added.

    Compared against the latest batch only, not all history: if the source
    reverts to an earlier state that is a real change, and latest_batch
    must reflect it.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    existing = load_raw(path)
    if not rows.is_empty() and not existing.is_empty():
        newest = existing.filter(pl.col("ingested_at") == pl.col("ingested_at").max())
        if rows["batch_sha256"][0] == newest["batch_sha256"][0]:
            return 0
    combined = rows if existing.is_empty() else pl.concat([existing, rows])
    temporary = f"{path}.tmp"
    combined.write_parquet(temporary)
    os.replace(temporary, path)
    return rows.height


def load_raw(path=TABLE_PATH):
    """Reads the whole Bronze table."""
    if not os.path.exists(path):
        return pl.DataFrame(schema=BRONZE_SCHEMA)
    return pl.read_parquet(path)


def latest_batch(path=TABLE_PATH):
    """The most recent ingestion only. This is what Silver should read."""
    table = load_raw(path)
    if table.is_empty():
        return table
    return table.filter(pl.col("ingested_at") == pl.col("ingested_at").max()).sort(
        "record_index"
    )


def to_records(rows):
    """Parses the raw column back into the original Python records."""
    return [json.loads(text) for text in rows["raw"].to_list()]
