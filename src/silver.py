import polars as pl

RECORD_SCHEMA = pl.Struct(
    {
        "names": pl.Struct({"common": pl.Utf8}),
        "codes": pl.Struct({"ccn3": pl.Utf8}),
        "capitals": pl.List(pl.Struct({"name": pl.Utf8})),
        "population": pl.Int64,
        "region": pl.Utf8,
        "continents": pl.List(pl.Utf8),
        "currencies": pl.List(pl.Struct({"code": pl.Utf8})),
    }
)


def transform_all(bronze_rows):
    """Cleans and transforms bronze rows. Step 3 in the pipeline (silver).

    bronze_rows is the DataFrame from bronze.latest_batch(): ingested_at,
    source_system, batch_sha256, record_index, raw (JSON text). raw is
    parsed here against an explicit schema, so types are fixed instead
    of guessed from whatever happens to be in the batch — a batch with
    every capitals list empty would otherwise infer List(Null) and
    crash, which only shows up in small test fixtures, not the real
    254-country batch.
    """
    if bronze_rows.is_empty():
        return pl.DataFrame(
            schema={
                "name": pl.Utf8,
                "capital": pl.Utf8,
                "population": pl.Int64,
                "region": pl.Utf8,
                "continents": pl.List(pl.Utf8),
                "currencies": pl.List(pl.Utf8),
                "ccn3": pl.Utf8,
                "ingested_at": pl.Datetime("us", "UTC"),
                "source_system": pl.Utf8,
            }
        )

    df = bronze_rows.select(
        "ingested_at",
        "source_system",
        pl.col("raw").str.json_decode(RECORD_SCHEMA).alias("parsed"),
    ).unnest("parsed")

    df = df.filter(
        pl.col("names").struct.field("common").is_not_null()
        & (pl.col("names").struct.field("common") != "")
    )

    df = df.with_columns(
        pl.col("names").struct.field("common").str.strip_chars().alias("name"),
        pl.col("capitals").list.first().struct.field("name").alias("capital"),
        pl.col("population").fill_null(0).alias("population"),
        pl.col("region").fill_null("Unknown").alias("region"),
        pl.col("continents").fill_null([]).alias("continents"),
        pl.col("currencies")
        .list.eval(pl.element().struct.field("code"))
        .list.drop_nulls()
        .alias("currencies"),
        pl.col("codes").struct.field("ccn3").replace("", None).alias("ccn3"),
    )

    return df.select(
        [
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
    )
