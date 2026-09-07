import os

import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "https://api.restcountries.com/countries/v5")
API_KEY = os.getenv("API_KEY")

PAGE_SIZE = 100
MAX_PAGES = 100
RETRY_ATTEMPTS = 4
BACKOFF_FACTOR = 0.5


def _session():
    """A session that retries transient failures.

    The source drops connections intermittently: one measurement caught
    four successes in six requests, and a full fetch needs three pages,
    so an unattended run fails more often than it succeeds without this.
    Only GET is retried, and only on connection errors, read errors and
    the status codes that mean "try again".
    """
    retry = Retry(
        total=RETRY_ATTEMPTS,
        connect=RETRY_ATTEMPTS,
        read=RETRY_ATTEMPTS,
        backoff_factor=BACKOFF_FACTOR,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def fetch_countries():
    """Fetches raw data from the source. Step 1 in the pipeline.

    REST Countries requires a Bearer key (free "Academic" plan, obtained
    at restcountries.com -> "Get an API key"). The key is read from .env
    locally and from repository secrets in CI, see README.

    Results are paginated. The loop is bounded by MAX_PAGES, and the
    record count is checked against the total the API reports, so a
    truncated fetch fails instead of landing as if it were complete.
    """
    if not API_KEY:
        raise RuntimeError(
            "API_KEY is missing — copy .env.example to .env and fill it in"
        )
    headers = {"Authorization": f"Bearer {API_KEY}"}
    session = _session()
    countries = []
    offset = 0
    reported_total = None

    for _ in range(MAX_PAGES):
        response = session.get(
            API_BASE_URL,
            headers=headers,
            params={"limit": PAGE_SIZE, "offset": offset},
            timeout=10,
        )
        response.raise_for_status()
        body = response.json()

        payload = body.get("data")
        if payload is None:
            raise RuntimeError(f"API returned no data: {body.get('errors') or body}")

        meta = payload.get("meta") or {}
        if reported_total is None:
            reported_total = meta.get("total")
        countries.extend(payload["objects"])

        if not meta.get("more"):
            break
        offset += PAGE_SIZE
    else:
        raise RuntimeError(
            f"Stopped after {MAX_PAGES} pages; the API kept reporting more results"
        )

    if not countries:
        raise RuntimeError("API returned zero records")
    if reported_total is not None and len(countries) != reported_total:
        raise RuntimeError(
            f"Fetched {len(countries)} records but the API reported {reported_total}"
        )
    return countries


if __name__ == "__main__":
    data = fetch_countries()
    print(f"Fetched {len(data)} records")
