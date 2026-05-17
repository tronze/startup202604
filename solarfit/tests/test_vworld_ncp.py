import pytest
from api.clients.vworld_ncp import (
    fetch_land_price,
    fetch_land_characteristics,
    fetch_land_ownership,
    fetch_land_use_plan,
)

SAMPLE_PNU = "4684025021100010000"  # 해남군 샘플 PNU


def test_land_price_returns_number_or_none():
    result = fetch_land_price(SAMPLE_PNU)
    # Without API key → None; with key → positive float or None if not found
    assert result is None or (isinstance(result, float) and result > 0)


def test_land_characteristics_returns_dict_or_none():
    result = fetch_land_characteristics(SAMPLE_PNU)
    assert result is None or isinstance(result, dict)
    if isinstance(result, dict):
        assert "slope_grade" in result
        assert "land_use_status" in result
        assert "jimok" in result


def test_land_ownership_returns_valid_type_or_none():
    result = fetch_land_ownership(SAMPLE_PNU)
    assert result is None or result in ("개인", "법인", "국공유", "기타")


def test_land_use_plan_returns_list_or_none():
    result = fetch_land_use_plan(SAMPLE_PNU)
    assert result is None or isinstance(result, list)


def test_functions_handle_empty_pnu():
    # Empty PNU should not crash
    assert fetch_land_price("") is None
    assert fetch_land_characteristics("") is None
    assert fetch_land_ownership("") is None
    assert fetch_land_use_plan("") is None
