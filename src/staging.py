import os

import requests

API_BASE_URL = os.getenv("API_BASE_URL", "https://api.restcountries.com/countries/v5")
API_KEY = os.getenv("API_KEY")


def fetch_countries():
    """Fetches raw data from the source. Step 1 in the pipeline.

    REST Countries now requires a Bearer key (free "Academic" plan,
    obtained at restcountries.com -> "Get an API key"). The key goes
    in .env locally and as a secret in CI, see README.

    Results are paginated (up to 100 per page on the free plan), so
    this loops until every country has been fetched.
    """
    if not API_KEY:
        raise RuntimeError(
            "API_KEY is missing — copy .env.example to .env and fill it in"
        )
    headers = {"Authorization": f"Bearer {API_KEY}"}
    countries = []
    offset = 0
    limit = 100
    while True:
        response = requests.get(
            API_BASE_URL,
            headers=headers,
            params={"limit": limit, "offset": offset},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()["data"]
        countries.extend(payload["objects"])
        if not payload["meta"]["more"]:
            break
        offset += limit
    return countries


if __name__ == "__main__":
    data = fetch_countries()
    print(f"Fetched {len(data)} records")
