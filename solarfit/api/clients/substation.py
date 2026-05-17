"""한전 변전소 데이터 로더 + Haversine 최근접 계산."""
import math
import csv
from pathlib import Path
from typing import Optional
from api.config import SUBSTATIONS_CSV


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 지점 간 거리를 Haversine 공식으로 계산 (km)."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _load_substations() -> list[dict]:
    """CSV에서 변전소 데이터 로드."""
    path = Path(SUBSTATIONS_CSV)
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


_SUBSTATIONS: list[dict] = _load_substations()


def find_nearest_substation(lat: float, lon: float) -> Optional[dict]:
    """가장 가까운 변전소와 거리(km) 반환."""
    if not _SUBSTATIONS:
        return None
    best = None
    best_dist = float("inf")
    for row in _SUBSTATIONS:
        try:
            d = _haversine_km(lat, lon, float(row["lat"]), float(row["lon"]))
            if d < best_dist:
                best_dist = d
                best = row
        except (ValueError, KeyError):
            continue
    if best is None:
        return None
    return {
        "name": best["name"],
        "distance_km": round(best_dist, 2),
        "voltage_kv": best.get("voltage_kv"),
        "remaining_kw": best.get("remaining_kw"),
    }
