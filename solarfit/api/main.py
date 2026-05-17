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
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
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


@app.get("/api/search")
def search_address(q: str = Query(..., description="주소 또는 장소명")):
    """VWorld 검색 API — 주소 → 좌표."""
    if not VWORLD_API_KEY:
        return {"results": []}
    params = {
        "service": "search",
        "request": "search",
        "key": VWORLD_API_KEY,
        "query": q,
        "type": "ADDRESS",
        "format": "json",
        "size": "5",
        "crs": "EPSG:4326",
    }
    try:
        r = httpx.get(VWORLD_SEARCH_URL, params=params, timeout=10)
        r.raise_for_status()
        body = r.json()
        items = body.get("response", {}).get("result", {}).get("items", [])
        return {
            "results": [
                {
                    "title": item.get("title"),
                    "address": (
                        item.get("address", {}).get("road")
                        or item.get("address", {}).get("parcel")
                    ),
                    "lat": float(item.get("point", {}).get("y", 0)),
                    "lon": float(item.get("point", {}).get("x", 0)),
                }
                for item in items
            ]
        }
    except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError, ValueError, KeyError) as e:
        raise HTTPException(status_code=502, detail=f"VWorld search error: {e}")
