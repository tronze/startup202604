from api.analysis import analyze


def test_analyze_returns_full_result():
    result = analyze(lat=34.57, lon=126.60)
    assert result.lat == 34.57
    assert result.lon == 126.60
    # GHI always available (NASA POWER, no key needed)
    assert result.annual_ghi_kwh is not None
    assert result.terrain.elevation_m is not None
    # Score always computed
    assert result.score is not None
    assert 0 <= result.score.total <= 100
    assert result.score.grade in ("A", "B", "C", "D", "F")
    # Substation always available (CSV)
    assert result.substation.name is not None


def test_analyze_result_has_valid_score_breakdown():
    result = analyze(lat=34.57, lon=126.60)
    for key in ("ghi", "slope", "south_facing", "land_price", "substation", "area"):
        assert key in result.score.breakdown
