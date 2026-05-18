export interface TerrainInfo {
  elevation_m: number | null;
  slope_deg: number | null;
  aspect_deg: number | null;
  is_south_facing: boolean | null;
}

export interface ParcelInfo {
  pnu: string | null;
  jimok: string | null;
  jimok_name: string | null;
  area_m2: number | null;
  address: string | null;
}

export interface LandValueInfo {
  official_price_per_m2: number | null;
  ownership_type: string | null;
  slope_grade: string | null;
}

export interface RegulatoryInfo {
  agri_promotion: boolean;
  agri_unfavorable: boolean;
  natural_conservation: boolean;
  wetland_protection: boolean;
  forest_protection: boolean;
  greenbelt: boolean;
  water_source: boolean;
  wildlife_protection: boolean;
  steep_slope_hazard: boolean;
  disaster_risk: boolean;
}

export interface SubstationInfo {
  name: string | null;
  distance_km: number | null;
  voltage_kv: string | null;
  remaining_kw: string | null;
}

export interface ScoreResult {
  total: number;
  grade: 'A' | 'B' | 'C' | 'D' | 'F';
  passed_hard_filter: boolean;
  breakdown: Record<string, number>;
}

export interface AnalysisResult {
  lat: number;
  lon: number;
  annual_ghi_kwh: number | null;
  terrain: TerrainInfo;
  parcel: ParcelInfo;
  land_value: LandValueInfo;
  regulatory: RegulatoryInfo;
  substation: SubstationInfo;
  score: ScoreResult | null;
}

export interface SearchResult {
  title: string;
  address: string | null;
  lat: number;
  lon: number;
}
