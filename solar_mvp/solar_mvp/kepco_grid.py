"""한전/계통 데이터 수집 — VWorld 전력시설 WFS + data.go.kr 태양광/변전소 현황.

우선순위:
  변전소: data/substations.csv → VWorld lp_pa_elec_ltfac → data.go.kr → 빈 DataFrame (NaN)
  전력선: VWorld lt_l_clfla → None (fallback: road distance proxy)
  태양광: data.go.kr SOLAR_PLANT_SERVICE_ID → empty DataFrame fallback (0 kW)
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import geopandas as gpd
import requests
from shapely.geometry import Point

from solar_mvp.config import (
    CACHE_DIR,
    CRS_WGS84,
    DATA_GO_KR_BASE_URL,
    SIGUNGU_CODE,
    SOLAR_PLANT_SERVICE_ID,
    VWORLD_WFS_URL,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# VWorld layer names
# ---------------------------------------------------------------------------

LAYER_ELEC_FACILITY = "lp_pa_elec_ltfac"  # 전력수급관련시설 (변전소 포인트)
LAYER_POWER_LINE = "lt_l_clfla"            # 전력선 (배전/송전)

# ---------------------------------------------------------------------------
# 전압 등급 → 용량 추정 (실데이터 없을 때 사용)
# ---------------------------------------------------------------------------

_VOLTAGE_CAPACITY_KW: dict[str, int] = {
    "765kV": 500_000,
    "345kV": 200_000,
    "154kV":  40_000,
    "66kV":   10_000,
    "22.9kV":  5_000,
}
_REMAINING_RATIO = 0.30  # 전체 용량의 30%를 잔여용량으로 가정 (보수적)

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

_SESSION = requests.Session()
_SESSION.headers.update({"Accept": "application/json"})
_CACHE_DIR = CACHE_DIR / "kepco_grid"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _get_json(url: str, params: dict, timeout: int = 20) -> dict | None:
    """GET JSON with simple retry (no disk cache — data changes)."""
    for attempt in range(3):
        try:
            resp = _SESSION.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            if attempt == 2:
                logger.warning("HTTP request failed after 3 attempts: %s — %s", url, exc)
                return None
            time.sleep(2 ** attempt)
    return None


# ---------------------------------------------------------------------------
# 변전소 수집
# ---------------------------------------------------------------------------

def _fetch_substations_vworld(api_key: str) -> pd.DataFrame | None:
    """VWorld WFS lp_pa_elec_ltfac 레이어에서 해남군 변전소 포인트 수집."""
    params = {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "TYPENAME": LAYER_ELEC_FACILITY,
        "CQL_FILTER": f"INTERSECTS(geometry,POLYGON((126.25 34.30,126.90 34.30,126.90 34.75,126.25 34.75,126.25 34.30)))",
        "outputFormat": "application/json",
        "COUNT": "200",
        "key": api_key,
    }
    data = _get_json(VWORLD_WFS_URL, params)
    if not data or data.get("type") != "FeatureCollection":
        return None

    features = data.get("features", [])
    if not features:
        logger.info("VWorld returned 0 features for %s in sigungu %s", LAYER_ELEC_FACILITY, SIGUNGU_CODE)
        return None

    rows = []
    for feat in features:
        props = feat.get("properties", {})
        geom = feat.get("geometry", {})
        coords = geom.get("coordinates", [None, None])
        if not coords or len(coords) < 2:
            continue

        lon, lat = float(coords[0]), float(coords[1])
        name = props.get("fac_nam", props.get("ftr_nam", "변전소"))
        voltage = props.get("vol_val", "154kV")
        capacity_kw = _VOLTAGE_CAPACITY_KW.get(voltage, 5000)
        remaining_kw = int(capacity_kw * _REMAINING_RATIO)

        rows.append({"name": name, "lat": lat, "lon": lon,
                     "remaining_kw": remaining_kw, "voltage": voltage})

    if not rows:
        return None

    df = pd.DataFrame(rows)
    logger.info("VWorld: fetched %d substations for %s", len(df), SIGUNGU_CODE)
    return df


def _fetch_substations_data_go_kr(api_key: str) -> pd.DataFrame | None:
    """data.go.kr 한전 변전소 현황 API.

    서비스ID 15043065 — 한국전력공사_변전소현황.
    columns: substation_name, lat, lon, voltage_class, transformer_capacity_kva
    """
    url = f"{DATA_GO_KR_BASE_URL}/B552584/SubstationService/getSubstationInfo"
    params = {
        "serviceKey": api_key,
        "pageNo": "1",
        "numOfRows": "500",
        "sigunguCd": SIGUNGU_CODE,
        "type": "json",
    }
    data = _get_json(url, params)
    if not data:
        return None

    # Handle both response structures
    items = (
        data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        or data.get("items", [])
        or data.get("data", [])
    )
    if not items:
        return None
    if isinstance(items, dict):
        items = [items]

    rows = []
    for item in items:
        try:
            lat = float(item.get("lat", item.get("latitude", 0)))
            lon = float(item.get("lon", item.get("longitude", 0)))
            if lat == 0 or lon == 0:
                continue
            voltage = str(item.get("voltageClass", item.get("voltage_class", "154kV")))
            capacity_kva = float(item.get("transformerCapacityKva", item.get("capacity_kva", 40000)))
            capacity_kw = capacity_kva * 0.9  # kVA → kW (역률 0.9)
            remaining_kw = int(capacity_kw * _REMAINING_RATIO)
            rows.append({
                "name": item.get("substationName", item.get("name", "변전소")),
                "lat": lat,
                "lon": lon,
                "remaining_kw": remaining_kw,
                "voltage": voltage,
            })
        except (TypeError, ValueError):
            continue

    if not rows:
        return None

    df = pd.DataFrame(rows)
    logger.info("data.go.kr: fetched %d substations", len(df))
    return df


def fetch_substations(
    vworld_key: str | None = None,
    data_go_key: str | None = None,
) -> pd.DataFrame:
    """변전소 데이터 반환.

    Priority: VWorld WFS → data.go.kr → synthetic fallback.
    Returns DataFrame with columns: name, lat, lon, remaining_kw, voltage
    """
    vworld_key = vworld_key or os.environ.get("VWORLD_API_KEY")
    data_go_key = data_go_key or os.environ.get("DATA_GO_KR_KEY")

    if vworld_key:
        df = _fetch_substations_vworld(vworld_key)
        if df is not None and len(df) > 0:
            return df
        logger.warning("VWorld substation fetch returned nothing — trying data.go.kr")

    if data_go_key:
        df = _fetch_substations_data_go_kr(data_go_key)
        if df is not None and len(df) > 0:
            return df
        logger.warning("data.go.kr substation fetch returned nothing")

    logger.warning(
        "REQUIRED: 변전소 데이터 없음 — dist_to_substation_km 및 substation_remaining_kw = NaN\n"
        "  해결 방법:\n"
        "    1) export VWORLD_API_KEY=...  (VWorld WFS lp_pa_elec_ltfac)\n"
        "    2) export DATA_GO_KR_KEY=...  (data.go.kr 한전 변전소 현황)\n"
        "    3) data/substations.csv 직접 작성  (name,lat,lon,remaining_kw,voltage)"
    )
    return pd.DataFrame(columns=["name", "lat", "lon", "remaining_kw", "voltage"])


# ---------------------------------------------------------------------------
# 전력선(배전선로) 수집
# ---------------------------------------------------------------------------

def fetch_powerlines(vworld_key: str | None = None) -> gpd.GeoDataFrame | None:
    """VWorld WFS lt_l_clfla 레이어에서 전력선 LineString 수집.

    Returns GeoDataFrame (EPSG:4326) or None if unavailable.
    None → caller falls back to road-distance proxy for dist_to_powerline_m.
    """
    vworld_key = vworld_key or os.environ.get("VWORLD_API_KEY")
    if not vworld_key:
        logger.info("No VWORLD_API_KEY — powerline data unavailable; using road distance proxy")
        return None

    params = {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "TYPENAME": LAYER_POWER_LINE,
        "CQL_FILTER": "INTERSECTS(geometry,POLYGON((126.25 34.30,126.90 34.30,126.90 34.75,126.25 34.75,126.25 34.30)))",
        "outputFormat": "application/json",
        "COUNT": "1000",
        "key": vworld_key,
    }
    data = _get_json(VWORLD_WFS_URL, params)
    if not data or data.get("type") != "FeatureCollection":
        logger.warning("VWorld powerline layer %s unavailable — using road distance proxy", LAYER_POWER_LINE)
        return None

    features = data.get("features", [])
    if not features:
        logger.info("VWorld returned 0 powerline features — using road distance proxy")
        return None

    try:
        gdf = gpd.GeoDataFrame.from_features(features, crs=CRS_WGS84)
        logger.info("VWorld: fetched %d powerline segments", len(gdf))
        return gdf
    except Exception as exc:
        logger.warning("Failed to parse VWorld powerline GeoJSON: %s", exc)
        return None


# ---------------------------------------------------------------------------
# 기존 태양광 발전소 현황
# ---------------------------------------------------------------------------

def _fetch_solar_data_go_kr(api_key: str, sigungu_code: str) -> pd.DataFrame | None:
    """data.go.kr 전국태양광발전소 표준데이터 (SERVICE_ID 15107742)."""
    url = f"{DATA_GO_KR_BASE_URL}/{SOLAR_PLANT_SERVICE_ID}/kepcoRenewableEnergyService/getSolarPwrSttsInfo"
    params = {
        "serviceKey": api_key,
        "pageNo": "1",
        "numOfRows": "1000",
        "sigunguCd": sigungu_code,
        "type": "json",
    }
    data = _get_json(url, params)
    if not data:
        return None

    items = (
        data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        or data.get("items", [])
        or data.get("data", [])
    )
    if not items:
        return None
    if isinstance(items, dict):
        items = [items]

    rows = []
    for item in items:
        try:
            lat = float(item.get("lat", item.get("latitude", 0)))
            lon = float(item.get("lon", item.get("longitude", 0)))
            cap = float(item.get("instalCapacity", item.get("capacity_kw", item.get("install_capacity_kw", 0))))
            if lat == 0 or lon == 0 or cap <= 0:
                continue
            rows.append({"lat": lat, "lon": lon, "capacity_kw": cap})
        except (TypeError, ValueError):
            continue

    if not rows:
        return None

    df = pd.DataFrame(rows)
    logger.info("data.go.kr: fetched %d existing solar plants in sigungu %s", len(df), sigungu_code)
    return df


def fetch_existing_solar(
    data_go_key: str | None = None,
    sigungu_code: str = SIGUNGU_CODE,
) -> pd.DataFrame:
    """기존 설치 태양광 발전소 현황 반환.

    Returns DataFrame with columns: lat, lon, capacity_kw.
    Empty DataFrame if API unavailable (graceful degradation).
    """
    data_go_key = data_go_key or os.environ.get("DATA_GO_KR_KEY")

    if data_go_key:
        df = _fetch_solar_data_go_kr(data_go_key, sigungu_code)
        if df is not None and len(df) > 0:
            return df
        logger.warning("data.go.kr solar fetch returned nothing — existing_solar_kw_5km will be 0")

    logger.info("No existing solar plant data — existing_solar_kw_5km defaults to 0")
    return pd.DataFrame(columns=["lat", "lon", "capacity_kw"])


# ---------------------------------------------------------------------------
# 반경 R km 내 기존 태양광 용량 합산
# ---------------------------------------------------------------------------

def compute_solar_density(
    parcels_lat: np.ndarray,
    parcels_lon: np.ndarray,
    solar_df: pd.DataFrame,
    radius_km: float = 5.0,
) -> np.ndarray:
    """각 필지 중심에서 반경 radius_km 내 기존 태양광 설치 용량(kW) 합 계산.

    Args:
        parcels_lat / parcels_lon: 필지 중심 WGS84 좌표 (n,)
        solar_df: lat, lon, capacity_kw 컬럼을 가진 DataFrame
        radius_km: 반경 (기본 5 km)

    Returns:
        (n,) array — 각 필지의 반경 내 기존 태양광 총 용량 kW
    """
    n = len(parcels_lat)
    result = np.zeros(n)

    if solar_df.empty:
        return result

    sol_lat = solar_df["lat"].values
    sol_lon = solar_df["lon"].values
    sol_kw = solar_df["capacity_kw"].values

    R = 6371.0
    r_lat1 = np.radians(parcels_lat[:, None])   # (n, 1)
    r_lon1 = np.radians(parcels_lon[:, None])   # (n, 1)
    r_lat2 = np.radians(sol_lat[None, :])       # (1, m)
    r_lon2 = np.radians(sol_lon[None, :])       # (1, m)

    dlat = r_lat2 - r_lat1
    dlon = r_lon2 - r_lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(r_lat1) * np.cos(r_lat2) * np.sin(dlon / 2) ** 2
    dist_km = R * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))  # (n, m)

    within = dist_km <= radius_km  # (n, m) bool
    result = (within * sol_kw[None, :]).sum(axis=1)
    return result
