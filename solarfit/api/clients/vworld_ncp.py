"""VWorld 국가중점데이터 API 클라이언트 — PNU 기반 속성 조회."""
import httpx
from typing import Optional
from api.config import VWORLD_API_KEY, VWORLD_DATA_URL, VWORLD_DOMAIN


def _ncp_get(service_id: str, pnu: str) -> list[dict]:
    """PNU 기반 국가중점데이터 속성 조회."""
    if not VWORLD_API_KEY or not pnu:
        return []
    params = {
        "service": "data",
        "request": "GetFeature",
        "data": service_id,
        "key": VWORLD_API_KEY,
        "domain": VWORLD_DOMAIN,
        "format": "json",
        "size": "1",
        "page": "1",
        "geometry": "false",
        "attribute": "true",
        "attrFilter": f"pnu:=:{pnu}",
    }
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


def fetch_land_price(pnu: str) -> Optional[float]:
    """개별공시지가 (원/m²). 없으면 None."""
    features = _ncp_get("LP_PA_CBND_BUBUN", pnu)
    if not features:
        return None
    props = features[0].get("properties", {})
    for field in ("jiga", "pblntfpclnd", "landprice", "publand_prc"):
        val = props.get(field)
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                continue
    return None


def fetch_land_characteristics(pnu: str) -> Optional[dict]:
    """토지특성정보 — 경사도등급, 이용상황, 지목 상세."""
    features = _ncp_get("LP_PA_CBND_BUBUN", pnu)
    if not features:
        return None
    props = features[0].get("properties", {})
    return {
        "slope_grade": props.get("tpgrp_cd"),
        "slope_grade_name": props.get("tpgrp_nm"),
        "land_use_status": props.get("lnusg_cd"),
        "land_use_name": props.get("lnusg_nm"),
        "jimok": props.get("lndcgr_cd"),
        "jimok_name": props.get("lndcgr_nm"),
    }


def fetch_land_ownership(pnu: str) -> Optional[str]:
    """토지소유구분: 개인/법인/국공유/기타."""
    features = _ncp_get("LP_PA_CBND_BUBUN", pnu)
    if not features:
        return None
    props = features[0].get("properties", {})
    code = props.get("ownsh_cd") or props.get("owner_cd")
    if code is None:
        return None
    mapping = {"1": "개인", "2": "법인", "3": "국공유", "4": "기타"}
    return mapping.get(str(code), "기타")


def fetch_land_use_plan(pnu: str) -> Optional[list[str]]:
    """토지이용계획정보 — 해당 필지의 규제 목록 반환."""
    features = _ncp_get("LP_PA_CBND_BUBUN", pnu)
    if not features:
        return None
    props = features[0].get("properties", {})
    restrictions = []
    for field in ("zone1", "zone2", "zone3", "restrict1", "restrict2"):
        val = props.get(field)
        if val and str(val).strip():
            restrictions.append(str(val).strip())
    return restrictions
