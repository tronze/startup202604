"""좌표 → 전체 분석 오케스트레이터."""
from api.models import (
    AnalysisResult, TerrainInfo, ParcelInfo,
    LandValueInfo, RegulatoryInfo, SubstationInfo,
)
from api.clients.vworld_data import fetch_parcel_at, fetch_regulatory_zones
from api.clients.vworld_ncp import fetch_land_price, fetch_land_characteristics, fetch_land_ownership
from api.clients.nasa_power import fetch_annual_ghi
from api.clients.opentopodata import fetch_elevation_slope
from api.clients.substation import find_nearest_substation
from api.scoring import calculate_score


def analyze(lat: float, lon: float) -> AnalysisResult:
    """좌표 하나에 대해 모든 데이터 수집 후 AnalysisResult 반환."""
    result = AnalysisResult(lat=lat, lon=lon)

    parcel_raw = fetch_parcel_at(lat, lon)
    if parcel_raw:
        result.parcel = ParcelInfo(
            pnu=parcel_raw.get("pnu"),
            jimok=parcel_raw.get("jimok"),
            jimok_name=parcel_raw.get("jimok_name"),
            area_m2=parcel_raw.get("area_m2"),
            address=parcel_raw.get("address"),
        )
        pnu = parcel_raw.get("pnu")
    else:
        pnu = None

    reg_raw = fetch_regulatory_zones(lat, lon)
    result.regulatory = RegulatoryInfo(**reg_raw)

    if pnu:
        price = fetch_land_price(pnu)
        chars = fetch_land_characteristics(pnu)
        ownership = fetch_land_ownership(pnu)
        result.land_value = LandValueInfo(
            official_price_per_m2=price,
            ownership_type=ownership,
            slope_grade=chars.get("slope_grade_name") if chars else None,
        )

    terrain_raw = fetch_elevation_slope(lat, lon)
    if terrain_raw:
        result.terrain = TerrainInfo(**terrain_raw)

    result.annual_ghi_kwh = fetch_annual_ghi(lat, lon)

    sub_raw = find_nearest_substation(lat, lon)
    if sub_raw:
        result.substation = SubstationInfo(**sub_raw)

    result.score = calculate_score(result)

    return result
