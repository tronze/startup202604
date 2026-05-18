from api.clients.nasa_power import fetch_annual_ghi
from api.clients.opentopodata import fetch_elevation_slope

def test_nasa_power_haenam():
    result = fetch_annual_ghi(lat=34.57, lon=126.60)
    assert result is not None
    assert 1200 < result < 1700  # 해남 예상 범위 kWh/m²/yr

def test_opentopodata_haenam():
    result = fetch_elevation_slope(lat=34.57, lon=126.60)
    assert result is not None
    assert "elevation_m" in result
    assert "slope_deg" in result
    assert "aspect_deg" in result
    assert "is_south_facing" in result
    assert 0 <= result["elevation_m"] < 1000
    assert 0 <= result["slope_deg"] < 90

def test_fetch_ghi_returns_float_or_none():
    # Invalid coordinates should return None without crashing
    result = fetch_annual_ghi(lat=0.0, lon=0.0)
    assert result is None or isinstance(result, float)

def test_fetch_elevation_returns_none_gracefully():
    # Should not crash even if API is slow
    result = fetch_elevation_slope(lat=34.57, lon=126.60)
    # Just verify structure if not None
    if result is not None:
        assert isinstance(result["elevation_m"], float)
        assert isinstance(result["slope_deg"], float)
        assert isinstance(result["is_south_facing"], bool)
