"""Stage 3: Feature enrichment — adds all FEATURES_V2 and hard-filter columns."""
from __future__ import annotations

import argparse
import logging
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd

warnings.filterwarnings("ignore", message="Geometry is in a geographic CRS", category=UserWarning)

from solar_mvp.config import (
    CRS_ANALYSIS,
    CRS_WGS84,
    DATA_DIR,
    OUTPUT_DIR,
    HAENAM_RESIDENTIAL_BUFFER_M,
    MIN_ROAD_WIDTH_M,
    FEATURES_V2,
    GRID_SATURATION_RADIUS_KM,
    HVLINE_SETBACK_M,
    HV_LINE_SETBACK_DEFAULT_M,
)
from solar_mvp.kepco_grid import (
    fetch_substations,
    fetch_powerlines,
    fetch_existing_solar,
    compute_solar_density,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


JIMOK_LAND_PRICE_KRW: dict[str, int] = {
    "임야":    5_000,
    "전":     25_000,
    "답":     30_000,
    "잡종지": 15_000,
    "목장용지": 8_000,
}
JIMOK_LAND_PRICE_DEFAULT = 10_000

HAENAM_EUP_MYEON = [
    ("해남읍",  34.574, 126.599),
    ("삼산면",  34.657, 126.551),
    ("화산면",  34.631, 126.672),
    ("현산면",  34.573, 126.528),
    ("송지면",  34.452, 126.641),
    ("북평면",  34.492, 126.706),
    ("북일면",  34.534, 126.637),
    ("옥천면",  34.583, 126.653),
    ("계곡면",  34.622, 126.729),
    ("마산면",  34.539, 126.735),
    ("황산면",  34.618, 126.611),
    ("산이면",  34.669, 126.627),
    ("문내면",  34.544, 126.568),
    ("화원면",  34.634, 126.507),
]


# ---------------------------------------------------------------------------
# Helper: haversine distance (vectorised)
# ---------------------------------------------------------------------------

_HAENAM_BBOX_WGS84 = (126.25, 34.30, 126.90, 34.75)  # minx, miny, maxx, maxy


def _gdf_within_area(gdf: gpd.GeoDataFrame, bbox: tuple, tolerance_deg: float = 1.0) -> bool:
    """Return True if gdf has any feature within tolerance_deg of bbox."""
    minx, miny, maxx, maxy = bbox
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    half_diag = ((maxx - minx) ** 2 + (maxy - miny) ** 2) ** 0.5 / 2
    threshold = half_diag + tolerance_deg
    # Use centroids in WGS84 for quick distance check
    g = gdf.to_crs("EPSG:4326") if gdf.crs and gdf.crs.to_epsg() != 4326 else gdf
    centroids = g.geometry.centroid
    dists = ((centroids.x - cx) ** 2 + (centroids.y - cy) ** 2) ** 0.5
    return bool((dists < threshold).any())


def _haversine_km(lat1: np.ndarray, lon1: np.ndarray,
                  lat2: np.ndarray | float, lon2: np.ndarray | float) -> np.ndarray:
    """Vectorized haversine distance in km. All inputs in decimal degrees.

    Computes great-circle distance between points.
    - lat1, lon1: arrays or scalars (source points)
    - lat2, lon2: arrays or scalars (target points)

    Returns array of distances in km.
    """
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return R * 2 * np.arcsin(np.sqrt(a))


# ---------------------------------------------------------------------------
# Feature functions
# ---------------------------------------------------------------------------

def _add_annual_ghi(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add annual_ghi (kWh/m²/year) via file or latitude-based estimate."""
    solar_csv = DATA_DIR / "solar_irradiance.csv"
    if solar_csv.exists():
        logger.info("Loading solar irradiance from %s", solar_csv)
        df = pd.read_csv(solar_csv)
        if {"pnu", "annual_ghi"}.issubset(df.columns):
            gdf = gdf.merge(df[["pnu", "annual_ghi"]], on="pnu", how="left")
            missing = gdf["annual_ghi"].isna().sum()
            if missing:
                logger.warning("%d parcels missing GHI after merge — filling with latitude estimate", missing)
                centroids_wgs = gdf.to_crs(CRS_WGS84).geometry.centroid
                lat = centroids_wgs.y
                gdf["annual_ghi"] = gdf["annual_ghi"].fillna(1400 - (lat - 34.5) * 200)
            return gdf
        else:
            logger.warning("solar_irradiance.csv missing 'pnu'/'annual_ghi' columns — using latitude estimate")

    logger.info("No solar_irradiance.csv found — computing GHI from centroid latitude")
    centroids_wgs = gdf.to_crs(CRS_WGS84).geometry.centroid
    lat = centroids_wgs.y
    gdf["annual_ghi"] = 1400.0 - (lat - 34.5) * 200.0
    return gdf


def _add_area_m2(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add area_m2 computed from geometry reprojected to EPSG:5179."""
    gdf_proj = gdf.to_crs(CRS_ANALYSIS)
    gdf["area_m2"] = gdf_proj.geometry.area
    return gdf


def _add_substation_features(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add dist_to_substation_km and substation_remaining_kw.

    Data source priority (via kepco_grid.fetch_substations):
      1. data/substations.csv  (수동 CSV — 가장 우선)
      2. VWorld WFS lp_pa_elec_ltfac  (VWORLD_API_KEY 필요)
      3. data.go.kr 변전소 현황  (DATA_GO_KR_KEY 필요)
      API 모두 실패 시 NaN (경고 출력).
    """
    sub_csv = DATA_DIR / "substations.csv"
    if sub_csv.exists():
        logger.info("Loading substations from local %s (overrides API)", sub_csv)
        df_sub = pd.read_csv(sub_csv)
        if {"lat", "lon", "remaining_kw"}.issubset(df_sub.columns):
            sub_df = df_sub[["lat", "lon", "remaining_kw"]]
        else:
            logger.warning("substations.csv missing required columns — falling back to API")
            sub_df = fetch_substations()
    else:
        sub_df = fetch_substations()

    if sub_df.empty:
        gdf["dist_to_substation_km"] = float("nan")
        gdf["substation_remaining_kw"] = float("nan")
        return gdf

    sub_lats = sub_df["lat"].values.astype(float)
    sub_lons = sub_df["lon"].values.astype(float)
    sub_kw   = sub_df["remaining_kw"].values.astype(float)

    centroids_wgs = gdf.to_crs(CRS_WGS84).geometry.centroid
    cent_lat = centroids_wgs.y.values
    cent_lon = centroids_wgs.x.values

    try:
        from scipy.spatial import KDTree
        tree = KDTree(np.column_stack([sub_lats, sub_lons]))
        _, idx = tree.query(np.column_stack([cent_lat, cent_lon]))
        dist_km = _haversine_km(cent_lat, cent_lon, sub_lats[idx], sub_lons[idx])
    except ImportError:
        n, m = len(cent_lat), len(sub_lats)
        dist_matrix = np.stack(
            [_haversine_km(cent_lat, cent_lon, sub_lats[j], sub_lons[j]) for j in range(m)],
            axis=1,
        )
        idx = dist_matrix.argmin(axis=1)
        dist_km = dist_matrix[np.arange(n), idx]

    gdf["dist_to_substation_km"] = dist_km
    gdf["substation_remaining_kw"] = sub_kw[idx]
    return gdf


def _add_powerline_features(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add dist_to_powerline_m and intersects_hvline_buffer.

    Data source: VWorld lt_l_clfla → if unavailable, dist_to_road_m proxy.

    intersects_hvline_buffer: True if parcel is within hard-filter setback
    distance of a high-voltage line (154kV+).  When no voltage attribute
    is available on the line, uses HV_LINE_SETBACK_DEFAULT_M (33 m).
    """
    centroids_wgs = gdf.to_crs(CRS_WGS84).geometry.centroid
    cent_lat = centroids_wgs.y.values
    cent_lon = centroids_wgs.x.values

    powerlines = fetch_powerlines()

    if powerlines is not None and not powerlines.empty:
        logger.info("Computing powerline distances from %d VWorld line segments", len(powerlines))
        gdf_proj = gdf.to_crs(CRS_ANALYSIS)
        lines_proj = powerlines.to_crs(CRS_ANALYSIS)

        from shapely.ops import unary_union
        lines_union = unary_union(lines_proj.geometry)
        dist_m = gdf_proj.geometry.distance(lines_union)
        gdf["dist_to_powerline_m"] = dist_m.values

        # High-voltage setback: check per-segment voltage attribute
        voltage_col = next(
            (c for c in ("voltage", "vol_val", "전압", "VOLTAGE") if c in powerlines.columns),
            None,
        )
        if voltage_col is not None:
            hv_lines = powerlines[
                powerlines[voltage_col].astype(str).str.contains("154|345|765", na=False)
            ]
            if not hv_lines.empty:
                hv_proj = hv_lines.to_crs(CRS_ANALYSIS)
                hv_union = unary_union(hv_proj.geometry)
                hv_dist_m = gdf_proj.geometry.distance(hv_union)
                gdf["intersects_hvline_buffer"] = hv_dist_m.values < HV_LINE_SETBACK_DEFAULT_M
            else:
                gdf["intersects_hvline_buffer"] = False
        else:
            # No voltage info: apply setback to all lines (conservative)
            gdf["intersects_hvline_buffer"] = dist_m.values < HV_LINE_SETBACK_DEFAULT_M
    else:
        # Fallback: use road distance as proxy for distribution line proximity.
        # In rural Korea, 배전선(배전주) typically run along roads.
        road_dist = gdf["dist_to_road_m"] if "dist_to_road_m" in gdf.columns else pd.Series(500.0, index=gdf.index)
        gdf["dist_to_powerline_m"] = road_dist.values.astype(float)
        gdf["intersects_hvline_buffer"] = False  # conservatively assume no HV line conflict
        logger.info("Powerline data unavailable — using road distance proxy for dist_to_powerline_m")

    return gdf


def _add_existing_solar_density(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add existing_solar_kw_5km and grid_saturation_ratio.

    existing_solar_kw_5km: sum of installed solar capacity (kW) within
    GRID_SATURATION_RADIUS_KM of each parcel centroid.

    grid_saturation_ratio: existing_solar_kw_5km / substation_remaining_kw
    (display/hard-filter metric, not in FEATURES_V2).

    Data source: data.go.kr SOLAR_PLANT_SERVICE_ID → 0 if unavailable.
    """
    solar_df = fetch_existing_solar()

    centroids_wgs = gdf.to_crs(CRS_WGS84).geometry.centroid
    cent_lat = centroids_wgs.y.values
    cent_lon = centroids_wgs.x.values

    existing_kw = compute_solar_density(
        cent_lat, cent_lon, solar_df, radius_km=GRID_SATURATION_RADIUS_KM
    )
    gdf["existing_solar_kw_5km"] = existing_kw

    # Derived ratio (for display and hard-filter use)
    sub_kw = gdf["substation_remaining_kw"].values.astype(float) if "substation_remaining_kw" in gdf.columns else np.full(len(gdf), 10000.0)
    safe_sub_kw = np.where(sub_kw > 0, sub_kw, 1.0)
    gdf["grid_saturation_ratio"] = existing_kw / safe_sub_kw

    if solar_df.empty:
        logger.info("existing_solar_kw_5km = 0 for all parcels (no solar plant data)")
    else:
        logger.info(
            "existing_solar_kw_5km: median=%.0f kW, max=%.0f kW (radius=%.1f km)",
            float(np.median(existing_kw)),
            float(existing_kw.max()),
            GRID_SATURATION_RADIUS_KM,
        )

    return gdf


def _add_road_features(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add dist_to_road_m and has_road_access_3m.

    Road data source (in priority order):
      1. data/roads.geojson  (VWorld lt_l_sprd, has road_bt width column)
      2. data/roads.shp
    Width column detection: road_bt (VWorld) > width > road_width > 폭 > 도로폭
    """
    roads_path = next(
        (DATA_DIR / f"roads{ext}" for ext in (".geojson", ".shp") if (DATA_DIR / f"roads{ext}").exists()),
        None,
    )
    if roads_path is not None:
        logger.info("Loading road data from %s", roads_path)
        roads = gpd.read_file(roads_path)
        if roads.crs is None:
            roads = roads.set_crs(CRS_WGS84)
        roads_proj = roads.to_crs(CRS_ANALYSIS)
        gdf_proj = gdf.to_crs(CRS_ANALYSIS)

        from shapely.ops import unary_union
        roads_union = unary_union(roads_proj.geometry)

        # Distance from each parcel boundary (not centroid) to nearest road
        dist_m = gdf_proj.geometry.distance(roads_union)

        # Sanity-check: if median distance > 5 km the road data is from a different
        # geographic area (VWorld WFS ignores spatial filters, returns national data).
        # Fall back to NaN so the hard filter treats it as unknown (fillna True = pass).
        if dist_m.median() > 5000:
            logger.warning(
                "Road data appears to be from wrong geographic area "
                "(median dist = %.0f m >> 5 km) — has_road_access_3m = NaN (pass-through). "
                "Fix: replace data/roads.geojson with Haenam-area road data.",
                dist_m.median(),
            )
            gdf["dist_to_road_m"] = float("nan")
            gdf["has_road_access_3m"] = pd.array([pd.NA] * len(gdf), dtype="boolean")
            return gdf

        gdf["dist_to_road_m"] = dist_m.values

        # Check width attribute if available
        # road_bt: VWorld lt_l_sprd (실제 도로폭 m), width/road_width: 기타 소스
        width_col = None
        for col in ("road_bt", "width", "road_width", "폭", "도로폭"):
            if col in roads.columns:
                width_col = col
                break

        if width_col is not None:
            # Spatial join to get nearest road width
            gdf_cent = gdf_proj.copy()
            gdf_cent.geometry = gdf_proj.geometry.centroid
            joined = gpd.sjoin_nearest(gdf_cent[["geometry"]], roads_proj[[width_col, "geometry"]], how="left")
            widths = joined[width_col].values
            gdf["has_road_access_3m"] = (dist_m.values <= 50.0) & (widths >= MIN_ROAD_WIDTH_M)
        else:
            gdf["has_road_access_3m"] = dist_m.values <= 50.0
    else:
        logger.warning(
            "REQUIRED: data/roads.geojson 없음 — dist_to_road_m 및 has_road_access_3m = NaN\n"
            "  해결: python -m solar_mvp.stage0_download (VWORLD_API_KEY 필요)"
        )
        gdf["dist_to_road_m"] = float("nan")
        gdf["has_road_access_3m"] = pd.array([pd.NA] * len(gdf), dtype="boolean")

    return gdf


def _add_building_features(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add nearest_building_dist_m."""
    buildings_path = next(
        (DATA_DIR / f"buildings{ext}" for ext in (".geojson", ".shp") if (DATA_DIR / f"buildings{ext}").exists()),
        None,
    )
    if buildings_path is not None:
        logger.info("Loading building data from %s", buildings_path)
        buildings = gpd.read_file(buildings_path)
        if buildings.crs is None:
            buildings = buildings.set_crs(CRS_WGS84)
        buildings_proj = buildings.to_crs(CRS_ANALYSIS)
        gdf_proj = gdf.to_crs(CRS_ANALYSIS)

        from shapely.ops import unary_union
        buildings_union = unary_union(buildings_proj.geometry)
        dist_m = gdf_proj.geometry.distance(buildings_union)

        # Same sanity-check as for roads: VWorld WFS may return national data.
        if dist_m.median() > 5000:
            logger.warning(
                "Building data appears to be from wrong geographic area "
                "(median dist = %.0f m) — nearest_building_dist_m = NaN (pass-through).",
                dist_m.median(),
            )
            gdf["nearest_building_dist_m"] = float("nan")
            return gdf

        gdf["nearest_building_dist_m"] = dist_m.values
    else:
        logger.warning(
            "REQUIRED: data/buildings.geojson 없음 — nearest_building_dist_m = NaN\n"
            "  해결: python -m solar_mvp.stage0_download (VWORLD_API_KEY 필요)"
        )
        gdf["nearest_building_dist_m"] = float("nan")

    return gdf


def _add_land_price(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add official_land_price (KRW/m²)."""
    price_csv = DATA_DIR / "land_price.csv"
    if price_csv.exists():
        logger.info("Loading land price data from %s", price_csv)
        df = pd.read_csv(price_csv)
        # Accept either column name
        price_col = "land_price_per_m2" if "land_price_per_m2" in df.columns else (
            "official_land_price" if "official_land_price" in df.columns else None
        )
        if "pnu" in df.columns and price_col:
            df = df.rename(columns={price_col: "official_land_price"})
            gdf = gdf.merge(df[["pnu", "official_land_price"]], on="pnu", how="left")
            missing = gdf["official_land_price"].isna().sum()
            if missing:
                logger.warning("%d parcels missing land price — filling with jimok-based estimate", missing)
                jimok_prices = gdf["jimok"].map(JIMOK_LAND_PRICE_KRW).fillna(JIMOK_LAND_PRICE_DEFAULT)
                gdf["official_land_price"] = gdf["official_land_price"].fillna(jimok_prices)
            return gdf
        else:
            logger.warning("land_price.csv missing 'pnu' or price column — using jimok-based estimate")

    logger.warning("No land_price.csv found — using jimok-based land price estimate")
    if "jimok" in gdf.columns:
        gdf["official_land_price"] = gdf["jimok"].map(JIMOK_LAND_PRICE_KRW).fillna(JIMOK_LAND_PRICE_DEFAULT).astype(float)
    else:
        gdf["official_land_price"] = float(JIMOK_LAND_PRICE_DEFAULT)
    return gdf


def _add_owner_type(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Ensure owner_type column is present."""
    if "owner_type" in gdf.columns:
        return gdf
    logger.warning("owner_type column not found in Stage 1 output — defaulting to '사유' (private) for all parcels")
    gdf["owner_type"] = "사유"
    return gdf


def _add_use_zone(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Ensure use_zone column is present."""
    if "use_zone" in gdf.columns:
        return gdf
    logger.warning("use_zone column not found — defaulting to '' for all parcels")
    gdf["use_zone"] = ""
    return gdf


def _add_agri_promotion_zone(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add in_agricultural_promotion_zone boolean."""
    agri_path = next(
        (DATA_DIR / f"agri_promotion{ext}" for ext in (".geojson", ".shp") if (DATA_DIR / f"agri_promotion{ext}").exists()),
        None,
    )
    shp_path = agri_path  # keep variable name for rest of function
    if shp_path is not None:
        logger.info("Loading agricultural promotion zone from %s", shp_path)
        agri = gpd.read_file(shp_path)
        if agri.crs is None:
            agri = agri.set_crs(CRS_WGS84)

        if not _gdf_within_area(agri, _HAENAM_BBOX_WGS84):
            logger.warning(
                "Agricultural promotion zone data has no features near Haenam "
                "(data likely from wrong geographic area) — in_agricultural_promotion_zone = False (pass-through)."
            )
            gdf["in_agricultural_promotion_zone"] = False
            return gdf

        agri_proj = agri.to_crs(CRS_ANALYSIS)
        gdf_proj = gdf.to_crs(CRS_ANALYSIS)[["geometry"]].copy()
        gdf_proj["_idx"] = range(len(gdf_proj))

        joined = gpd.sjoin(gdf_proj, agri_proj[["geometry"]], how="left", predicate="intersects")
        hit_idx = set(joined.loc[joined["index_right"].notna(), "_idx"].values)
        # Vectorized set lookup with numpy indexing
        hit_mask = np.zeros(len(gdf), dtype=bool)
        if hit_idx:
            hit_mask[list(hit_idx)] = True
        gdf["in_agricultural_promotion_zone"] = hit_mask
    else:
        logger.warning(
            "data/agri_promotion.geojson 없음 — in_agricultural_promotion_zone = False (낙관적)\n"
            "  해결: python -m solar_mvp.stage0_download (VWORLD_API_KEY 필요)"
        )
        gdf["in_agricultural_promotion_zone"] = False
    return gdf


def _add_protected_area(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add intersects_protected_area boolean from protected/*.shp or *.geojson files."""
    protected_dir = DATA_DIR / "protected"
    data_files: list[Path] = []
    if protected_dir.exists():
        data_files = list(protected_dir.glob("*.shp")) + list(protected_dir.glob("*.geojson"))

    shp_files = data_files  # keep variable name for rest of function

    if shp_files:
        logger.info("Loading %d protected area shapefile(s) from %s", len(shp_files), protected_dir)
        gdf_proj = gdf.to_crs(CRS_ANALYSIS)[["geometry"]].copy()
        gdf_proj["_idx"] = range(len(gdf_proj))
        hit_idx: set[int] = set()

        for shp in shp_files:
            try:
                pa = gpd.read_file(shp)
                if pa.crs is None:
                    pa = pa.set_crs(CRS_WGS84)
                if not _gdf_within_area(pa, _HAENAM_BBOX_WGS84):
                    logger.warning(
                        "Protected area file %s has no features near Haenam — skipping (data quality guard).", shp.name
                    )
                    continue
                pa_proj = pa.to_crs(CRS_ANALYSIS)
                joined = gpd.sjoin(gdf_proj, pa_proj[["geometry"]], how="left", predicate="intersects")
                hit_idx |= set(joined.loc[joined["index_right"].notna(), "_idx"].values)
            except Exception as exc:
                logger.warning("Failed to load protected area file %s: %s", shp, exc)

        # Vectorized set lookup with numpy indexing
        hit_mask = np.zeros(len(gdf), dtype=bool)
        if hit_idx:
            hit_mask[list(hit_idx)] = True
        gdf["intersects_protected_area"] = hit_mask
    else:
        logger.warning(
            "data/protected/ 없음 — intersects_protected_area = False (낙관적)\n"
            "  해결: python -m solar_mvp.stage0_download (VWORLD_API_KEY 필요)"
        )
        gdf["intersects_protected_area"] = False
    return gdf


def _add_forest_age(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add forest_age_class string column."""
    shp_path = DATA_DIR / "forest_age.shp"
    if shp_path.exists():
        logger.info("Loading forest age data from %s", shp_path)
        forest = gpd.read_file(shp_path)
        if forest.crs is None:
            forest = forest.set_crs(CRS_WGS84)
        forest_proj = forest.to_crs(CRS_ANALYSIS)

        # Detect age class column
        age_col = None
        for col in ("age_class", "영급", "AGECL", "age_cl", "AGE_CLASS"):
            if col in forest_proj.columns:
                age_col = col
                break
        if age_col is None:
            logger.warning("forest_age.shp has no recognisable age class column — defaulting to ''")
            gdf["forest_age_class"] = ""
            return gdf

        forest_proj = forest_proj[[age_col, "geometry"]].rename(columns={age_col: "forest_age_class"})
        gdf_proj = gdf.to_crs(CRS_ANALYSIS)[["geometry"]].copy()
        gdf_proj["_idx"] = range(len(gdf_proj))

        joined = gpd.sjoin(gdf_proj, forest_proj, how="left", predicate="intersects")
        # Resolve duplicates: take first match
        joined = joined[~joined.index.duplicated(keep="first")]
        age_values = joined["forest_age_class"].fillna("").astype(str).values
        gdf["forest_age_class"] = age_values
    else:
        logger.warning("Forest age shapefile not found at %s — defaulting to ''", shp_path)
        gdf["forest_age_class"] = ""
    return gdf


def _add_eup_myeon(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add eup_myeon (읍면) string column based on nearest centroid lookup."""
    if "eup_myeon" in gdf.columns:
        return gdf

    logger.info("Assigning eup_myeon from nearest known 해남군 읍면 centroid")
    names = [em[0] for em in HAENAM_EUP_MYEON]
    em_lats = np.array([em[1] for em in HAENAM_EUP_MYEON])
    em_lons = np.array([em[2] for em in HAENAM_EUP_MYEON])

    centroids_wgs = gdf.to_crs(CRS_WGS84).geometry.centroid
    cent_lat = centroids_wgs.y.values
    cent_lon = centroids_wgs.x.values

    # Build distance matrix (n_parcels × 14 읍면) and pick argmin
    n = len(cent_lat)
    m = len(names)
    dist_matrix = np.zeros((n, m))
    for j in range(m):
        dist_matrix[:, j] = _haversine_km(cent_lat, cent_lon, em_lats[j], em_lons[j])

    best_idx = dist_matrix.argmin(axis=1)
    gdf["eup_myeon"] = np.array(names)[best_idx]
    return gdf


# ---------------------------------------------------------------------------
# Main enrichment function
# ---------------------------------------------------------------------------

def enrich_parcels(force: bool = False) -> gpd.GeoDataFrame:
    """Stage 3: Add all FEATURES_V2 and hard-filter columns to parcels.

    Loads output/parcels_geom.parquet, adds features, saves
    output/parcels_enriched.parquet.  Skips if output exists unless force=True.
    """
    input_path  = OUTPUT_DIR / "parcels_geom.parquet"
    output_path = OUTPUT_DIR / "parcels_enriched.parquet"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not force and output_path.exists():
        logger.info("Loading cached Stage 3 output from %s", output_path)
        gdf = gpd.read_parquet(output_path)
        logger.info("Loaded %d parcels from cache.", len(gdf))
        return gdf

    logger.info("Loading Stage 2 output from %s", input_path)
    if not input_path.exists():
        raise FileNotFoundError(
            f"Stage 2 output not found: {input_path}\n"
            "Run stage2_geom.py first."
        )
    gdf = gpd.read_parquet(input_path)
    if gdf.crs is None:
        gdf = gdf.set_crs(CRS_WGS84)
    logger.info("Loaded %d parcels (CRS: %s)", len(gdf), gdf.crs)

    # ---- FEATURES_V2 (new columns) ----------------------------------------
    logger.info("Step 1/14: Computing annual_ghi …")
    gdf = _add_annual_ghi(gdf)

    logger.info("Step 2/14: Computing area_m2 …")
    gdf = _add_area_m2(gdf)

    logger.info("Step 3/14: Computing substation features (VWorld/data.go.kr/synthetic) …")
    gdf = _add_substation_features(gdf)

    logger.info("Step 4/14: Computing road features …")
    gdf = _add_road_features(gdf)

    logger.info("Step 5/14: Computing building distance …")
    gdf = _add_building_features(gdf)

    logger.info("Step 6/14: Adding official land price …")
    gdf = _add_land_price(gdf)

    # ---- 계통 피처 (한전 관련) -------------------------------------------
    logger.info("Step 7/14: Computing powerline features (VWorld/road proxy) …")
    gdf = _add_powerline_features(gdf)

    logger.info("Step 8/14: Computing existing solar density (data.go.kr/zero fallback) …")
    gdf = _add_existing_solar_density(gdf)

    # ---- Hard-filter input columns ----------------------------------------
    logger.info("Step 9/14: Ensuring use_zone …")
    gdf = _add_use_zone(gdf)

    logger.info("Step 10/14: Ensuring owner_type …")
    gdf = _add_owner_type(gdf)

    logger.info("Step 11/14: Computing agricultural promotion zone …")
    gdf = _add_agri_promotion_zone(gdf)

    logger.info("Step 12/14: Computing protected area intersection …")
    gdf = _add_protected_area(gdf)

    logger.info("Step 13/14: Adding forest age class and eup_myeon …")
    gdf = _add_forest_age(gdf)
    gdf = _add_eup_myeon(gdf)

    logger.info("Step 14/14: (done — validation follows)")

    # ---- Validation: confirm all FEATURES_V2 columns are present ----------
    missing_features = [c for c in FEATURES_V2 if c not in gdf.columns]
    if missing_features:
        logger.error("Missing FEATURES_V2 columns after enrichment: %s", missing_features)
    else:
        logger.info("All %d FEATURES_V2 columns present.", len(FEATURES_V2))

    # ---- Summary stats ----------------------------------------------------
    n_total = len(gdf)
    print(f"\nStage 3 enrichment complete")
    print(f"  Parcels                  : {n_total:,}")
    print(f"  annual_ghi range         : {gdf['annual_ghi'].min():.0f} – {gdf['annual_ghi'].max():.0f} kWh/m²/yr")
    print(f"  area_m2 median           : {gdf['area_m2'].median():,.0f} m²")
    print(f"  dist_to_substation_km    : {gdf['dist_to_substation_km'].median():.2f} km (median)")
    print(f"  FEATURES_V2 missing cols : {missing_features or 'none'}")
    print(f"  Output                   : {output_path}")

    gdf.to_parquet(output_path, index=False)
    logger.info("Saved enriched parcels to %s", output_path)

    return gdf


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Stage 3: Feature enrichment for 해남군 solar site candidates."
    )
    parser.add_argument("--force", action="store_true",
                        help="Re-compute even if parcels_enriched.parquet already exists.")
    args = parser.parse_args()
    enrich_parcels(force=args.force)
