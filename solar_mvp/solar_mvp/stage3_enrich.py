"""Stage 3: Feature enrichment — adds all FEATURES_V2 and hard-filter columns."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd

from solar_mvp.config import (
    CRS_ANALYSIS,
    CRS_WGS84,
    DATA_DIR,
    OUTPUT_DIR,
    HAENAM_RESIDENTIAL_BUFFER_M,
    MIN_ROAD_WIDTH_M,
    FEATURES_V2,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SYNTHETIC_SUBSTATIONS = [
    {"name": "해남변전소",  "lat": 34.5745, "lon": 126.5991, "remaining_kw": 15000},
    {"name": "화원변전소",  "lat": 34.6327, "lon": 126.5109, "remaining_kw":  8000},
    {"name": "북평변전소",  "lat": 34.4897, "lon": 126.7092, "remaining_kw":  5000},
    {"name": "완도변전소",  "lat": 34.3389, "lon": 126.7540, "remaining_kw": 20000},
]

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
    """Add dist_to_substation_km and substation_remaining_kw."""
    sub_csv = DATA_DIR / "substations.csv"
    substations = []
    if sub_csv.exists():
        logger.info("Loading substations from %s", sub_csv)
        df = pd.read_csv(sub_csv)
        required = {"lat", "lon", "remaining_kw"}
        if required.issubset(df.columns):
            substations = df[["lat", "lon", "remaining_kw"]].to_dict("records")
        else:
            logger.warning("substations.csv missing columns — using synthetic fallback")
    if not substations:
        logger.warning("Using synthetic Haenam substation data (4 stations)")
        substations = SYNTHETIC_SUBSTATIONS

    # Build arrays for KD-tree lookup
    sub_lats = np.array([s["lat"] for s in substations])
    sub_lons = np.array([s["lon"] for s in substations])
    sub_kw   = np.array([s["remaining_kw"] for s in substations])

    centroids_wgs = gdf.to_crs(CRS_WGS84).geometry.centroid
    cent_lat = centroids_wgs.y.values
    cent_lon = centroids_wgs.x.values

    # For each parcel, compute distance to all substations and pick nearest
    # Use scipy KDTree on (lat, lon) — approximate but fine for ~100 km region
    try:
        from scipy.spatial import KDTree
        coords_sub = np.column_stack([sub_lats, sub_lons])
        coords_par = np.column_stack([cent_lat, cent_lon])
        tree = KDTree(coords_sub)
        _, idx = tree.query(coords_par)
        # Convert angular distance to km with haversine for accuracy (vectorized)
        dist_km = _haversine_km(cent_lat, cent_lon, sub_lats[idx], sub_lons[idx])
    except ImportError:
        logger.warning("scipy not available — computing substation distances with numpy")
        # Brute-force: (n_parcels, n_substations) distance matrix
        n = len(cent_lat)
        m = len(sub_lats)
        dist_matrix = np.zeros((n, m))
        for j in range(m):
            dist_matrix[:, j] = _haversine_km(cent_lat, cent_lon, sub_lats[j], sub_lons[j])
        idx = dist_matrix.argmin(axis=1)
        dist_km = dist_matrix[np.arange(n), idx]

    gdf["dist_to_substation_km"] = dist_km
    gdf["substation_remaining_kw"] = sub_kw[idx]
    return gdf


def _add_road_features(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add dist_to_road_m and has_road_access_3m."""
    roads_path = DATA_DIR / "roads.geojson"
    if roads_path.exists():
        logger.info("Loading road data from %s", roads_path)
        roads = gpd.read_file(roads_path)
        if roads.crs is None:
            roads = roads.set_crs(CRS_WGS84)
        roads_proj = roads.to_crs(CRS_ANALYSIS)
        gdf_proj = gdf.to_crs(CRS_ANALYSIS)

        # Spatial join: nearest road for each parcel boundary
        # Use unary_union of roads for distance computation
        from shapely.ops import unary_union
        roads_union = unary_union(roads_proj.geometry)

        # Distance from each parcel boundary (not centroid) to nearest road
        dist_m = gdf_proj.geometry.distance(roads_union)
        gdf["dist_to_road_m"] = dist_m.values

        # Check width attribute if available
        width_col = None
        for col in ("width", "road_width", "폭", "도로폭"):
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
            "Road data not found at %s — setting dist_to_road_m=0 (optimistic fallback)", roads_path
        )
        gdf["dist_to_road_m"] = 0.0
        gdf["has_road_access_3m"] = True

    return gdf


def _add_building_features(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add nearest_building_dist_m."""
    buildings_path = DATA_DIR / "buildings.geojson"
    if buildings_path.exists():
        logger.info("Loading building data from %s", buildings_path)
        buildings = gpd.read_file(buildings_path)
        if buildings.crs is None:
            buildings = buildings.set_crs(CRS_WGS84)
        buildings_proj = buildings.to_crs(CRS_ANALYSIS)
        gdf_proj = gdf.to_crs(CRS_ANALYSIS)

        from shapely.ops import unary_union
        buildings_union = unary_union(buildings_proj.geometry)
        dist_m = gdf_proj.geometry.distance(buildings_union)
        gdf["nearest_building_dist_m"] = dist_m.values
    else:
        fallback = float(HAENAM_RESIDENTIAL_BUFFER_M + 1)  # 301 m — passes the filter
        logger.warning(
            "Building data not found at %s — setting nearest_building_dist_m=%.0f (optimistic fallback)",
            buildings_path, fallback,
        )
        gdf["nearest_building_dist_m"] = fallback

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
    shp_path = DATA_DIR / "agri_promotion.shp"
    if shp_path.exists():
        logger.info("Loading agricultural promotion zone from %s", shp_path)
        agri = gpd.read_file(shp_path)
        if agri.crs is None:
            agri = agri.set_crs(CRS_WGS84)
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
            "Agricultural promotion zone shapefile not found at %s — defaulting to False", shp_path
        )
        gdf["in_agricultural_promotion_zone"] = False
    return gdf


def _add_protected_area(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add intersects_protected_area boolean from protected/*.shp files."""
    protected_dir = DATA_DIR / "protected"
    shp_files = list(protected_dir.glob("*.shp")) if protected_dir.exists() else []

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
            "No protected area shapefiles found in %s — defaulting to False", protected_dir
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
    logger.info("Step 1/11: Computing annual_ghi …")
    gdf = _add_annual_ghi(gdf)

    logger.info("Step 2/11: Computing area_m2 …")
    gdf = _add_area_m2(gdf)

    logger.info("Step 3/11: Computing substation features …")
    gdf = _add_substation_features(gdf)

    logger.info("Step 4/11: Computing road features …")
    gdf = _add_road_features(gdf)

    logger.info("Step 5/11: Computing building distance …")
    gdf = _add_building_features(gdf)

    logger.info("Step 6/11: Adding official land price …")
    gdf = _add_land_price(gdf)

    # ---- Hard-filter input columns ----------------------------------------
    logger.info("Step 7/11: Ensuring use_zone …")
    gdf = _add_use_zone(gdf)

    logger.info("Step 8/11: Ensuring owner_type …")
    gdf = _add_owner_type(gdf)

    logger.info("Step 9/11: Computing agricultural promotion zone …")
    gdf = _add_agri_promotion_zone(gdf)

    logger.info("Step 10/11: Computing protected area intersection …")
    gdf = _add_protected_area(gdf)

    logger.info("Step 11/11: Adding forest age class and eup_myeon …")
    gdf = _add_forest_age(gdf)
    gdf = _add_eup_myeon(gdf)

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
