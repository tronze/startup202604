"""OpenTopoData SRTM 90m — 고도 + 인접 격자 경사도 계산."""
import httpx
import math
from typing import Optional
from api.config import OPENTOPODATA_URL


def fetch_elevation_slope(lat: float, lon: float) -> Optional[dict]:
    """
    고도(m)와 인접 4개 격자에서 경사도(°) 계산.
    SRTM 90m 해상도 = ~0.0009° 간격.
    """
    d = 0.0009  # ~90m at Korean latitudes
    points = [
        (lat, lon),        # 중심
        (lat + d, lon),    # 북
        (lat - d, lon),    # 남
        (lat, lon + d),    # 동
        (lat, lon - d),    # 서
    ]
    locations = "|".join(f"{la},{lo}" for la, lo in points)
    try:
        r = httpx.get(
            OPENTOPODATA_URL,
            params={"locations": locations},
            timeout=20,
        )
        r.raise_for_status()
        results = r.json().get("results", [])
        if len(results) < 5:
            return None
        elevs = [float(res.get("elevation") or 0.0) for res in results]
        elev_c, elev_n, elev_s, elev_e, elev_w = elevs

        dist_m = 90.0
        dz_ns = (elev_n - elev_s) / (2 * dist_m)
        dz_ew = (elev_e - elev_w) / (2 * dist_m)
        slope_rad = math.atan(math.sqrt(dz_ns ** 2 + dz_ew ** 2))
        slope_deg = round(math.degrees(slope_rad), 2)

        aspect_rad = math.atan2(-dz_ns, dz_ew)
        aspect_deg = round(math.degrees(aspect_rad) % 360, 1)

        return {
            "elevation_m": round(elev_c, 1),
            "slope_deg": slope_deg,
            "aspect_deg": aspect_deg,
            "is_south_facing": aspect_deg < 90 or aspect_deg > 270,
        }
    except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError, ValueError, KeyError):
        return None
