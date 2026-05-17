"""Tests for hard_filter_v2 and score computation."""
import pytest
import pandas as pd
import numpy as np
from solar_mvp.stage4_score import hard_filter_v2, apply_hard_filter, compute_score_rule
from solar_mvp.config import (
    ALLOWED_JIMOK, BLOCKED_USE_ZONES, BLOCKED_OWNER_TYPES,
    MIN_AREA_M2, MAX_SLOPE_DEG, MAX_ELEVATION_M, BLOCKED_FOREST_AGES,
    REQUIRED_KW, HAENAM_RESIDENTIAL_BUFFER_M, FEATURES_V2, WEIGHTS_RULE,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def passing_parcel():
    """A parcel that passes all 13 hard filter conditions."""
    return pd.Series({
        "jimok": "임야",
        "area_m2": 5000.0,
        "slope_mean": 10.0,
        "use_zone": "계획관리지역",
        "intersects_protected_area": False,
        "nearest_building_dist_m": 500.0,
        "owner_type": "사유",
        "has_road_access_3m": True,
        "in_agricultural_promotion_zone": False,
        "substation_remaining_kw": 500.0,
        "forest_age_class": "II",
        "elevation_m": 300.0,
        "aspect_class": "남향",
    })


# ---------------------------------------------------------------------------
# Sanity check: passing_parcel actually passes
# ---------------------------------------------------------------------------

def test_passing_parcel_passes(passing_parcel):
    passes, reason = hard_filter_v2(passing_parcel)
    assert passes is True
    assert reason == "통과"


# ---------------------------------------------------------------------------
# Filter 1: 지목
# ---------------------------------------------------------------------------

def test_filter_jimok_blocked(passing_parcel):
    p = passing_parcel.copy()
    p["jimok"] = "대"  # not in ALLOWED_JIMOK
    passes, reason = hard_filter_v2(p)
    assert passes is False
    assert reason == "지목"


def test_filter_jimok_allowed(passing_parcel):
    for jimok in ALLOWED_JIMOK:
        p = passing_parcel.copy()
        p["jimok"] = jimok
        passes, reason = hard_filter_v2(p)
        assert passes is True, f"jimok={jimok!r} should be allowed but got reason={reason!r}"


# ---------------------------------------------------------------------------
# Filter 2: 면적<1000㎡
# ---------------------------------------------------------------------------

def test_filter_area_too_small(passing_parcel):
    p = passing_parcel.copy()
    p["area_m2"] = 999.0
    passes, reason = hard_filter_v2(p)
    assert passes is False
    assert reason == "면적<1000㎡"


def test_filter_area_exactly_minimum(passing_parcel):
    p = passing_parcel.copy()
    p["area_m2"] = float(MIN_AREA_M2)
    passes, _ = hard_filter_v2(p)
    assert passes is True


def test_filter_area_just_below_minimum(passing_parcel):
    p = passing_parcel.copy()
    p["area_m2"] = float(MIN_AREA_M2) - 0.01
    passes, reason = hard_filter_v2(p)
    assert passes is False
    assert reason == "면적<1000㎡"


# ---------------------------------------------------------------------------
# Filter 3: 경사>15°
# ---------------------------------------------------------------------------

def test_filter_slope_too_steep(passing_parcel):
    p = passing_parcel.copy()
    p["slope_mean"] = 20.0
    passes, reason = hard_filter_v2(p)
    assert passes is False
    assert reason == "경사>15°"


def test_filter_slope_exactly_max(passing_parcel):
    """Slope exactly equal to MAX_SLOPE_DEG should pass (filter is strictly >)."""
    p = passing_parcel.copy()
    p["slope_mean"] = float(MAX_SLOPE_DEG)
    passes, _ = hard_filter_v2(p)
    assert passes is True


def test_filter_slope_just_above_max(passing_parcel):
    p = passing_parcel.copy()
    p["slope_mean"] = float(MAX_SLOPE_DEG) + 0.01
    passes, reason = hard_filter_v2(p)
    assert passes is False
    assert reason == "경사>15°"


# ---------------------------------------------------------------------------
# Filter 4: 용도지역
# ---------------------------------------------------------------------------

def test_filter_use_zone_blocked(passing_parcel):
    for zone in BLOCKED_USE_ZONES:
        p = passing_parcel.copy()
        p["use_zone"] = zone
        passes, reason = hard_filter_v2(p)
        assert passes is False, f"use_zone={zone!r} should be blocked"
        assert reason == "용도지역"


def test_filter_use_zone_allowed(passing_parcel):
    p = passing_parcel.copy()
    p["use_zone"] = "계획관리지역"
    passes, _ = hard_filter_v2(p)
    assert passes is True


# ---------------------------------------------------------------------------
# Filter 5: 보전구역
# ---------------------------------------------------------------------------

def test_filter_protected_area_intersects(passing_parcel):
    p = passing_parcel.copy()
    p["intersects_protected_area"] = True
    passes, reason = hard_filter_v2(p)
    assert passes is False
    assert reason == "보전구역"


def test_filter_protected_area_not_intersecting(passing_parcel):
    p = passing_parcel.copy()
    p["intersects_protected_area"] = False
    passes, _ = hard_filter_v2(p)
    assert passes is True


# ---------------------------------------------------------------------------
# Filter 6: 이격거리
# ---------------------------------------------------------------------------

def test_filter_building_too_close(passing_parcel):
    p = passing_parcel.copy()
    p["nearest_building_dist_m"] = float(HAENAM_RESIDENTIAL_BUFFER_M) - 1.0
    passes, reason = hard_filter_v2(p)
    assert passes is False
    assert reason == "이격거리"


def test_filter_building_exactly_at_buffer(passing_parcel):
    """Distance exactly equal to buffer should pass (filter is strictly <)."""
    p = passing_parcel.copy()
    p["nearest_building_dist_m"] = float(HAENAM_RESIDENTIAL_BUFFER_M)
    passes, _ = hard_filter_v2(p)
    assert passes is True


def test_filter_building_far_enough(passing_parcel):
    p = passing_parcel.copy()
    p["nearest_building_dist_m"] = float(HAENAM_RESIDENTIAL_BUFFER_M) + 1.0
    passes, _ = hard_filter_v2(p)
    assert passes is True


# ---------------------------------------------------------------------------
# Filter 7: 소유구분
# ---------------------------------------------------------------------------

def test_filter_owner_type_blocked(passing_parcel):
    for owner in BLOCKED_OWNER_TYPES:
        p = passing_parcel.copy()
        p["owner_type"] = owner
        passes, reason = hard_filter_v2(p)
        assert passes is False, f"owner_type={owner!r} should be blocked"
        assert reason == "소유구분"


def test_filter_owner_type_private(passing_parcel):
    p = passing_parcel.copy()
    p["owner_type"] = "사유"
    passes, _ = hard_filter_v2(p)
    assert passes is True


# ---------------------------------------------------------------------------
# Filter 8: 현황도로<3m
# ---------------------------------------------------------------------------

def test_filter_no_road_access(passing_parcel):
    p = passing_parcel.copy()
    p["has_road_access_3m"] = False
    passes, reason = hard_filter_v2(p)
    assert passes is False
    assert reason == "현황도로<3m"


def test_filter_has_road_access(passing_parcel):
    p = passing_parcel.copy()
    p["has_road_access_3m"] = True
    passes, _ = hard_filter_v2(p)
    assert passes is True


# ---------------------------------------------------------------------------
# Filter 9: 농업진흥지역
# ---------------------------------------------------------------------------

def test_filter_agricultural_promotion_zone(passing_parcel):
    p = passing_parcel.copy()
    p["in_agricultural_promotion_zone"] = True
    passes, reason = hard_filter_v2(p)
    assert passes is False
    assert reason == "농업진흥지역"


def test_filter_not_agricultural_promotion_zone(passing_parcel):
    p = passing_parcel.copy()
    p["in_agricultural_promotion_zone"] = False
    passes, _ = hard_filter_v2(p)
    assert passes is True


# ---------------------------------------------------------------------------
# Filter 10: 계통포화
# ---------------------------------------------------------------------------

def test_filter_substation_saturated(passing_parcel):
    p = passing_parcel.copy()
    p["substation_remaining_kw"] = float(REQUIRED_KW) - 1.0
    passes, reason = hard_filter_v2(p)
    assert passes is False
    assert reason == "계통포화"


def test_filter_substation_exactly_required(passing_parcel):
    """Remaining kW exactly equal to REQUIRED_KW should pass (filter is strictly <)."""
    p = passing_parcel.copy()
    p["substation_remaining_kw"] = float(REQUIRED_KW)
    passes, _ = hard_filter_v2(p)
    assert passes is True


def test_filter_substation_sufficient(passing_parcel):
    p = passing_parcel.copy()
    p["substation_remaining_kw"] = float(REQUIRED_KW) + 50.0
    passes, _ = hard_filter_v2(p)
    assert passes is True


# ---------------------------------------------------------------------------
# Filter 11: 임상영급
# ---------------------------------------------------------------------------

def test_filter_forest_age_blocked(passing_parcel):
    for age_class in BLOCKED_FOREST_AGES:
        p = passing_parcel.copy()
        p["forest_age_class"] = age_class
        passes, reason = hard_filter_v2(p)
        assert passes is False, f"forest_age_class={age_class!r} should be blocked"
        assert reason == "임상영급"


def test_filter_forest_age_allowed(passing_parcel):
    for allowed_class in ["I", "II", "III"]:
        p = passing_parcel.copy()
        p["forest_age_class"] = allowed_class
        passes, _ = hard_filter_v2(p)
        assert passes is True, f"forest_age_class={allowed_class!r} should be allowed"


# ---------------------------------------------------------------------------
# Filter 12: 고도>600m
# ---------------------------------------------------------------------------

def test_filter_elevation_too_high(passing_parcel):
    p = passing_parcel.copy()
    p["elevation_m"] = 700.0
    passes, reason = hard_filter_v2(p)
    assert passes is False
    assert reason == "고도>600m"


def test_filter_elevation_exactly_max(passing_parcel):
    """Elevation exactly equal to MAX_ELEVATION_M should pass (filter is strictly >)."""
    p = passing_parcel.copy()
    p["elevation_m"] = float(MAX_ELEVATION_M)
    passes, _ = hard_filter_v2(p)
    assert passes is True


def test_filter_elevation_just_above_max(passing_parcel):
    p = passing_parcel.copy()
    p["elevation_m"] = float(MAX_ELEVATION_M) + 0.01
    passes, reason = hard_filter_v2(p)
    assert passes is False
    assert reason == "고도>600m"


# ---------------------------------------------------------------------------
# Filter 13: 북향
# ---------------------------------------------------------------------------

def test_filter_aspect_north(passing_parcel):
    p = passing_parcel.copy()
    p["aspect_class"] = "북향"
    passes, reason = hard_filter_v2(p)
    assert passes is False
    assert reason == "북향"


def test_filter_aspect_south_passes(passing_parcel):
    p = passing_parcel.copy()
    p["aspect_class"] = "남향"
    passes, _ = hard_filter_v2(p)
    assert passes is True


def test_filter_aspect_east_passes(passing_parcel):
    p = passing_parcel.copy()
    p["aspect_class"] = "동향"
    passes, _ = hard_filter_v2(p)
    assert passes is True


# ---------------------------------------------------------------------------
# Vectorized filter
# ---------------------------------------------------------------------------

def test_apply_hard_filter_vectorized():
    """Test vectorized filter produces same results as row-by-row."""
    parcels = pd.DataFrame([
        {
            "jimok": "임야", "area_m2": 5000.0, "slope_mean": 10.0,
            "use_zone": "계획관리지역", "intersects_protected_area": False,
            "nearest_building_dist_m": 500.0, "owner_type": "사유",
            "has_road_access_3m": True, "in_agricultural_promotion_zone": False,
            "substation_remaining_kw": 500.0, "forest_age_class": "II",
            "elevation_m": 300.0, "aspect_class": "남향",
        },
        {
            "jimok": "대", "area_m2": 5000.0, "slope_mean": 10.0,  # fails 지목
            "use_zone": "계획관리지역", "intersects_protected_area": False,
            "nearest_building_dist_m": 500.0, "owner_type": "사유",
            "has_road_access_3m": True, "in_agricultural_promotion_zone": False,
            "substation_remaining_kw": 500.0, "forest_age_class": "II",
            "elevation_m": 300.0, "aspect_class": "남향",
        },
    ])
    result = apply_hard_filter(parcels)
    assert "passes_hard_filter" in result.columns
    assert "dropout_reason" in result.columns
    assert result.loc[0, "passes_hard_filter"] == True
    assert result.loc[1, "passes_hard_filter"] == False
    assert result.loc[1, "dropout_reason"] == "지목"

    # Verify consistency with row-by-row
    for i, row in parcels.iterrows():
        row_result, _ = hard_filter_v2(row)
        assert row_result == result.loc[i, "passes_hard_filter"]


def test_apply_hard_filter_all_pass():
    """All parcels passing should result in all True flags."""
    parcels = pd.DataFrame([
        {
            "jimok": "임야", "area_m2": 5000.0, "slope_mean": 10.0,
            "use_zone": "계획관리지역", "intersects_protected_area": False,
            "nearest_building_dist_m": 500.0, "owner_type": "사유",
            "has_road_access_3m": True, "in_agricultural_promotion_zone": False,
            "substation_remaining_kw": 500.0, "forest_age_class": "II",
            "elevation_m": 300.0, "aspect_class": "남향",
        }
        for _ in range(5)
    ])
    result = apply_hard_filter(parcels)
    assert result["passes_hard_filter"].all()
    assert (result["dropout_reason"] == "통과").all()


def test_apply_hard_filter_first_failure_wins():
    """When a parcel fails multiple filters, dropout_reason is from the first failing filter."""
    parcels = pd.DataFrame([{
        "jimok": "대",             # fails 지목 first
        "area_m2": 50.0,           # also fails 면적<1000㎡
        "slope_mean": 25.0,        # also fails 경사>15°
        "use_zone": "계획관리지역",
        "intersects_protected_area": False,
        "nearest_building_dist_m": 500.0,
        "owner_type": "사유",
        "has_road_access_3m": True,
        "in_agricultural_promotion_zone": False,
        "substation_remaining_kw": 500.0,
        "forest_age_class": "II",
        "elevation_m": 300.0,
        "aspect_class": "남향",
    }])
    result = apply_hard_filter(parcels)
    assert result.loc[0, "passes_hard_filter"] == False
    assert result.loc[0, "dropout_reason"] == "지목"


# ---------------------------------------------------------------------------
# Score normalization
# ---------------------------------------------------------------------------

def test_compute_score_rule_range():
    """Scores for passing parcels should be in [0, 1]."""
    n = 20
    rng = np.random.default_rng(42)
    data = {feat: rng.uniform(0, 100, n) for feat in FEATURES_V2}
    data["passes_hard_filter"] = True  # all pass
    parcels = pd.DataFrame(data)

    scores = compute_score_rule(parcels)
    valid = scores.dropna()
    assert len(valid) == n
    assert (valid >= 0.0).all(), f"Some scores below 0: {valid[valid < 0]}"
    assert (valid <= 1.0).all(), f"Some scores above 1: {valid[valid > 1]}"


def test_compute_score_rule_nan_for_failing():
    """Failing parcels should get NaN score."""
    n = 10
    rng = np.random.default_rng(42)
    data = {feat: rng.uniform(0, 100, n) for feat in FEATURES_V2}
    data["passes_hard_filter"] = [True] * 5 + [False] * 5
    parcels = pd.DataFrame(data)

    scores = compute_score_rule(parcels)
    assert scores.iloc[:5].notna().all(), "Passing parcels should have non-NaN scores"
    assert scores.iloc[5:].isna().all(), "Failing parcels should have NaN scores"


def test_compute_score_rule_all_failing():
    """When all parcels fail, all scores should be NaN."""
    n = 5
    rng = np.random.default_rng(0)
    data = {feat: rng.uniform(0, 100, n) for feat in FEATURES_V2}
    data["passes_hard_filter"] = False
    parcels = pd.DataFrame(data)

    scores = compute_score_rule(parcels)
    assert scores.isna().all()


def test_compute_score_rule_identical_features():
    """When all feature values are identical, score should still be in [0, 1]."""
    n = 5
    data = {feat: [50.0] * n for feat in FEATURES_V2}
    data["passes_hard_filter"] = True
    parcels = pd.DataFrame(data)

    scores = compute_score_rule(parcels)
    valid = scores.dropna()
    assert len(valid) == n
    assert (valid >= 0.0).all()
    assert (valid <= 1.0).all()


def test_compute_score_rule_higher_ghi_is_better():
    """Higher annual_ghi should result in higher score (positive weight)."""
    assert WEIGHTS_RULE.get("annual_ghi", 0) > 0, "annual_ghi weight must be positive for test to be valid"

    base_data = {feat: [50.0, 50.0] for feat in FEATURES_V2}
    base_data["passes_hard_filter"] = [True, True]
    base_data["annual_ghi"] = [10.0, 90.0]  # second row has more sun
    parcels = pd.DataFrame(base_data)

    scores = compute_score_rule(parcels)
    assert scores.iloc[1] > scores.iloc[0], "Higher annual_ghi should yield higher score"
