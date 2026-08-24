import os

import requests

API_BASE_URL = os.getenv("API_BASE_URL", "https://api.restcountries.com/v1")
API_KEY = os.getenv("API_KEY")


def fetch_countries(fields="name,capital,population,region"):
    """Fetches raw data from the source. Step 1 in the pipeline.

    REST Countries now requires a Bearer key (free "Academic" plan,
    obtained at restcountries.com -> "Get an API key"). The key goes
    in .env locally and as a secret in CI, see README.
    """
    if not API_KEY:
        raise RuntimeError(
            "API_KEY is missing — copy .env.example to .env and fill it in"
        )
    url = f"{API_BASE_URL}/all?fields={fields}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    data = fetch_countries()
    print(f"Fetched {len(data)} records")
