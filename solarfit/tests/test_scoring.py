from api.models import (
    AnalysisResult, TerrainInfo, ParcelInfo,
    LandValueInfo, RegulatoryInfo, SubstationInfo,
)
from api.scoring import calculate_score


def _make_ideal() -> AnalysisResult:
    return AnalysisResult(
        lat=34.57, lon=126.60,
        annual_ghi_kwh=1450,
        terrain=TerrainInfo(elevation_m=50, slope_deg=3.0, is_south_facing=True),
        parcel=ParcelInfo(jimok="임야", area_m2=10000),
        land_value=LandValueInfo(official_price_per_m2=5000),
        substation=SubstationInfo(distance_km=2.0),
    )


def test_ideal_site_scores_high():
    result = calculate_score(_make_ideal())
    assert result.total >= 70
    assert result.grade in ("A", "B")
    assert result.passed_hard_filter is True


def test_greenbelt_site_fails_hard_filter():
    r = _make_ideal()
    r.regulatory.greenbelt = True
    result = calculate_score(r)
    assert result.passed_hard_filter is False
    assert result.total <= 20


def test_steep_slope_fails_hard_filter():
    r = _make_ideal()
    r.terrain.slope_deg = 20.0
    result = calculate_score(r)
    assert result.passed_hard_filter is False
    assert result.total <= 20


def test_far_substation_lowers_score():
    close = _make_ideal()
    far = _make_ideal()
    far.substation.distance_km = 15.0
    assert calculate_score(close).total > calculate_score(far).total


def test_grade_ranges():
    r = _make_ideal()
    score = calculate_score(r)
    assert score.grade in ("A", "B", "C", "D", "F")
    total = score.total
    if total >= 80:
        assert score.grade == "A"
    elif total >= 65:
        assert score.grade == "B"
    elif total >= 50:
        assert score.grade == "C"
    elif total >= 35:
        assert score.grade == "D"
    else:
        assert score.grade == "F"


def test_breakdown_has_all_keys():
    score = calculate_score(_make_ideal())
    for key in ("ghi", "slope", "south_facing", "land_price", "substation", "area"):
        assert key in score.breakdown
        assert 0.0 <= score.breakdown[key] <= 100.0
