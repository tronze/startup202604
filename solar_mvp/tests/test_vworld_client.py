"""Tests for VWorldClient — all HTTP mocked with `responses` library."""
import pytest
import responses as resp_mock
from solar_mvp.vworld_client import VWorldClient, LAYER_PARCEL, LAYER_LAND_USE

# Minimal GeoJSON FeatureCollection for mocking
MOCK_FEATURE = {
    "type": "Feature",
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[126.5, 34.5], [126.51, 34.5], [126.51, 34.51], [126.5, 34.51], [126.5, 34.5]]],
    },
    "properties": {"pnu": "4681025021100010001", "jimok": "임야", "area": 5000},
}
MOCK_GEOJSON = {"type": "FeatureCollection", "features": [MOCK_FEATURE]}

BBOX = (126.5, 34.5, 126.6, 34.6)


@pytest.fixture
def client(tmp_path):
    """VWorldClient with a temp cache directory and dummy API key."""
    return VWorldClient(
        api_key="test-key-12345",
        cache_dir=tmp_path / "cache",
        max_age_days=1,
    )


@resp_mock.activate
def test_get_parcels_by_bbox_success(client):
    """Should return GeoJSON FeatureCollection when API responds successfully."""
    resp_mock.add(
        resp_mock.GET,
        "https://api.vworld.kr/req/wfs",
        json=MOCK_GEOJSON,
        status=200,
    )
    result = client.get_parcels_by_bbox(bbox=BBOX)
    assert result["type"] == "FeatureCollection"
    assert "features" in result


@resp_mock.activate
def test_get_caches_response(client, tmp_path):
    """Second call should use cache, not make another HTTP request."""
    resp_mock.add(
        resp_mock.GET,
        "https://api.vworld.kr/req/wfs",
        json=MOCK_GEOJSON,
        status=200,
    )
    # First call — hits the network
    client.get_parcels_by_bbox(bbox=BBOX)
    # Cache should now exist
    cache_files = list((tmp_path / "cache").glob("*.json"))
    assert len(cache_files) > 0, "Cache file should exist after first request"

    # Second call — should NOT make another HTTP request.
    # The `responses` library raises ConnectionError for unregistered requests,
    # so if a second network call were attempted it would fail noisily.
    result = client.get_parcels_by_bbox(bbox=BBOX)
    assert result["type"] == "FeatureCollection"
    # Only one real call should have been made
    assert len(resp_mock.calls) == 1, "Cache hit should not trigger a second HTTP call"


@resp_mock.activate
def test_retry_on_server_error(client, monkeypatch):
    """Should retry up to 3 times on 5xx errors."""
    # Suppress sleep to keep test fast
    monkeypatch.setattr("time.sleep", lambda _: None)

    resp_mock.add(resp_mock.GET, "https://api.vworld.kr/req/wfs", status=500)
    resp_mock.add(resp_mock.GET, "https://api.vworld.kr/req/wfs", status=500)
    resp_mock.add(resp_mock.GET, "https://api.vworld.kr/req/wfs", json=MOCK_GEOJSON, status=200)

    result = client.get_parcels_by_bbox(bbox=BBOX)
    assert result is not None
    assert len(resp_mock.calls) == 3, "Two failures + one success = 3 calls"


@resp_mock.activate
def test_returns_empty_on_persistent_failure(client, monkeypatch):
    """Should return empty GeoJSON after all retries fail."""
    monkeypatch.setattr("time.sleep", lambda _: None)

    for _ in range(3):
        resp_mock.add(resp_mock.GET, "https://api.vworld.kr/req/wfs", status=500)

    result = client.get_parcels_by_bbox(bbox=BBOX)
    assert result["type"] == "FeatureCollection"
    assert result["features"] == []


@resp_mock.activate
def test_api_key_not_in_cache_filename(client, tmp_path):
    """Cached file name must not contain the API key."""
    resp_mock.add(
        resp_mock.GET,
        "https://api.vworld.kr/req/wfs",
        json=MOCK_GEOJSON,
        status=200,
    )
    client.get_parcels_by_bbox(bbox=BBOX)

    cache_files = list((tmp_path / "cache").glob("*.json"))
    assert len(cache_files) > 0, "A cache file must have been written"
    for cf in cache_files:
        assert "test-key" not in cf.name, f"API key leaked into cache filename: {cf.name}"
        content = cf.read_text()
        assert "test-key-12345" not in content, "API key leaked into cache content"


def test_layer_constants_defined():
    """Layer name constants must be non-empty strings."""
    from solar_mvp.vworld_client import (
        LAYER_PARCEL, LAYER_LAND_USE, LAYER_BUILDING, LAYER_ROAD, LAYER_SIGUNGU,
    )
    for name in [LAYER_PARCEL, LAYER_LAND_USE, LAYER_BUILDING, LAYER_ROAD, LAYER_SIGUNGU]:
        assert isinstance(name, str) and len(name) > 0, f"Layer constant must be non-empty string, got {name!r}"


def test_client_rejects_empty_api_key(tmp_path):
    """VWorldClient must raise ValueError if api_key is empty."""
    with pytest.raises(ValueError):
        VWorldClient(api_key="", cache_dir=tmp_path / "cache")


@resp_mock.activate
def test_get_land_use_plan_returns_feature_collection(client):
    """get_land_use_plan should also return a FeatureCollection."""
    resp_mock.add(
        resp_mock.GET,
        "https://api.vworld.kr/req/wfs",
        json=MOCK_GEOJSON,
        status=200,
    )
    result = client.get_land_use_plan(bbox=BBOX)
    assert result["type"] == "FeatureCollection"
