"""NASA POWER API — 연간 일사량 (GHI) 조회."""
import httpx
from typing import Optional
from api.config import NASA_POWER_URL


def fetch_annual_ghi(lat: float, lon: float) -> Optional[float]:
    """
    연간 평균 GHI (kWh/m²/yr) 반환.
    20년 기후 평균값. No API key required.
    """
    params = {
        "parameters": "ALLSKY_SFC_SW_DWN",
        "community": "RE",
        "longitude": lon,
        "latitude": lat,
        "format": "JSON",
    }
    try:
        r = httpx.get(NASA_POWER_URL, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        monthly = (
            data.get("properties", {})
            .get("parameter", {})
            .get("ALLSKY_SFC_SW_DWN", {})
        )
        annual = monthly.get("ANN")  # 연평균 kWh/m²/day
        if annual is None:
            return None
        return round(float(annual) * 365, 1)  # → kWh/m²/yr
    except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError, ValueError, KeyError):
        return None
