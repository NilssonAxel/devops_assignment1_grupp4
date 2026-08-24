def summarize(cleaned_list):
    """Compiles the final result. Step 4 in the pipeline."""
    total_population = sum(c["population"] for c in cleaned_list)
    by_region = {}
    for c in cleaned_list:
        by_region.setdefault(c["region"], []).append(c["name"])
    return {
        "total_countries": len(cleaned_list),
        "total_population": total_population,
        "regions": {region: len(names) for region, names in by_region.items()},
    }
