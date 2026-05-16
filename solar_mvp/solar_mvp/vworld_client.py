"""VWorld API client with retry and disk caching."""
import json
import hashlib
import logging
import time
from pathlib import Path

import requests

from solar_mvp.config import CACHE_DIR, VWORLD_BASE_URL, VWORLD_WFS_URL

logger = logging.getLogger(__name__)

# Layer name constants
LAYER_PARCEL = "lp_pa_cbnd_bubun"        # 연속지적도 (필지)
LAYER_LAND_USE = "ud_wd_ngout_pcel_ma"   # 토지이용계획
LAYER_BUILDING = "lp_pa_cbnd_bonbun"     # 건물 (simplified)
LAYER_ROAD = "lt_c_lanl"                 # 도로중심선
LAYER_SIGUNGU = "lt_c_adsido_c"          # 시군구 경계

_EMPTY_GEOJSON = {
    "type": "FeatureCollection",
    "features": [],
}


class VWorldClient:
    """Thin wrapper around the VWorld REST / WFS API with disk cache and retry."""

    def __init__(self, api_key: str, cache_dir: Path = CACHE_DIR / "vworld"):
        if not api_key:
            raise ValueError("VWORLD_API_KEY must not be empty.")
        self.api_key = api_key
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _cache_path(self, url: str, params: dict) -> Path:
        """SHA-256 of (url, sorted params) → cache/<hash>.json"""
        key = json.dumps({"url": url, "params": sorted(params.items())}, sort_keys=True)
        digest = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def _get(self, url: str, params: dict, timeout: int = 30) -> dict:
        """GET with disk cache and 3-retry exponential backoff."""
        cache_file = self._cache_path(url, params)
        if cache_file.exists():
            logger.debug("Cache hit: %s", cache_file.name)
            with cache_file.open("r", encoding="utf-8") as f:
                return json.load(f)

        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                resp = self.session.get(url, params=params, timeout=timeout)
                if resp.status_code >= 500:
                    raise requests.HTTPError(
                        f"Server error {resp.status_code}", response=resp
                    )
                resp.raise_for_status()
                data = resp.json()
                with cache_file.open("w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False)
                return data
            except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as exc:
                last_exc = exc
                wait = 2 ** attempt
                logger.warning(
                    "VWorld request failed (attempt %d/3): %s — retrying in %ds",
                    attempt + 1,
                    exc,
                    wait,
                )
                time.sleep(wait)

        raise RuntimeError(
            f"VWorld API unreachable after 3 attempts: {last_exc}"
        ) from last_exc

    # ------------------------------------------------------------------
    # WFS helper
    # ------------------------------------------------------------------

    def _wfs_get_feature(
        self,
        type_name: str,
        cql_filter: str,
        page: int = 1,
        per_page: int = 1000,
    ) -> dict:
        """Generic WFS GetFeature returning GeoJSON FeatureCollection."""
        start_index = (page - 1) * per_page
        params = {
            "SERVICE": "WFS",
            "VERSION": "2.0.0",
            "REQUEST": "GetFeature",
            "TYPENAME": type_name,
            "OUTPUT": "application/json",
            "SRSNAME": "EPSG:4326",
            "COUNT": str(per_page),
            "STARTINDEX": str(start_index),
            "CQL_FILTER": cql_filter,
            "KEY": self.api_key,
        }
        try:
            raw = self._get(VWORLD_WFS_URL, params)
        except Exception as exc:
            logger.warning(
                "WFS GetFeature failed for layer %s: %s — returning empty FeatureCollection",
                type_name,
                exc,
            )
            return dict(_EMPTY_GEOJSON)

        # VWorld sometimes wraps in {"response": ...} or returns GeoJSON directly
        if isinstance(raw, dict):
            if raw.get("type") == "FeatureCollection":
                return raw
            # Try to unwrap nested response
            for candidate in ("response", "result", "features"):
                if candidate in raw:
                    inner = raw[candidate]
                    if isinstance(inner, dict) and inner.get("type") == "FeatureCollection":
                        return inner
                    if candidate == "features" and isinstance(inner, list):
                        return {"type": "FeatureCollection", "features": inner}

        logger.warning(
            "Unexpected WFS response structure for layer %s — returning empty FeatureCollection",
            type_name,
        )
        return dict(_EMPTY_GEOJSON)

    @staticmethod
    def _bbox_to_polygon_wkt(bbox: tuple[float, float, float, float]) -> str:
        """(minx, miny, maxx, maxy) → POLYGON((...)) WKT string."""
        minx, miny, maxx, maxy = bbox
        return (
            f"POLYGON(({minx} {miny}, {maxx} {miny}, "
            f"{maxx} {maxy}, {minx} {maxy}, {minx} {miny}))"
        )

    @staticmethod
    def _bbox_to_cql(bbox: tuple[float, float, float, float]) -> str:
        return f"INTERSECTS(geometry,{VWorldClient._bbox_to_polygon_wkt(bbox)})"

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def get_parcel_features(self, pnu: str) -> dict:
        """Single parcel by PNU from VWorld data API."""
        params = {
            "service": "data",
            "request": "GetFeature",
            "data": "LT_C_LPLBUBUN",
            "key": self.api_key,
            "format": "json",
            "size": "1",
            "page": "1",
            "attrfilter": f"pnu:=:{pnu}",
        }
        try:
            return self._get(f"{VWORLD_BASE_URL}/data", params)
        except Exception as exc:
            logger.warning("get_parcel_features(%s) failed: %s", pnu, exc)
            return {}

    def get_parcels_by_bbox(
        self,
        bbox: tuple[float, float, float, float],
        page: int = 1,
        per_page: int = 1000,
    ) -> dict:
        """WFS GetFeature for 연속지적도 layer filtered to bbox, returns GeoJSON dict."""
        cql = self._bbox_to_cql(bbox)
        return self._wfs_get_feature(LAYER_PARCEL, cql, page=page, per_page=per_page)

    def get_land_use_plan(self, bbox: tuple) -> dict:
        """토지이용계획 layer for bbox."""
        cql = self._bbox_to_cql(bbox)
        return self._wfs_get_feature(LAYER_LAND_USE, cql)

    def get_buildings(self, bbox: tuple) -> dict:
        """건물통합정보 layer for bbox."""
        cql = self._bbox_to_cql(bbox)
        return self._wfs_get_feature(LAYER_BUILDING, cql)

    def get_roads(self, bbox: tuple) -> dict:
        """도로중심선 layer for bbox."""
        cql = self._bbox_to_cql(bbox)
        return self._wfs_get_feature(LAYER_ROAD, cql)

    def get_admin_boundary(self, sigungu_code: str) -> dict:
        """시군구 경계 polygon for given code."""
        params = {
            "service": "data",
            "request": "GetFeature",
            "data": "LT_C_ADSIGG_INFO",
            "key": self.api_key,
            "format": "json",
            "size": "1",
            "page": "1",
            "attrfilter": f"sig_cd:=:{sigungu_code}",
        }
        try:
            raw = self._get(f"{VWORLD_BASE_URL}/data", params)
        except Exception as exc:
            logger.warning(
                "get_admin_boundary(%s) failed: %s — returning empty FeatureCollection",
                sigungu_code,
                exc,
            )
            return dict(_EMPTY_GEOJSON)

        # Normalise to GeoJSON FeatureCollection
        if isinstance(raw, dict):
            if raw.get("type") == "FeatureCollection":
                return raw
            # VWorld data API wraps result in response.result.featureCollection
            try:
                fc = raw["response"]["result"]["featureCollection"]
                if isinstance(fc, dict):
                    return fc
            except (KeyError, TypeError):
                pass
            # Try common alternative paths
            for path in [["result", "featureCollection"], ["featureCollection"]]:
                node = raw
                for key in path:
                    node = node.get(key, {}) if isinstance(node, dict) else {}
                if isinstance(node, dict) and node.get("type") == "FeatureCollection":
                    return node

        logger.warning(
            "Could not parse admin boundary response for %s — returning empty FeatureCollection",
            sigungu_code,
        )
        return dict(_EMPTY_GEOJSON)

    def reverse_geocode(self, lon: float, lat: float) -> dict | None:
        """Reverse geocode WGS84 coords → address + PNU if available."""
        params = {
            "service": "address",
            "request": "getAddress",
            "key": self.api_key,
            "format": "json",
            "type": "both",
            "point": f"{lon},{lat}",
        }
        try:
            raw = self._get(f"{VWORLD_BASE_URL}/address", params)
        except Exception as exc:
            logger.warning("reverse_geocode(%.6f, %.6f) failed: %s", lon, lat, exc)
            return None

        if not isinstance(raw, dict):
            return None

        try:
            status = (
                raw.get("response", {}).get("status")
                or raw.get("status")
            )
            if status and str(status).upper() not in ("OK", "200"):
                return None
            result = raw.get("response", {}).get("result", raw.get("result"))
            return result if result else None
        except Exception:
            return None
