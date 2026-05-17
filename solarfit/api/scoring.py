"""규칙 기반 종합 점수 (0-100) 산출."""
from __future__ import annotations
from api.models import AnalysisResult, ScoreResult

_WEIGHTS: dict[str, float] = {
    "ghi":          0.25,
    "slope":        0.20,
    "south_facing": 0.10,
    "land_price":   0.15,
    "substation":   0.20,
    "area":         0.10,
}


def _ghi_score(ghi: float | None) -> float:
    if ghi is None:
        return 50.0
    return max(0.0, min(100.0, (ghi - 1200) / 3.0))


def _slope_score(slope: float | None) -> float:
    if slope is None:
        return 50.0
    return max(0.0, min(100.0, 100.0 - slope / 15.0 * 100.0))


def _south_facing_score(is_south: bool | None) -> float:
    if is_south is None:
        return 50.0
    return 100.0 if is_south else 0.0


def _price_score(price: float | None) -> float:
    if price is None:
        return 50.0
    return max(0.0, min(100.0, 100.0 - price / 10_000.0))


def _substation_score(dist_km: float | None) -> float:
    if dist_km is None:
        return 30.0
    return max(0.0, min(100.0, 100.0 - (dist_km - 1.0) / 9.0 * 100.0))


def _area_score(area_m2: float | None) -> float:
    if area_m2 is None:
        return 50.0
    return max(0.0, min(100.0, area_m2 / 30_000.0 * 100.0))


def calculate_score(result: AnalysisResult) -> ScoreResult:
    passed = not result.regulatory.any_blocked

    if result.terrain.slope_deg is not None and result.terrain.slope_deg > 15:
        passed = False

    breakdown = {
        "ghi":          _ghi_score(result.annual_ghi_kwh),
        "slope":        _slope_score(result.terrain.slope_deg),
        "south_facing": _south_facing_score(result.terrain.is_south_facing),
        "land_price":   _price_score(result.land_value.official_price_per_m2),
        "substation":   _substation_score(result.substation.distance_km),
        "area":         _area_score(result.parcel.area_m2),
    }

    total = sum(breakdown[k] * _WEIGHTS[k] for k in breakdown)
    if not passed:
        total = min(total, 20.0)

    total_int = round(total)
    grade = (
        "A" if total_int >= 80
        else "B" if total_int >= 65
        else "C" if total_int >= 50
        else "D" if total_int >= 35
        else "F"
    )

    return ScoreResult(
        total=total_int,
        grade=grade,
        passed_hard_filter=passed,
        breakdown=breakdown,
    )
