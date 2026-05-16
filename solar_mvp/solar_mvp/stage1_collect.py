"""Stage 1: Collect raw parcel data for Haenam-gun from VWorld."""
from __future__ import annotations

import argparse
import logging
import os
import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
from dotenv import load_dotenv
from shapely.geometry import shape, box

from solar_mvp.config import (
    CACHE_DIR,
    CRS_WGS84,
    OUTPUT_DIR,
    SIGUNGU_CODE,
)
from solar_mvp.vworld_client import VWorldClient

logger = logging.getLogger(__name__)

# Tile size in degrees (WGS-84).  해남군 bbox is ~0.6° × 0.5° → ~30 tiles.
TILE_DEG = 0.1

# Haenam-gun approximate bounding box (fallback if API doesn't return boundary)
HAENAM_BBOX_APPROX = (126.25, 34.30, 126.90, 34.75)  # (minx, miny, maxx, maxy)


def _load_api_key() -> str:
    load_dotenv()
    key = os.getenv("VWORLD_API_KEY", "").strip()
    if not key:
        raise EnvironmentError(
            "VWORLD_API_KEY is not set.  "
            "Add it to your .env file or export it as an environment variable."
        )
    return key


def _make_tiles(
    bbox: tuple[float, float, float, float],
    tile_deg: float = TILE_DEG,
) -> list[tuple[float, float, float, float]]:
    """Subdivide bbox into tiles of size tile_deg × tile_deg."""
    minx, miny, maxx, maxy = bbox
    tiles: list[tuple[float, float, float, float]] = []
    x = minx
    while x < maxx:
        y = miny
        while y < maxy:
            tiles.append((x, y, min(x + tile_deg, maxx), min(y + tile_deg, maxy)))
            y += tile_deg
        x += tile_deg
    return tiles


def _geojson_to_gdf(geojson: dict) -> gpd.GeoDataFrame:
    """Convert a GeoJSON FeatureCollection dict to a GeoDataFrame (EPSG:4326)."""
    features = geojson.get("features", [])
    if not features:
        return gpd.GeoDataFrame(geometry=[], crs=CRS_WGS84)

    rows = []
    for feat in features:
        props = feat.get("properties") or {}
        geom_raw = feat.get("geometry")
        try:
            geom = shape(geom_raw) if geom_raw else None
        except Exception:
            geom = None
        rows.append({**props, "geometry": geom})

    gdf = gpd.GeoDataFrame(rows, crs=CRS_WGS84)
    return gdf


