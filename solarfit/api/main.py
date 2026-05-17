"""SolarFit API 서버."""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
from api.analysis import analyze
from api.models import AnalysisResult
from api.config import VWORLD_API_KEY, VWORLD_SEARCH_URL

app = FastAPI(title="SolarFit API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/analyze", response_model=AnalysisResult)
def analyze_location(
    lat: float = Query(..., description="위도 (WGS84)", ge=33.0, le=39.0),
    lon: float = Query(..., description="경도 (WGS84)", ge=124.0, le=132.0),
):
    """좌표 → 태양광 입지 분석 결과."""
    try:
        return analyze(lat=lat, lon=lon)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _vworld_search(q: str, search_type: str, category: str | None = None) -> list[dict]:
    """VWorld 단일 타입 검색 — 결과 없으면 []."""
    base = {
        "service": "search",
        "request": "search",
        "key": VWORLD_API_KEY,
        "query": q,
        "type": search_type,
        "format": "json",
        "size": "5",
        "crs": "EPSG:4326",
    }
    if category:
        base["category"] = category
    r = httpx.get(VWORLD_SEARCH_URL, params=base, timeout=10)
    r.raise_for_status()
    body = r.json()
    if body.get("response", {}).get("status") != "OK":
        return []
    items = body.get("response", {}).get("result", {}).get("items", [])
    results = []
    for item in items:
        addr = item.get("address", {})
        label = addr.get("road") or addr.get("parcel") or ""
        results.append({
            "title": item.get("title") or label,
            "address": label,
            "lat": float(item.get("point", {}).get("y", 0)),
            "lon": float(item.get("point", {}).get("x", 0)),
        })
    return results


@app.get("/api/search")
def search_address(q: str = Query(..., description="주소 또는 장소명")):
    """VWorld 검색 API — 장소명·도로명 주소 → 좌표."""
    if not VWORLD_API_KEY:
        return {"results": []}
    try:
        # 장소명(POI) 검색 — category 불필요
        place_results = _vworld_search(q, "PLACE")
        # 도로명 주소 검색 — category=ROAD 필수
        road_results = _vworld_search(q, "ADDRESS", "ROAD")

        seen: set[tuple] = set()
        merged = []
        for item in place_results + road_results:
            key = (round(item["lat"], 5), round(item["lon"], 5))
            if key not in seen:
                seen.add(key)
                merged.append(item)
            if len(merged) >= 5:
                break

        return {"results": merged}
    except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError, ValueError, KeyError) as e:
        raise HTTPException(status_code=502, detail=f"VWorld search error: {e}")
