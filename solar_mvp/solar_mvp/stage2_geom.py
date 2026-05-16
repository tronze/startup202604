"""Stage 2: Compute terrain features (slope, aspect, elevation) from 5m DEM."""
from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path
from typing import Optional

import numpy as np
import geopandas as gpd
import rasterio
from rasterio.mask import mask as rasterio_mask
from rasterio.features import rasterize
from rasterio.transform import from_bounds
from shapely.geometry import mapping
from tqdm import tqdm

from solar_mvp.config import (
    CRS_ANALYSIS,
    CRS_WGS84,
    DATA_DIR,
    OUTPUT_DIR,
    MAX_SLOPE_DEG,
    MAX_ELEVATION_M,
)

logger = logging.getLogger(__name__)

DEM_PATH = DATA_DIR / "dem" / "haenam_slope.tif"

# Threshold for switching to vectorized path
_VECTORIZED_THRESHOLD = 10_000


# ---------------------------------------------------------------------------
# 1. load_dem
# ---------------------------------------------------------------------------

def load_dem(dem_path: Path) -> tuple[np.ndarray, dict]:
    """Open DEM raster and return (elevation_array, meta_dict).

    The meta dict contains: transform, crs, nodata, height, width.
    """
    with rasterio.open(dem_path) as src:
        elevation = src.read(1).astype(np.float64)
        meta = {
            "transform": src.transform,
            "crs": src.crs,
            "nodata": src.nodata,
            "height": src.height,
            "width": src.width,
        }
    return elevation, meta


# ---------------------------------------------------------------------------
# 2. compute_slope_aspect
# ---------------------------------------------------------------------------