def _normalise_pnu(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Ensure a consistent 'pnu' column regardless of VWorld field name."""
    if "pnu" not in gdf.columns:
        for candidate in ("PNU", "A1", "pnu_cd", "PNU_CD"):
            if candidate in gdf.columns:
                gdf = gdf.rename(columns={candidate: "pnu"})
                break
    if "pnu" not in gdf.columns:
        gdf["pnu"] = None
    return gdf


def _normalise_columns(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Map VWorld field names to canonical schema columns."""
    rename_map = {
        # jimok (지목)
        "JIMOK": "jimok",
        "jimok": "jimok",
        "A7": "jimok",
        # area (면적)
        "SHAPE_AREA": "area_official_m2",
        "shape_area": "area_official_m2",
        "A4": "area_official_m2",
        # use_zone (용도지역)
        "USE_ZONE": "use_zone",
        "use_zone": "use_zone",
        # owner_type (소유구분)
        "OWN_DIV_CD": "owner_type",
        "own_div_cd": "owner_type",
        "A9": "owner_type",
        # land_price (공시지가)
        "LAND_PRICE": "land_price",
        "land_price": "land_price",
        "OFFPRICE": "land_price",
    }
    cols_to_rename = {k: v for k, v in rename_map.items() if k in gdf.columns and k != v}
    if cols_to_rename:
        gdf = gdf.rename(columns=cols_to_rename)

    # Ensure all canonical columns exist (fill with NaN if missing)
    for col in ["jimok", "area_official_m2", "use_zone", "owner_type", "land_price"]:
        if col not in gdf.columns:
            gdf[col] = None

    # Keep only the columns we care about plus geometry
    keep = ["pnu", "jimok", "area_official_m2", "use_zone", "owner_type", "land_price", "geometry"]
    extra = [c for c in gdf.columns if c not in keep]
    return gdf.drop(columns=extra, errors="ignore")[keep]


def _fetch_all_parcels(
    client: VWorldClient,
    bbox: tuple[float, float, float, float],
) -> gpd.GeoDataFrame:
    """Collect parcels from all tiles covering bbox, with pagination."""
    tiles = _make_tiles(bbox)
    logger.info("Fetching parcels across %d tiles (bbox=%s)", len(tiles), bbox)

    all_gdfs: list[gpd.GeoDataFrame] = []
    for i, tile in enumerate(tiles, 1):
        logger.info("Tile %d/%d: %s", i, len(tiles), tile)
        page = 1
        while True:
            result = client.get_parcels_by_bbox(tile, page=page, per_page=1000)
            features = result.get("features", [])
            if not features:
                break
            tile_gdf = _geojson_to_gdf(result)
            all_gdfs.append(tile_gdf)
            logger.debug("  Page %d: %d features", page, len(features))
            if len(features) < 1000:
                break  # no more pages
            page += 1

    if not all_gdfs:
        logger.warning("No parcel features retrieved from any tile.")
        return gpd.GeoDataFrame(
            columns=["pnu", "jimok", "area_official_m2", "use_zone", "owner_type", "land_price", "geometry"],
            crs=CRS_WGS84,
        )

    combined = gpd.GeoDataFrame(
        pd.concat(all_gdfs, ignore_index=True), crs=CRS_WGS84
    )
    return combined


def _get_haenam_boundary(client: VWorldClient) -> gpd.GeoDataFrame | None:
    """Return Haenam-gun boundary as GeoDataFrame, or None on failure."""
    raw = client.get_admin_boundary(SIGUNGU_CODE)
    features = raw.get("features", [])
    if not features:
        logger.warning("Admin boundary API returned no features for code %s", SIGUNGU_CODE)
        return None
    return _geojson_to_gdf(raw)


def _join_land_use(
    parcels: gpd.GeoDataFrame,
    client: VWorldClient,
    bbox: tuple[float, float, float, float],
) -> gpd.GeoDataFrame:
    """Spatial-join land use plan zones onto parcels (best-effort)."""
    tiles = _make_tiles(bbox)
    lu_gdfs: list[gpd.GeoDataFrame] = []
    for tile in tiles:
        raw = client.get_land_use_plan(tile)
        if raw.get("features"):
            lu_gdfs.append(_geojson_to_gdf(raw))

    if not lu_gdfs:
        logger.warning("No land use plan features retrieved — use_zone column will be NaN.")
        return parcels

    lu = gpd.GeoDataFrame(pd.concat(lu_gdfs, ignore_index=True), crs=CRS_WGS84)
    lu = lu.drop_duplicates()

    # Find the use zone field
    zone_col = None
    for candidate in ("USE_ZONE", "use_zone", "LUSE_NM", "luse_nm", "NM"):
        if candidate in lu.columns:
            zone_col = candidate
            break

    if zone_col is None:
        logger.warning("Cannot identify use_zone column in land use layer.")
        return parcels

    lu_slim = lu[[zone_col, "geometry"]].rename(columns={zone_col: "_lu_zone"})
    lu_slim = lu_slim[lu_slim.geometry.notna() & lu_slim.geometry.is_valid]

    # Centroid join: faster and avoids edge cases
    parcel_centroids = parcels.copy()
    parcel_centroids["geometry"] = parcel_centroids.geometry.centroid
    joined = gpd.sjoin(parcel_centroids, lu_slim, how="left", predicate="within")

    if "_lu_zone" in joined.columns:
        # Fill use_zone only where currently null
        mask = parcels["use_zone"].isna() | (parcels["use_zone"] == "")
        parcels.loc[mask & joined["_lu_zone"].notna().values, "use_zone"] = (
            joined.loc[mask, "_lu_zone"].values
        )

    return parcels


def collect_parcels(force: bool = False) -> gpd.GeoDataFrame:
    """
    Collect all parcels for 해남군.

    Args:
        force: if True, ignore existing parcels_raw.parquet and re-fetch.

    Returns:
        GeoDataFrame with columns:
            pnu, geometry, jimok, area_official_m2, use_zone, owner_type, land_price
        (some columns may be NaN if not available from VWorld parcel layer)
    """
    output_path = OUTPUT_DIR / "parcels_raw.parquet"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not force and output_path.exists():
        logger.info("Loading existing %s", output_path)
        gdf = gpd.read_parquet(output_path)
        logger.info("Loaded %d parcels from cache.", len(gdf))
        return gdf

    api_key = _load_api_key()
    client = VWorldClient(api_key, cache_dir=CACHE_DIR / "vworld")

    t0 = time.time()

    # 1. Get admin boundary
    boundary_gdf = _get_haenam_boundary(client)
    if boundary_gdf is not None and not boundary_gdf.empty:
        total_bounds = boundary_gdf.geometry.total_bounds  # (minx, miny, maxx, maxy)
        bbox = tuple(float(v) for v in total_bounds)
        boundary_union = boundary_gdf.geometry.union_all()
        logger.info("Using API boundary bbox: %s", bbox)
    else:
        bbox = HAENAM_BBOX_APPROX
        boundary_union = box(*bbox)
        logger.warning(
            "Falling back to approximate Haenam-gun bbox: %s", bbox
        )

    # 2. Fetch all parcels in tiles
    raw_gdf = _fetch_all_parcels(client, bbox)

    if raw_gdf.empty:
        logger.error("No parcels retrieved. Check VWORLD_API_KEY and network.")
        return raw_gdf

    # 3. Normalise columns
    raw_gdf = _normalise_pnu(raw_gdf)
    raw_gdf = _normalise_columns(raw_gdf)

    # 4. Deduplicate by PNU (keep first occurrence)
    before_dedup = len(raw_gdf)
    raw_gdf = raw_gdf.drop_duplicates(subset=["pnu"]) if raw_gdf["pnu"].notna().any() else raw_gdf.drop_duplicates()
    logger.info("Deduplication: %d → %d parcels", before_dedup, len(raw_gdf))

    # 5. Filter to parcels whose centroid is within the Haenam-gun boundary
    raw_gdf = raw_gdf[raw_gdf.geometry.notna() & raw_gdf.geometry.is_valid]
    centroids = raw_gdf.geometry.centroid
    within_mask = centroids.within(boundary_union)
    before_filter = len(raw_gdf)
    raw_gdf = raw_gdf[within_mask].reset_index(drop=True)
    logger.info(
        "Boundary filter: %d → %d parcels (kept %.1f%%)",
        before_filter,
        len(raw_gdf),
        100.0 * len(raw_gdf) / max(before_filter, 1),
    )

    # 6. Best-effort land use join to populate use_zone
    raw_gdf = _join_land_use(raw_gdf, client, bbox)

    elapsed = time.time() - t0
    logger.info(
        "Summary: %d parcels collected | bbox=%s | elapsed=%.1fs",
        len(raw_gdf),
        bbox,
        elapsed,
    )

    # 7. Save
    raw_gdf.to_parquet(output_path, index=False)
    logger.info("Saved to %s", output_path)

    # Human-readable summary to stdout
    print(f"Total parcels collected : {len(raw_gdf):,}")
    print(f"Bounding box            : {bbox}")
    print(f"Time elapsed            : {elapsed:.1f}s")
    print(f"Output                  : {output_path}")

    return raw_gdf


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Stage 1: Collect raw parcel data for 해남군 from VWorld API."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch even if parcels_raw.parquet already exists.",
    )
    args = parser.parse_args()
    df = collect_parcels(force=args.force)
    print(f"Collected {len(df)} parcels")
