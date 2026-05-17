"""Stage 0: VWorld WFS에서 필요 공간 데이터 자동 다운로드.

다운로드 대상:
  roads.geojson           — 도로명주소도로 (lt_l_sprd) — 도로폭 road_bt 포함
  buildings.geojson       — 도로명주소건물 (lt_c_spbd)
  agri_promotion.geojson  — 농업진흥구역 (lt_c_agrixue101 + agrixue102)
  protected/natural_conservation.geojson  — 자연환경보전지역 (lt_c_uq114)
  protected/wetland.geojson               — 습지보호지역 (lt_c_um901)

필수: VWORLD_API_KEY 환경변수

실행:
    python -m solar_mvp.stage0_download
    python -m solar_mvp.stage0_download --force   # 기존 파일 덮어쓰기
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import shape

from solar_mvp.config import CRS_WGS84, DATA_DIR, VWORLD_WFS_URL

logger = logging.getLogger(__name__)

# 해남군 바운딩박스
HAENAM_BBOX = (126.25, 34.30, 126.90, 34.75)  # (minx, miny, maxx, maxy)
TILE_DEG = 0.1  # 0.1° × 0.1° 타일 분할 (각 타일 ≤ 2000 features 보장)

DOWNLOAD_TARGETS: list[dict] = [
    {
        "name": "roads",
        "layers": ["lt_l_sprd"],
        "output": DATA_DIR / "roads.geojson",
        "description": "도로명주소도로 (도로폭 road_bt 포함)",
        "tile": True,
    },
    {
        "name": "buildings",
        "layers": ["lt_c_spbd"],
        "output": DATA_DIR / "buildings.geojson",
        "description": "도로명주소건물 (주거 이격 필터용)",
        "tile": True,
    },
    {
        "name": "agri_promotion",
        "layers": ["lt_c_agrixue101", "lt_c_agrixue102"],
        "output": DATA_DIR / "agri_promotion.geojson",
        "description": "농업진흥구역 + 농업보호구역 (하드필터)",
        "tile": True,
    },
    {
        "name": "protected_natural",
        "layers": ["lt_c_uq114"],
        "output": DATA_DIR / "protected" / "natural_conservation.geojson",
        "description": "자연환경보전지역 (하드필터)",
        "tile": True,
    },
    {
        "name": "protected_wetland",
        "layers": ["lt_c_um901"],
        "output": DATA_DIR / "protected" / "wetland.geojson",
        "description": "습지보호지역 (하드필터)",
        "tile": False,
    },
]

_SESSION = requests.Session()
_SESSION.headers.update({"Accept": "application/json, application/xml"})


# ---------------------------------------------------------------------------
# 타일 분할
# ---------------------------------------------------------------------------

def _make_tiles(bbox: tuple, tile_deg: float = TILE_DEG) -> list[tuple]:
    minx, miny, maxx, maxy = bbox
    tiles = []
    x = minx
    while x < maxx:
        y = miny
        while y < maxy:
            tiles.append((x, y, min(x + tile_deg, maxx), min(y + tile_deg, maxy)))
            y += tile_deg
        x += tile_deg
    return tiles


def _tile_to_cql(tile: tuple) -> str:
    minx, miny, maxx, maxy = tile
    return (
        f"INTERSECTS(geometry,POLYGON(("
        f"{minx} {miny},{maxx} {miny},{maxx} {maxy},{minx} {maxy},{minx} {miny}"
        f")))"
    )


# ---------------------------------------------------------------------------
# WFS 요청
# ---------------------------------------------------------------------------

def _wfs_get_features(layer: str, cql: str, api_key: str, start_index: int = 0) -> list[dict]:
    """WFS GetFeature 요청. features 리스트 반환 (실패 시 빈 리스트)."""
    params = {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "TYPENAME": layer,
        "CQL_FILTER": cql,
        "outputFormat": "application/json",
        "SRSNAME": "EPSG:4326",
        "COUNT": "1000",
        "STARTINDEX": str(start_index),
        "key": api_key,
    }
    for attempt in range(3):
        try:
            r = _SESSION.get(VWORLD_WFS_URL, params=params, timeout=30)
            if not r.content:
                return []
            data = r.json()
            if data.get("type") == "FeatureCollection":
                return data.get("features", [])
            return []
        except Exception as exc:
            if attempt == 2:
                logger.warning("WFS %s STARTINDEX=%d 실패: %s", layer, start_index, exc)
                return []
            time.sleep(2 ** attempt)
    return []


# ---------------------------------------------------------------------------
# 레이어 전체 수집 (타일 방식 또는 단일 bbox)
# ---------------------------------------------------------------------------

def _fetch_layer(layer: str, bbox: tuple, api_key: str, tile: bool) -> list[dict]:
    """해당 레이어의 모든 features 수집. 타일 방식 또는 단일 bbox."""
    all_features: dict[str, dict] = {}

    if tile:
        tiles = _make_tiles(bbox)
        logger.info("  %s: %d 타일 처리 중", layer, len(tiles))
        for i, t in enumerate(tiles, 1):
            cql = _tile_to_cql(t)
            for start in (0, 1000):
                feats = _wfs_get_features(layer, cql, api_key, start)
                for f in feats:
                    key = _feature_key(f)
                    all_features[key] = f
                if len(feats) < 1000:
                    break
    else:
        cql = _tile_to_cql(bbox)
        for start in (0, 1000):
            feats = _wfs_get_features(layer, cql, api_key, start)
            for f in feats:
                key = _feature_key(f)
                all_features[key] = f
            if len(feats) < 1000:
                break

    return list(all_features.values())


def _feature_key(feature: dict) -> str:
    """중복 제거용 키. PNU > 고유ID > geometry 해시 순으로 사용."""
    props = feature.get("properties") or {}
    for col in ("pnu", "pk", "bd_mgt_sn", "mnum", "link_id", "rn_cd"):
        if props.get(col):
            return f"{col}:{props[col]}"
    geom = feature.get("geometry")
    if geom:
        return str(geom)[:120]
    return str(props)[:120]


# ---------------------------------------------------------------------------
# GeoDataFrame 변환 + 저장
# ---------------------------------------------------------------------------

def _to_gdf(features: list[dict]) -> gpd.GeoDataFrame:
    if not features:
        return gpd.GeoDataFrame(geometry=[], crs=CRS_WGS84)
    rows = []
    for f in features:
        props = dict(f.get("properties") or {})
        geom_raw = f.get("geometry")
        try:
            geom = shape(geom_raw) if geom_raw else None
        except Exception:
            geom = None
        props["geometry"] = geom
        rows.append(props)
    gdf = gpd.GeoDataFrame(rows, crs=CRS_WGS84)
    gdf = gdf[gdf.geometry.notna() & gdf.geometry.is_valid]
    return gdf


def _save_geojson(gdf: gpd.GeoDataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(path, driver="GeoJSON")
    size_kb = path.stat().st_size // 1024
    logger.info("  저장: %s (%d features, %d KB)", path, len(gdf), size_kb)


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def download_all(force: bool = False) -> dict[str, int]:
    """모든 대상 레이어 다운로드. 반환: {name: feature_count}"""
    api_key = os.environ.get("VWORLD_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError(
            "VWORLD_API_KEY 환경변수가 설정되지 않았습니다.\n"
            "export VWORLD_API_KEY=your_key_here"
        )

    results: dict[str, int] = {}

    for target in DOWNLOAD_TARGETS:
        name = target["name"]
        output: Path = target["output"]
        layers: list[str] = target["layers"]
        tile: bool = target["tile"]

        if output.exists() and not force:
            logger.info("[%s] 이미 존재 — 건너뜀 (--force 로 재다운로드)", name)
            try:
                existing = gpd.read_file(output)
                results[name] = len(existing)
            except Exception:
                results[name] = -1
            continue

        logger.info("[%s] 다운로드 시작: %s", name, target["description"])
        t0 = time.time()

        all_features: dict[str, dict] = {}
        for layer in layers:
            feats = _fetch_layer(layer, HAENAM_BBOX, api_key, tile)
            logger.info("  %s → %d features", layer, len(feats))
            for f in feats:
                k = _feature_key(f)
                all_features[k] = f

        gdf = _to_gdf(list(all_features.values()))
        elapsed = time.time() - t0

        if gdf.empty:
            logger.warning("[%s] 수집된 features 없음 — 빈 파일 저장", name)
        _save_geojson(gdf, output)

        results[name] = len(gdf)
        logger.info("[%s] 완료: %d features, %.1fs", name, len(gdf), elapsed)

    return results


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Stage 0: VWorld WFS에서 공간 참조 데이터 다운로드"
    )
    parser.add_argument("--force", action="store_true", help="기존 파일 덮어쓰기")
    parser.add_argument(
        "--target",
        choices=[t["name"] for t in DOWNLOAD_TARGETS],
        help="특정 대상만 다운로드",
    )
    args = parser.parse_args()

    if args.target:
        original = DOWNLOAD_TARGETS[:]
        DOWNLOAD_TARGETS[:] = [t for t in DOWNLOAD_TARGETS if t["name"] == args.target]

    results = download_all(force=args.force)

    print("\n" + "=" * 60)
    print("  Stage 0 — 다운로드 결과")
    print("=" * 60)
    for name, count in results.items():
        status = "✅" if count > 0 else ("⚠️  빈 파일" if count == 0 else "⏭  스킵")
        print(f"  {status}  {name:20s}: {count:,} features")
    print("=" * 60)
    print()
    print("  다음 단계:")
    print("  python -m solar_mvp.pipeline --start-from 1")
    print()
