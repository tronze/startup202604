"""VWorld Data API 2.0 클라이언트 — geomFilter=BOX() 방식."""
import re
import httpx
from typing import Optional
from api.config import VWORLD_API_KEY, VWORLD_DATA_URL, VWORLD_DOMAIN

_JIMOK: dict[str, str] = {
    "전": "전", "답": "답", "과": "과수원", "목": "목장용지",
    "임": "임야", "광": "광천지", "염": "염전", "대": "대지",
    "공": "공장용지", "학": "학교용지", "주": "주차장",
    "유": "유원지", "종": "종교용지", "사": "사적지",
    "묘": "묘지", "잡": "잡종지", "도": "도로",
    "철": "철도용지", "제": "제방", "하": "하천",
    "구": "구거", "양": "양어장", "수": "수도용지",
    "공원": "공원", "체": "체육용지",
}


def _parse_jimok(jibun: str) -> tuple[str | None, str | None]:
    """'161대' → ('대', '대지') 형태로 지목코드/이름 파싱."""
    m = re.search(r'([가-힣]+)$', jibun or '')
    if not m:
        return None, None
    code = m.group(1)
    return code, _JIMOK.get(code, code)

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
        "domain": VWORLD_DOMAIN,
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
    jimok_code, jimok_name = _parse_jimok(props.get("jibun", ""))
    return {
        "pnu": props.get("pnu"),
        "jimok": jimok_code,
        "jimok_name": jimok_name,
        "area_m2": None,  # LP_PA_CBND_BUBUN 레이어에 면적 필드 없음
        "address": props.get("addr"),
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