def compute_slope_aspect(
    elevation: np.ndarray,
    transform,
    nodata,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute slope (degrees) and aspect (degrees) from an elevation array.

    Cell sizes come from the affine transform:
      - transform.a  → pixel width  in CRS units (positive, metres for EPSG:5179)
      - transform.e  → pixel height in CRS units (negative, hence abs)

    Slope formula:
        slope_deg = arctan(sqrt((dz/dx)² + (dz/dy)²)) × 180/π

    Aspect formula (0 = North, 90 = East, …):
        aspect_deg = arctan2(-dz/dx, dz/dy) × 180/π, normalised to [0, 360)
    """
    elev = elevation.astype(np.float64)

    # Mask nodata
    if nodata is not None:
        elev[elev == nodata] = np.nan

    cell_x = abs(transform.a)  # metres
    cell_y = abs(transform.e)  # metres

    # numpy.gradient returns [grad_row, grad_col] i.e. [dz/dy_pix, dz/dx_pix]
    grad = np.gradient(elev)
    dz_dy = grad[0] / cell_y  # rise per metre in y direction
    dz_dx = grad[1] / cell_x  # rise per metre in x direction

    # Slope
    slope_rad = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
    slope_deg = np.degrees(slope_rad)

    # Aspect: 0 = North, clockwise
    aspect_rad = np.arctan2(-dz_dx, dz_dy)
    aspect_deg = np.degrees(aspect_rad)
    aspect_deg = (aspect_deg + 360.0) % 360.0

    # Propagate NaN mask
    nan_mask = np.isnan(elev)
    slope_deg[nan_mask] = np.nan
    aspect_deg[nan_mask] = np.nan

    return slope_deg, aspect_deg


# ---------------------------------------------------------------------------
# 3. classify_aspect
# ---------------------------------------------------------------------------

def classify_aspect(aspect_deg: np.ndarray) -> np.ndarray:
    """Convert aspect degrees to Korean cardinal-direction strings.

    Boundaries (clockwise from North):
        북향: [315, 360) ∪ [0, 45)
        동향: [45, 135)
        남향: [135, 225)
        서향: [225, 315)
    """
    result = np.empty(aspect_deg.shape, dtype=object)
    result[:] = ""  # default (handles NaN positions)

    valid = ~np.isnan(aspect_deg)
    a = aspect_deg[valid]

    classes = np.where(
        (a >= 135) & (a < 225), "남향",
        np.where(
            (a >= 45) & (a < 135), "동향",
            np.where(
                (a >= 225) & (a < 315), "서향",
                "북향",  # [315, 360) ∪ [0, 45)
            ),
        ),
    )
    result[valid] = classes
    return result


# ---------------------------------------------------------------------------
# 4. sample_raster_for_parcel
# ---------------------------------------------------------------------------

def sample_raster_for_parcel(
    parcel_geom,
    raster_array: np.ndarray,
    transform,
    nodata,
) -> Optional[np.ndarray]:
    """Extract valid pixel values within *parcel_geom* from *raster_array*.

    The geometry must already be in the same CRS as the raster.
    Uses rasterio.mask to cut out pixels, then returns a 1-D array of
    non-nodata values (or None if nothing is found).
    """
    import rasterio.io
    from rasterio.crs import CRS as RasterioCRS

    height, width = raster_array.shape
    mem_profile = {
        "driver": "GTiff",
        "dtype": raster_array.dtype,
        "width": width,
        "height": height,
        "count": 1,
        "transform": transform,
        "nodata": nodata if nodata is not None else np.nan,
    }

    with rasterio.io.MemoryFile() as memfile:
        with memfile.open(**mem_profile) as dataset:
            dataset.write(raster_array, 1)
            try:
                masked, _ = rasterio_mask(
                    dataset,
                    [mapping(parcel_geom)],
                    crop=True,
                    all_touched=True,
                    nodata=mem_profile["nodata"],
                )
            except Exception:
                return None

    flat = masked[0].ravel().astype(np.float64)

    nd = mem_profile["nodata"]
    if nodata is not None:
        valid = flat[flat != nd]
    else:
        valid = flat[~np.isnan(flat)]

    return valid if len(valid) > 0 else None


# ---------------------------------------------------------------------------
# 5a. _loop_terrain  (small datasets)
# ---------------------------------------------------------------------------

def _loop_terrain(
    parcels_proj: gpd.GeoDataFrame,
    slope_arr: np.ndarray,
    aspect_arr: np.ndarray,
    elevation: np.ndarray,
    meta: dict,
) -> dict[str, list]:
    """Per-parcel loop using rasterio.mask.  Used when n < _VECTORIZED_THRESHOLD."""
    transform = meta["transform"]
    nodata = meta["nodata"]

    slope_means, slope_stds, elev_means = [], [], []
    aspect_south_flags, aspect_classes = [], []

    for geom in tqdm(parcels_proj.geometry, desc="terrain (loop)", unit="parcel"):
        if geom is None or geom.is_empty:
            slope_means.append(np.nan)
            slope_stds.append(np.nan)
            elev_means.append(np.nan)
            aspect_south_flags.append(np.nan)
            aspect_classes.append("")
            continue

        pixels_elev = sample_raster_for_parcel(geom, elevation, transform, nodata)
        pixels_slope = sample_raster_for_parcel(geom, slope_arr, transform, nodata)
        pixels_aspect = sample_raster_for_parcel(geom, aspect_arr, transform, nodata)

        if pixels_slope is None or len(pixels_slope) == 0:
            slope_means.append(np.nan)
            slope_stds.append(np.nan)
            elev_means.append(np.nan)
            aspect_south_flags.append(np.nan)
            aspect_classes.append("")
            continue

        slope_means.append(float(np.nanmean(pixels_slope)))
        slope_stds.append(float(np.nanstd(pixels_slope)))
        elev_means.append(float(np.nanmean(pixels_elev)) if pixels_elev is not None else np.nan)

        if pixels_aspect is not None and len(pixels_aspect) > 0:
            aspect_labels = classify_aspect(pixels_aspect)
            # Modal class
            unique, counts = np.unique(aspect_labels[aspect_labels != ""], return_counts=True)
            if len(unique) == 0:
                aspect_classes.append("")
                aspect_south_flags.append(0)
            else:
                modal = unique[np.argmax(counts)]
                aspect_classes.append(str(modal))
                aspect_south_flags.append(1 if modal == "남향" else 0)
        else:
            aspect_classes.append("")
            aspect_south_flags.append(np.nan)

    return {
        "slope_mean": slope_means,
        "slope_std": slope_stds,
        "elevation_m": elev_means,
        "aspect_south": aspect_south_flags,
        "aspect_class": aspect_classes,
    }


# ---------------------------------------------------------------------------
# 5b. _vectorized_terrain  (large datasets)
# ---------------------------------------------------------------------------

def _vectorized_terrain(
    parcels_proj: gpd.GeoDataFrame,
    slope_arr: np.ndarray,
    aspect_arr: np.ndarray,
    elevation: np.ndarray,
    meta: dict,
) -> dict[str, list]:
    """Rasterize all parcel polygons at DEM resolution, then do numpy zonal stats.

    Significantly faster for large n because rasterio.mask overhead is bypassed.
    """
    transform = meta["transform"]
    height = meta["height"]
    width = meta["width"]

    # Build label raster: pixel value = parcel index + 1  (0 = background)
    shapes = [
        (mapping(geom), int(idx + 1))
        for idx, geom in enumerate(parcels_proj.geometry)
        if geom is not None and not geom.is_empty
    ]

    label_raster = rasterize(
        shapes,
        out_shape=(height, width),
        transform=transform,
        fill=0,
        dtype=np.int32,
    )

    # Flatten arrays for fast indexing
    labels_flat = label_raster.ravel()
    slope_flat = slope_arr.ravel()
    aspect_flat = aspect_arr.ravel()
    elev_flat = elevation.ravel()

    n = len(parcels_proj)
    slope_means = np.full(n, np.nan)
    slope_stds = np.full(n, np.nan)
    elev_means = np.full(n, np.nan)
    aspect_south_flags: list = [np.nan] * n
    aspect_classes: list = [""] * n

    logger.info("Vectorized zonal stats over %d parcels…", n)
    for idx in tqdm(range(n), desc="terrain (vectorized)", unit="parcel"):
        label = idx + 1
        mask = labels_flat == label
        if not mask.any():
            continue

        s = slope_flat[mask]
        e = elev_flat[mask]
        a = aspect_flat[mask]

        valid_s = s[~np.isnan(s)]
        valid_e = e[~np.isnan(e)]
        valid_a = a[~np.isnan(a)]

        if len(valid_s) == 0:
            continue

        slope_means[idx] = float(np.mean(valid_s))
        slope_stds[idx] = float(np.std(valid_s))
        if len(valid_e) > 0:
            elev_means[idx] = float(np.mean(valid_e))

        if len(valid_a) > 0:
            aspect_labels = classify_aspect(valid_a)
            unique, counts = np.unique(aspect_labels[aspect_labels != ""], return_counts=True)
            if len(unique) > 0:
                modal = unique[np.argmax(counts)]
                aspect_classes[idx] = str(modal)
                aspect_south_flags[idx] = 1 if modal == "남향" else 0

    return {
        "slope_mean": slope_means.tolist(),
        "slope_std": slope_stds.tolist(),
        "elevation_m": elev_means.tolist(),
        "aspect_south": aspect_south_flags,
        "aspect_class": aspect_classes,
    }


# ---------------------------------------------------------------------------
# 5. enrich_terrain
# ---------------------------------------------------------------------------

def enrich_terrain(
    parcels: gpd.GeoDataFrame,
    dem_path: Path,
) -> gpd.GeoDataFrame:
    """Add terrain columns (slope_mean, slope_std, elevation_m, aspect_south,
    aspect_class) to *parcels*.

    Spatial operations are performed in EPSG:5179; geometry is returned in
    EPSG:4326 for downstream compatibility.
    """
    parcels = parcels.copy()

    # Reproject to analysis CRS for spatial operations
    parcels_proj = parcels.to_crs(CRS_ANALYSIS)

    # Load DEM
    elevation, meta = load_dem(dem_path)
    slope_arr, aspect_arr = compute_slope_aspect(elevation, meta["transform"], meta["nodata"])

    logger.info(
        "DEM loaded: shape=%s, transform=%s, nodata=%s",
        elevation.shape,
        meta["transform"],
        meta["nodata"],
    )

    n = len(parcels_proj)
    if n >= _VECTORIZED_THRESHOLD:
        logger.info("Large dataset (%d parcels) → vectorized path", n)
        cols = _vectorized_terrain(parcels_proj, slope_arr, aspect_arr, elevation, meta)
    else:
        logger.info("Small dataset (%d parcels) → loop path", n)
        cols = _loop_terrain(parcels_proj, slope_arr, aspect_arr, elevation, meta)

    for col, values in cols.items():
        parcels[col] = values

    return parcels


# ---------------------------------------------------------------------------
# 6. process_geometry
# ---------------------------------------------------------------------------

def process_geometry(force: bool = False) -> gpd.GeoDataFrame:
    """Main entry point for Stage 2.

    Loads parcels_raw.parquet, enriches with terrain features, and saves
    parcels_geom.parquet.  Skips processing if output exists (unless force=True).
    """
    input_path = OUTPUT_DIR / "parcels_raw.parquet"
    output_path = OUTPUT_DIR / "parcels_geom.parquet"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not force and output_path.exists():
        logger.info("Loading existing %s", output_path)
        gdf = gpd.read_parquet(output_path)
        logger.info("Loaded %d parcels from cache.", len(gdf))
        return gdf

    logger.info("Loading %s", input_path)
    parcels = gpd.read_parquet(input_path)
    logger.info("Loaded %d parcels.", len(parcels))

    t0 = time.time()

    dem_path = DEM_PATH
    if not dem_path.exists():
        logger.warning(
            "DEM file not found at %s — terrain features will be NaN.  "
            "Provide the file to enable full processing.",
            dem_path,
        )
        for col in ("slope_mean", "slope_std", "elevation_m"):
            parcels[col] = np.nan
        for col in ("aspect_south",):
            parcels[col] = np.nan
        parcels["aspect_class"] = ""
    else:
        parcels = enrich_terrain(parcels, dem_path)

    elapsed = time.time() - t0

    # Summary stats
    n_total = len(parcels)
    n_terrain = int(parcels["slope_mean"].notna().sum())
    pct = 100.0 * n_terrain / max(n_total, 1)

    print(f"Parcels processed      : {n_total:,}")
    print(f"With terrain data      : {n_terrain:,}  ({pct:.1f}%)")
    print(f"Time elapsed           : {elapsed:.1f}s")
    print(f"Output                 : {output_path}")

    parcels.to_parquet(output_path, index=False)
    logger.info("Saved to %s", output_path)

    return parcels


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Stage 2: Compute terrain features from 5m DEM for 해남군 parcels."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-compute even if parcels_geom.parquet already exists.",
    )
    args = parser.parse_args()
    process_geometry(force=args.force)
