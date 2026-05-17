"""Stage 5: Generate interactive folium map for SolarFit MVP v2."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import folium
from folium import plugins

from solar_mvp.config import OUTPUT_DIR, CRS_WGS84

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def get_top_n(parcels: pd.DataFrame, score_col: str, n: int = 100) -> pd.DataFrame:
    """
    Return the top-n parcels by score_col (descending, NaN excluded).

    Args:
        parcels: DataFrame with score column
        score_col: Column name to sort by
        n: Number of top parcels to return

    Returns:
        DataFrame of top-n parcels
    """
    if score_col not in parcels.columns:
        logger.warning(f"Column '{score_col}' not found; returning empty DataFrame")
        return pd.DataFrame()

    # Filter out NaN scores and sort descending
    valid = parcels[parcels[score_col].notna()].copy()
    if valid.empty:
        return pd.DataFrame()

    return valid.nlargest(n, score_col)


def score_to_color(score: float, min_score: float = 0.0, max_score: float = 1.0) -> str:
    """
    Map a score [0,1] to a hex color using green-yellow-red colormap.

    Args:
        score: Score value between min_score and max_score
        min_score: Minimum score (default 0.0)
        max_score: Maximum score (default 1.0)

    Returns:
        Hex color string
    """
    # Normalize score to [0, 1]
    if max_score == min_score:
        normalized = 0.5
    else:
        normalized = (score - min_score) / (max_score - min_score)

    # Clamp to [0, 1]
    normalized = max(0.0, min(1.0, normalized))

    # Color mapping
    if normalized >= 0.8:
        return "#1a7a1a"  # dark green
    elif normalized >= 0.6:
        return "#4caf50"  # green
    elif normalized >= 0.4:
        return "#cddc39"  # yellow-green
    elif normalized >= 0.2:
        return "#ff9800"  # orange
    else:
        return "#f44336"  # red


def parcel_to_marker(
    row: pd.Series,
    color: str,
    score_col: str | None = None,
    popup_extra: str = ""
) -> folium.CircleMarker | None:
    """
    Create a folium.CircleMarker for a single parcel row.

    Args:
        row: Parcel row (must have geometry)
        color: Marker color
        score_col: Optional score column name (for popup display)
        popup_extra: Extra text to add to popup

    Returns:
        folium.CircleMarker or None if geometry is missing
    """
    # Get centroid
    if not hasattr(row.get("geometry"), "centroid"):
        return None

    centroid = row["geometry"].centroid
    lat, lon = centroid.y, centroid.x

    # Build popup HTML
    popup_lines = []

    if "pnu" in row:
        popup_lines.append(f"<b>PNU:</b> {row['pnu']}")

    if score_col and score_col in row and pd.notna(row[score_col]):
        popup_lines.append(f"<b>{score_col}:</b> {row[score_col]:.3f}")

    if "jimok" in row and pd.notna(row["jimok"]):
        popup_lines.append(f"<b>지목:</b> {row['jimok']}")

    if "area_m2" in row and pd.notna(row["area_m2"]):
        area_formatted = f"{row['area_m2']:,.0f}"
        popup_lines.append(f"<b>면적:</b> {area_formatted} ㎡")

    if "slope_mean" in row and pd.notna(row["slope_mean"]):
        popup_lines.append(f"<b>경사:</b> {row['slope_mean']:.1f}°")

    if "dropout_reason" in row and pd.notna(row["dropout_reason"]):
        popup_lines.append(f"<b>판정:</b> {row['dropout_reason']}")

    if popup_extra:
        popup_lines.append(popup_extra)

    popup_html = "<br>".join(popup_lines)
    popup = folium.Popup(popup_html, max_width=300)

    # Create marker
    marker = folium.CircleMarker(
        location=[lat, lon],
        radius=8,
        popup=popup,
        color=color,
        fill=True,
        fillColor=color,
        fillOpacity=0.8,
        weight=1,
    )

    return marker


# ---------------------------------------------------------------------------
# Map building
# ---------------------------------------------------------------------------

def build_map(parcels_final: gpd.GeoDataFrame) -> folium.Map:
    """
    Build interactive folium map with layer toggles.

    Args:
        parcels_final: GeoDataFrame with parcels and scores

    Returns:
        folium.Map object
    """
    # Create base map centered on Haenam-gun
    m = folium.Map(
        location=[34.574, 126.599],
        zoom_start=11,
        tiles="OpenStreetMap"
    )

    # Layer 1: 규칙기반 상위 100
    layer_rule = folium.FeatureGroup(name="규칙기반 상위 100", show=True)

    if "score_rule" in parcels_final.columns:
        top_rule = get_top_n(parcels_final, "score_rule", n=100)
        if not top_rule.empty:
            for idx, row in top_rule.iterrows():
                color = score_to_color(row["score_rule"], min_score=0.0, max_score=1.0)
                marker = parcel_to_marker(row, color, score_col="score_rule")
                if marker:
                    marker.add_to(layer_rule)
        else:
            logger.warning("No valid score_rule values found for top 100")
    else:
        logger.warning("score_rule column not found")

    layer_rule.add_to(m)

    # Layer 2: ML 상위 100
    layer_ml = folium.FeatureGroup(name="ML 상위 100", show=True)

    if "score_ml" in parcels_final.columns:
        top_ml = get_top_n(parcels_final, "score_ml", n=100)
        if not top_ml.empty:
            for idx, row in top_ml.iterrows():
                # Use blue shades for ML
                color = "#2196f3"  # bright blue
                marker = parcel_to_marker(row, color, score_col="score_ml")
                if marker:
                    marker.add_to(layer_ml)
        else:
            logger.warning("No valid score_ml values found for top 100")
    else:
        logger.warning("score_ml column not found")

    layer_ml.add_to(m)

    # Layer 3: 앙상블 상위 100
    layer_ensemble = folium.FeatureGroup(name="앙상블 상위 100", show=True)

    if "score_ensemble" in parcels_final.columns:
        top_ensemble = get_top_n(parcels_final, "score_ensemble", n=100)
        if not top_ensemble.empty:
            for idx, row in top_ensemble.iterrows():
                # Use purple for ensemble
                color = "#9c27b0"  # purple
                marker = parcel_to_marker(row, color, score_col="score_ensemble")
                if marker:
                    marker.add_to(layer_ensemble)
        else:
            logger.warning("No valid score_ensemble values found for top 100")
    else:
        logger.warning("score_ensemble column not found")

    layer_ensemble.add_to(m)

    # Layer 4: 실제 설치지 (if is_installed column exists)
    layer_installed = folium.FeatureGroup(name="실제 설치지", show=True)

    if "is_installed" in parcels_final.columns:
        installed = parcels_final[parcels_final["is_installed"].astype(bool)].copy()
        if not installed.empty:
            for idx, row in installed.iterrows():
                color = "#e53935"  # red
                popup_extra = ""
                if "install_year" in row and pd.notna(row["install_year"]):
                    popup_extra = f"<b>설치년도:</b> {int(row['install_year'])}"
                marker = parcel_to_marker(row, color, popup_extra=popup_extra)
                if marker:
                    marker.add_to(layer_installed)
        else:
            logger.info("No installed parcels found (is_installed == True)")
    else:
        logger.debug("is_installed column not found; skipping installed layer")

    layer_installed.add_to(m)

    # Add layer control
    folium.LayerControl(collapsed=False).add_to(m)

    # Add title/legend as HTML element
    title_html = """
    <div style="position:fixed;top:10px;left:50px;z-index:1000;background:white;padding:15px;border-radius:8px;box-shadow:0 2px 6px rgba(0,0,0,0.3);">
      <b>SolarFit MVP v2 — 해남군 태양광 적합지역</b><br>
      <span style="color:#1a7a1a">●</span> 규칙기반 상위 100 &nbsp;
      <span style="color:#2196f3">●</span> ML 상위 100 &nbsp;
      <span style="color:#9c27b0">●</span> 앙상블 상위 100 &nbsp;
      <span style="color:#e53935">●</span> 실제 설치지
    </div>
    """
    m.get_root().html.add_child(folium.Element(title_html))

    return m


# ---------------------------------------------------------------------------
# Main pipeline function
# ---------------------------------------------------------------------------

def generate_map(force: bool = False) -> None:
    """
    Stage 5: Generate interactive folium map.

    Loads parcels_final.parquet; if missing, tries parcels_scored_rule.parquet (fallback).
    Saves map to output/haenam_solar_map_v2.html.

    Args:
        force: If True, regenerate even if output exists
    """
    output_path = OUTPUT_DIR / "haenam_solar_map_v2.html"

    # Check if output already exists
    if output_path.exists() and not force:
        logger.info("Map already exists at %s; use --force to regenerate", output_path)
        return

    # Try to load parcels_final; fallback to parcels_scored_rule
    input_primary = OUTPUT_DIR / "parcels_final.parquet"
    input_fallback = OUTPUT_DIR / "parcels_scored_rule.parquet"

    if input_primary.exists():
        logger.info("Loading %s …", input_primary)
        gdf = gpd.read_parquet(input_primary)
    elif input_fallback.exists():
        logger.warning(
            "%s not found; using fallback %s",
            input_primary,
            input_fallback
        )
        gdf = gpd.read_parquet(input_fallback)
    else:
        raise FileNotFoundError(
            f"Neither {input_primary} nor {input_fallback} found.\n"
            "Run Stage 4 first: python -m solar_mvp.stage4_score"
        )

    total = len(gdf)
    logger.info("Loaded %d parcels", total)

    # Ensure CRS is EPSG:4326
    if gdf.crs is None:
        logger.warning("GeoDataFrame has no CRS; assuming EPSG:4326")
        gdf = gdf.set_crs(CRS_WGS84)
    elif gdf.crs != CRS_WGS84:
        logger.info("Reprojecting from %s to %s …", gdf.crs, CRS_WGS84)
        gdf = gdf.to_crs(CRS_WGS84)

    # Build map
    logger.info("Building map …")
    m = build_map(gdf)

    # Save map
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    m.save(str(output_path))
    logger.info("Map saved to %s", output_path)

    print("\n" + "=" * 60)
    print("Stage 5 — Map Generation Complete")
    print("=" * 60)
    print(f"Map saved to output/haenam_solar_map_v2.html — open in browser to view")
    print("=" * 60 + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s — %(name)s — %(levelname)s — %(message)s"
    )

    parser = argparse.ArgumentParser(
        description="Stage 5: Generate interactive folium map for SolarFit MVP v2"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate map even if output already exists"
    )
    args = parser.parse_args()

    generate_map(force=args.force)
