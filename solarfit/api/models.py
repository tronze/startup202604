from pydantic import BaseModel
from typing import Optional


class TerrainInfo(BaseModel):
    elevation_m: Optional[float] = None
    slope_deg: Optional[float] = None
    aspect_deg: Optional[float] = None
    is_south_facing: Optional[bool] = None


class ParcelInfo(BaseModel):
    pnu: Optional[str] = None
    jimok: Optional[str] = None
    jimok_name: Optional[str] = None
    area_m2: Optional[float] = None
    address: Optional[str] = None


class LandValueInfo(BaseModel):
    official_price_per_m2: Optional[float] = None
    ownership_type: Optional[str] = None
    slope_grade: Optional[str] = None


class RegulatoryInfo(BaseModel):
    agri_promotion: bool = False
    agri_unfavorable: bool = False
    natural_conservation: bool = False
    wetland_protection: bool = False
    forest_protection: bool = False
    greenbelt: bool = False
    water_source: bool = False
    wildlife_protection: bool = False
    steep_slope_hazard: bool = False
    disaster_risk: bool = False

    @property
    def any_blocked(self) -> bool:
        return any([
            self.agri_promotion, self.natural_conservation,
            self.wetland_protection, self.forest_protection,
            self.greenbelt, self.water_source,
            self.steep_slope_hazard, self.disaster_risk,
        ])


class SubstationInfo(BaseModel):
    name: Optional[str] = None
    distance_km: Optional[float] = None
    voltage_kv: Optional[str] = None
    remaining_kw: Optional[str] = None


class ScoreResult(BaseModel):
    total: int
    grade: str
    passed_hard_filter: bool
    breakdown: dict[str, float]


class AnalysisResult(BaseModel):
    lat: float
    lon: float
    annual_ghi_kwh: Optional[float] = None
    terrain: TerrainInfo = TerrainInfo()
    parcel: ParcelInfo = ParcelInfo()
    land_value: LandValueInfo = LandValueInfo()
    regulatory: RegulatoryInfo = RegulatoryInfo()
    substation: SubstationInfo = SubstationInfo()
    score: Optional[ScoreResult] = None
