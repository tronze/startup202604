"""Stage 1: Generate candidate solar site grid for Haenam-gun.

VWorld WFS cadastral layers (lp_pa_cbnd_*) do not support spatial filtering
for the Haenam area — they return national data regardless of CQL_FILTER.
As a practical alternative, we generate a 1km × 1km grid of candidate sites
over Haenam's bounding box.  Downstream stages (3-4) enrich and score each
cell using the real spatial layers already downloaded in Stage 0.
"""
from __future__ import annotations

import argparse
import hashlib
import logging
import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
from pyproj import Transformer
from shapely.geometry import box

from solar_mvp.config import CRS_ANALYSIS, CRS_WGS84, OUTPUT_DIR

logger = logging.getLogger(__name__)

# Haenam-gun approximate bounding box (WGS-84)
HAENAM_BBOX_WGS84 = (126.25, 34.30, 126.90, 34.75)

# Grid resolution in metres (projected CRS)
GRID_CELL_M = 1000  # 1 km × 1 km


def _make_grid(
    bbox_wgs84: tuple[float, float, float, float],
    cell_m: float,
) -> gpd.GeoDataFrame:
    """
    Create a regular grid of square cells covering bbox, in WGS-84.

    Args:
        bbox_wgs84: (minx, miny, maxx, maxy) in EPSG:4326
        cell_m: cell side length in metres

    Returns:
        GeoDataFrame with columns: pnu, geometry (polygon, EPSG:4326),
            jimok, area_official_m2, use_zone, owner_type, land_price
    """
    # Project bbox to metric CRS for grid construction
    to_proj = Transformer.from_crs(CRS_WGS84, CRS_ANALYSIS, always_xy=True)
    to_wgs = Transformer.from_crs(CRS_ANALYSIS, CRS_WGS84, always_xy=True)

    minx, miny = to_proj.transform(bbox_wgs84[0], bbox_wgs84[1])
    maxx, maxy = to_proj.transform(bbox_wgs84[2], bbox_wgs84[3])

    rows = []
    ix = 0
    x = minx
    while x < maxx:
        iy = 0
        y = miny
        while y < maxy:
            # Cell in projected CRS
            cx0, cy0 = x, y
            cx1, cy1 = x + cell_m, y + cell_m

            # Convert corners to WGS84
            lon0, lat0 = to_wgs.transform(cx0, cy0)
            lon1, lat1 = to_wgs.transform(cx1, cy1)

            cell_geom = box(lon0, lat0, lon1, lat1)
            cx_mid = (cx0 + cx1) / 2
            cy_mid = (cy0 + cy1) / 2

            # Synthetic PNU: deterministic hash of projected centroid
            pnu_seed = f"HN_{cx_mid:.0f}_{cy_mid:.0f}"
            pnu = "SIM" + hashlib.md5(pnu_seed.encode()).hexdigest()[:13].upper()

            rows.append({
                "pnu": pnu,
                "geometry": cell_geom,
                "jimok": "임야",        # default; stage3 refines via agri/forest layers
                "area_official_m2": float(cell_m ** 2),
                "use_zone": None,
                "owner_type": None,
                "land_price": None,
            })
            iy += 1
            y += cell_m
        ix += 1
        x += cell_m

    gdf = gpd.GeoDataFrame(rows, crs=CRS_WGS84)
    return gdf


def collect_parcels(force: bool = False) -> gpd.GeoDataFrame:
    """
    Generate candidate solar site grid cells for 해남군.

    Returns GeoDataFrame with columns:
        pnu, geometry, jimok, area_official_m2, use_zone, owner_type, land_price
    """
    output_path = OUTPUT_DIR / "parcels_raw.parquet"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not force and output_path.exists():
        logger.info("Loading existing %s", output_path)
        gdf = gpd.read_parquet(output_path)
        logger.info("Loaded %d candidate cells from cache.", len(gdf))
        return gdf

    t0 = time.time()

    logger.info(
        "Generating %dm grid over Haenam bbox %s",
        GRID_CELL_M,
        HAENAM_BBOX_WGS84,
    )
    gdf = _make_grid(HAENAM_BBOX_WGS84, GRID_CELL_M)
    elapsed = time.time() - t0

    logger.info(
        "Generated %d candidate cells | grid=%dm | elapsed=%.1fs",
        len(gdf),
        GRID_CELL_M,
        elapsed,
    )

    gdf.to_parquet(output_path, index=False)
    logger.info("Saved to %s", output_path)

    print(f"Candidate cells generated : {len(gdf):,}")
    print(f"Grid resolution           : {GRID_CELL_M}m × {GRID_CELL_M}m")
    print(f"Coverage bbox             : {HAENAM_BBOX_WGS84}")
    print(f"Time elapsed              : {elapsed:.1f}s")
    print(f"Output                    : {output_path}")

    return gdf


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Stage 1: Generate candidate solar site grid for 해남군."
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-generate even if parcels_raw.parquet already exists.",
    )
    parser.add_argument(
        "--cell-size", type=int, default=GRID_CELL_M, metavar="M",
        help=f"Grid cell size in metres (default: {GRID_CELL_M})",
    )
    args = parser.parse_args()

    if args.cell_size != GRID_CELL_M:
        GRID_CELL_M = args.cell_size

    collect_parcels(force=args.force)
