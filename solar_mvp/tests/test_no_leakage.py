"""Tests to prevent data leakage in ML training."""
import pytest
from solar_mvp.config import FEATURES_V2, FORBIDDEN_FEATURES
from solar_mvp.stage4_6_ml_tune import check_no_leakage


def test_features_v2_no_forbidden():
    """FEATURES_V2 must not contain any FORBIDDEN_FEATURES."""
    overlap = set(FEATURES_V2) & FORBIDDEN_FEATURES
    assert overlap == set(), f"Leakage! Forbidden features in FEATURES_V2: {overlap}"


def test_check_no_leakage_passes_clean_list():
    """check_no_leakage should not raise for clean feature list."""
    clean = ["slope_mean", "aspect_south", "annual_ghi"]
    check_no_leakage(clean)  # should not raise


def test_check_no_leakage_raises_on_forbidden():
    """check_no_leakage must raise ValueError for each forbidden feature."""
    for forbidden in FORBIDDEN_FEATURES:
        with pytest.raises(ValueError, match="DATA LEAKAGE"):
            check_no_leakage(["slope_mean", forbidden])


def test_is_installed_not_in_features():
    """is_installed must not appear in FEATURES_V2 — it's the label."""
    assert "is_installed" not in FEATURES_V2


def test_forbidden_features_are_all_strings():
    """FORBIDDEN_FEATURES should be a set of strings."""
    assert isinstance(FORBIDDEN_FEATURES, (set, frozenset))
    assert all(isinstance(f, str) for f in FORBIDDEN_FEATURES)


def test_features_v2_are_all_strings():
    """FEATURES_V2 should be a list of strings with no duplicates."""
    assert isinstance(FEATURES_V2, list)
    assert len(FEATURES_V2) == len(set(FEATURES_V2)), "Duplicate features in FEATURES_V2"
    assert all(isinstance(f, str) for f in FEATURES_V2)
