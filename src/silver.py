def clean_country(raw):
    """Cleans and transforms a single record. Step 3 in the pipeline."""
    return {
        "name": raw.get("names", {}).get("common", "").strip(),
        "capital": (raw.get("capitals") or [{}])[0].get("name"),
        "population": raw.get("population", 0),
        "region": raw.get("region", "Unknown"),
    }
 
 
def transform_all(raw_list):
    return [clean_country(item) for item in raw_list if item.get("names", {}).get("common")]