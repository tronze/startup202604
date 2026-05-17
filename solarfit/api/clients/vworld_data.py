"""VWorld Data API 2.0 클라이언트 — geomFilter=BOX() 방식."""
import httpx
from typing import Optional
from api.config import VWORLD_API_KEY, VWORLD_DATA_URL

_DELTA = 0.001  # ~111m bbox half-width


def _box_filter(lat: float, lon: float, delta: float = _DELTA) -> str:
    return f"BOX({lon-delta},{lat-delta},{lon+delta},{lat+delta})"


def _get(data: str, geom_filter: str, attr_filter: str = "", size: int = 5) -> list[dict]:
    if not VWORLD_API_KEY:
        return []
    params = {
        "service": "data",
        "request": "GetFeature",
        "data": data,
        "key": VWORLD_API_KEY,
        "format": "json",
        "size": str(size),
        "page": "1",
        "geometry": "true",
        "attribute": "true",
        "crs": "EPSG:4326",
        "geomFilter": geom_filter,
    }
    if attr_filter:
        params["attrFilter"] = attr_filter
    try:
        r = httpx.get(VWORLD_DATA_URL, params=params, timeout=10)
        r.raise_for_status()
        body = r.json()
        fc = (
            body.get("response", {})
            .get("result", {})
            .get("featureCollection", {})
        )
        return fc.get("features", [])
    except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError, ValueError, KeyError):
        return []


def fetch_parcel_at(lat: float, lon: float) -> Optional[dict]:
    """좌표에서 가장 가까운 필지 반환 (LP_PA_CBND_BUBUN)."""
    features = _get("LP_PA_CBND_BUBUN", _box_filter(lat, lon))
    if not features:
        return None
    props = features[0].get("properties", {})
    return {
        "pnu": props.get("pnu"),
        "jimok": props.get("jmcode") or props.get("jimok") or props.get("lndcgr_cd"),
        "jimok_name": props.get("jmcode_nm") or props.get("lndcgr_nm"),
        "area_m2": props.get("area") or props.get("lndar"),
        "address": props.get("addr") or props.get("lnm_addrss"),
    }


def fetch_regulatory_zones(lat: float, lon: float) -> dict:
    """규제구역 10종 포함 여부 반환. True = 규제 적용."""
    bbox = _box_filter(lat, lon)

    def hits(layer_id: str) -> bool:
        return len(_get(layer_id, bbox, size=1)) > 0

    return {
        "agri_promotion":       hits("LT_C_AGRIXUE101"),
        "agri_unfavorable":     hits("LT_C_AGRIXUE102"),
        "natural_conservation": hits("LT_C_UQ114"),
        "wetland_protection":   hits("LT_C_UM901"),
        "forest_protection":    hits("LT_C_UF151"),
        "greenbelt":            hits("LT_C_UD801"),
        "water_source":         hits("LT_C_UM710"),
        "wildlife_protection":  hits("LT_C_UM221"),
        "steep_slope_hazard":   hits("LT_C_UP401"),
        "disaster_risk":        hits("LT_C_UP201"),
    }
