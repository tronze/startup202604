import pytest
from api.clients.vworld_data import fetch_parcel_at, fetch_regulatory_zones


def test_fetch_parcel_returns_dict_or_none():
    # 해남군 임야 지점 (34.57°N, 126.60°E)
    result = fetch_parcel_at(lat=34.57, lon=126.60)
    # Without API key returns None; with key returns dict
    assert result is None or (
        isinstance(result, dict)
        and "jimok" in result
        and "pnu" in result
        and "area_m2" in result
    )


def test_fetch_regulatory_zones_returns_dict():
    result = fetch_regulatory_zones(lat=34.57, lon=126.60)
    assert isinstance(result, dict)
    assert "agri_promotion" in result
    assert "natural_conservation" in result
    assert "greenbelt" in result
    # All values are bool
    assert all(isinstance(v, bool) for v in result.values())


def test_box_filter_format():
    from api.clients.vworld_data import _box_filter
    box = _box_filter(lat=34.57, lon=126.60)
    # Format: BOX(minLon,minLat,maxLon,maxLat)
    assert box.startswith("BOX(")
    assert box.count(",") == 3
