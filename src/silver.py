import polars as pl


def transform_all(raw_list):
    """Cleans and transforms the raw records. Step 3 in the pipeline (silver).

    REST Countries v5 nests fields differently from v4: names/capitals
    are objects/lists of objects rather than flat strings, and
    currencies is a list of objects with a "code" field. Records
    without a country name are dropped, matching clean_country().
    """
    df = pl.DataFrame(raw_list)

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
    )

    return df.select(
        ["name", "capital", "population", "region", "continents", "currencies"]
    )