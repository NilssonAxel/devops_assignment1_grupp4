"""Unit tests for staging.

The network is stubbed out, so these need no API key and no connectivity.
They test our own logic: the pagination loop, the auth header, and the
guards that stop a bad response from landing as if it were good.
"""

import pytest
import requests

from src import staging


class FakeResponse:
    """Stands in for a requests.Response, without touching the network."""

    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")


def _page(objects, more, total=None):
    """Builds one page of the v5 response envelope."""
    meta = {"more": more}
    if total is not None:
        meta["total"] = total
    return {"data": {"objects": objects, "meta": meta}}


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setattr(staging, "API_KEY", "test-key")


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.setattr(staging, "API_KEY", None)
    with pytest.raises(RuntimeError, match="API_KEY is missing"):
        staging.fetch_countries()


def test_single_page_returns_records(monkeypatch):
    monkeypatch.setattr(
        staging.requests,
        "get",
        lambda *a, **k: FakeResponse(_page([{"n": 1}, {"n": 2}], more=False, total=2)),
    )
    assert staging.fetch_countries() == [{"n": 1}, {"n": 2}]


def test_pagination_collects_every_page(monkeypatch):
    pages = [
        _page([{"n": i} for i in range(100)], more=True, total=254),
        _page([{"n": i} for i in range(100, 200)], more=True),
        _page([{"n": i} for i in range(200, 254)], more=False),
    ]
    seen_offsets = []

    def fake_get(url, headers=None, params=None, timeout=None):
        seen_offsets.append(params["offset"])
        return FakeResponse(pages[len(seen_offsets) - 1])

    monkeypatch.setattr(staging.requests, "get", fake_get)
    assert len(staging.fetch_countries()) == 254
    assert seen_offsets == [0, 100, 200], "offset must advance by the page size"


def test_sends_bearer_token(monkeypatch):
    monkeypatch.setattr(staging, "API_KEY", "secret-123")
    captured = {}

    def fake_get(url, headers=None, params=None, timeout=None):
        captured.update(headers)
        return FakeResponse(_page([{"n": 1}], more=False))

    monkeypatch.setattr(staging.requests, "get", fake_get)
    staging.fetch_countries()
    assert captured["Authorization"] == "Bearer secret-123"


def test_http_error_propagates(monkeypatch):
    monkeypatch.setattr(
        staging.requests, "get", lambda *a, **k: FakeResponse({}, status=401)
    )
    with pytest.raises(requests.HTTPError):
        staging.fetch_countries()


def test_error_envelope_with_http_200_is_rejected(monkeypatch):
    """The deprecated-endpoint case: HTTP 200 but the body carries no data."""
    monkeypatch.setattr(
        staging.requests,
        "get",
        lambda *a, **k: FakeResponse(
            {"success": False, "data": None, "errors": [{"message": "deprecated"}]}
        ),
    )
    with pytest.raises(RuntimeError, match="API returned no data"):
        staging.fetch_countries()


def test_zero_records_is_rejected(monkeypatch):
    """An empty result would otherwise surface as an empty Gold table."""
    monkeypatch.setattr(
        staging.requests, "get", lambda *a, **k: FakeResponse(_page([], more=False))
    )
    with pytest.raises(RuntimeError, match="zero records"):
        staging.fetch_countries()


def test_truncated_fetch_is_rejected(monkeypatch):
    """The API says it holds 254; stopping at 2 must not pass as complete."""
    monkeypatch.setattr(
        staging.requests,
        "get",
        lambda *a, **k: FakeResponse(
            _page([{"n": 1}, {"n": 2}], more=False, total=254)
        ),
    )
    with pytest.raises(
        RuntimeError, match="Fetched 2 records but the API reported 254"
    ):
        staging.fetch_countries()


def test_runaway_pagination_stops(monkeypatch):
    """A source stuck on more=true must not loop forever."""
    calls = []

    def fake_get(url, headers=None, params=None, timeout=None):
        calls.append(1)
        return FakeResponse(_page([{"n": 1}], more=True))

    monkeypatch.setattr(staging.requests, "get", fake_get)
    with pytest.raises(RuntimeError, match="Stopped after"):
        staging.fetch_countries()
    assert len(calls) == staging.MAX_PAGES


def test_missing_total_in_meta_is_tolerated(monkeypatch):
    """The completeness check only applies when the API reports a total."""
    monkeypatch.setattr(
        staging.requests,
        "get",
        lambda *a, **k: FakeResponse(_page([{"n": 1}], more=False)),
    )
    assert staging.fetch_countries() == [{"n": 1}]
