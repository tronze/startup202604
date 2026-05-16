"""Stage 4.5: Ground truth validation and recall@K metrics."""
from __future__ import annotations

import argparse
import base64
import io
import logging
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import geopandas as gpd
from scipy import stats
from shapely.geometry import Point

from solar_mvp.config import (
    OUTPUT_DIR,
    DATA_DIR,
    RECALL_K_VALUES,
    FEATURES_V2,
    LABEL_BUFFER_M,
    SIGUNGU_CODE,
    CRS_WGS84,
    CRS_ANALYSIS,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Synthetic ground truth fallback
# ---------------------------------------------------------------------------

SYNTHETIC_SOLAR_PLANTS = [
    {"lat": 34.573, "lon": 126.599, "install_year": 2018, "capacity_kw": 500},
    {"lat": 34.452, "lon": 126.641, "install_year": 2019, "capacity_kw": 1000},
    {"lat": 34.634, "lon": 126.507, "install_year": 2017, "capacity_kw": 300},
    {"lat": 34.492, "lon": 126.706, "install_year": 2020, "capacity_kw": 2000},
    {"lat": 34.583, "lon": 126.653, "install_year": 2016, "capacity_kw": 800},
    {"lat": 34.622, "lon": 126.729, "install_year": 2021, "capacity_kw": 1500},
    {"lat": 34.539, "lon": 126.735, "install_year": 2018, "capacity_kw": 400},
    {"lat": 34.657, "lon": 126.551, "install_year": 2019, "capacity_kw": 600},
    {"lat": 34.631, "lon": 126.672, "install_year": 2022, "capacity_kw": 2500},
    {"lat": 34.518, "lon": 126.580, "install_year": 2020, "capacity_kw": 750},
    {"lat": 34.603, "lon": 126.620, "install_year": 2017, "capacity_kw": 1200},
    {"lat": 34.469, "lon": 126.663, "install_year": 2021, "capacity_kw": 900},
    {"lat": 34.551, "lon": 126.615, "install_year": 2023, "capacity_kw": 300},
    {"lat": 34.490, "lon": 126.590, "install_year": 2016, "capacity_kw": 1800},
    {"lat": 34.648, "lon": 126.633, "install_year": 2022, "capacity_kw": 450},
    {"lat": 34.421, "lon": 126.700, "install_year": 2019, "capacity_kw": 1100},
    {"lat": 34.575, "lon": 126.640, "install_year": 2018, "capacity_kw": 650},
    {"lat": 34.522, "lon": 126.545, "install_year": 2020, "capacity_kw": 2200},
    {"lat": 34.680, "lon": 126.572, "install_year": 2023, "capacity_kw": 380},
    {"lat": 34.400, "lon": 126.650, "install_year": 2015, "capacity_kw": 1600},
]

# ---------------------------------------------------------------------------
# Column name normalization maps
# ---------------------------------------------------------------------------

_LAT_COLS = {"lat", "위도", "latitude", "y"}
_LON_COLS = {"lon", "경도", "longitude", "x"}
_PNU_COLS = {"pnu", "필지고유번호", "pnu_code"}
_YEAR_COLS = {"install_year", "준공년도", "completion_year"}
_CAP_COLS = {"capacity_kw", "설비용량", "capacity", "kw"}


def _find_col(df: pd.DataFrame, candidates: set[str]) -> Optional[str]:
    """Return the first column name found in df whose lower-stripped form matches candidates."""
    for col in df.columns:
        if col.strip().lower() in candidates or col.strip() in candidates:
            return col
    return None


# ---------------------------------------------------------------------------
# 1. load_solar_plants
# ---------------------------------------------------------------------------

def load_solar_plants(data_path: Optional[Path] = None) -> pd.DataFrame:
    """Load solar plant ground truth from CSV or fall back to synthetic data.

    Returns DataFrame with columns: lat, lon, install_year, capacity_kw
    and optionally pnu if available in source.
    """
    if data_path is None:
        data_path = DATA_DIR / "haenam_solar_plants.csv"

    if data_path.exists():
        logger.info("Loading real ground truth from %s", data_path)
        df = pd.read_csv(data_path, encoding="utf-8-sig")

        # Normalise column names
        rename_map: dict[str, str] = {}

        lat_col = _find_col(df, _LAT_COLS)
        if lat_col and lat_col != "lat":
            rename_map[lat_col] = "lat"

        lon_col = _find_col(df, _LON_COLS)
        if lon_col and lon_col != "lon":
            rename_map[lon_col] = "lon"

        pnu_col = _find_col(df, _PNU_COLS)
        if pnu_col and pnu_col != "pnu":
            rename_map[pnu_col] = "pnu"

        year_col = _find_col(df, _YEAR_COLS)
        if year_col and year_col != "install_year":
            rename_map[year_col] = "install_year"

        cap_col = _find_col(df, _CAP_COLS)
        if cap_col and cap_col != "capacity_kw":
            rename_map[cap_col] = "capacity_kw"

        if rename_map:
            df = df.rename(columns=rename_map)

        # Ensure required columns exist
        for col in ("lat", "lon", "install_year", "capacity_kw"):
            if col not in df.columns:
                logger.warning("Column %s missing from ground truth CSV; filling with NaN", col)
                df[col] = np.nan

        logger.info("Loaded %d real solar plants", len(df))
        return df
    else:
        logger.warning(
            "Ground truth CSV not found at %s — using %d synthetic plants for testing",
            data_path,
            len(SYNTHETIC_SOLAR_PLANTS),
        )
        return pd.DataFrame(SYNTHETIC_SOLAR_PLANTS)


# ---------------------------------------------------------------------------
# 2. map_plants_to_pnu
# ---------------------------------------------------------------------------

def map_plants_to_pnu(
    plants_df: pd.DataFrame,
    parcels_gdf: gpd.GeoDataFrame,
    buffer_m: float = LABEL_BUFFER_M,
) -> pd.DataFrame:
    """Spatially match each plant to the nearest parcel PNU within buffer_m metres.

    If the plant already has a 'pnu' column, that is used directly (after verifying
    it exists in parcels_gdf). Otherwise sjoin_nearest is used in the projected CRS.

    Returns plants_df with an extra 'matched_pnu' column (NaN if no match).
    """
    plants_df = plants_df.copy()
    plants_df["matched_pnu"] = np.nan

    # Build a geometry column for plants
    valid_mask = plants_df["lat"].notna() & plants_df["lon"].notna()
    plants_with_geom = plants_df[valid_mask].copy()

    if plants_with_geom.empty:
        logger.warning("No plants with valid lat/lon; nothing matched")
        return plants_df

    plants_gdf = gpd.GeoDataFrame(
        plants_with_geom,
        geometry=[
            Point(row["lon"], row["lat"]) for _, row in plants_with_geom.iterrows()
        ],
        crs=CRS_WGS84,
    )

    # Case 1: Plants already have PNU — use directly
    if "pnu" in plants_df.columns:
        known_pnus = set(parcels_gdf["pnu"].dropna().astype(str))
        direct_mask = plants_gdf["pnu"].notna()
        direct_plants = plants_gdf[direct_mask].copy()
        remaining_plants = plants_gdf[~direct_mask].copy()

        for idx, row in direct_plants.iterrows():
            pnu_str = str(row["pnu"])
            if pnu_str in known_pnus:
                plants_df.at[idx, "matched_pnu"] = pnu_str
            else:
                logger.debug("PNU %s from ground truth not found in parcels; will try spatial match", pnu_str)
                remaining_plants = pd.concat(
                    [remaining_plants, direct_plants.loc[[idx]]]
                )
    else:
        remaining_plants = plants_gdf.copy()

    # Case 2: Spatial nearest-parcel match
    if remaining_plants.empty:
        n_matched = plants_df["matched_pnu"].notna().sum()
        n_total = len(plants_df)
        logger.info("Matched %d / %d plants via direct PNU; no spatial matching needed", n_matched, n_total)
        return plants_df

    # Reproject to metric CRS for distance-based join
    parcels_proj = parcels_gdf[["pnu", "geometry"]].to_crs(CRS_ANALYSIS)
    plants_proj = remaining_plants.to_crs(CRS_ANALYSIS)

    # sjoin_nearest returns the nearest parcel for each plant
    joined = gpd.sjoin_nearest(
        plants_proj,
        parcels_proj,
        how="left",
        max_distance=buffer_m,
        distance_col="_dist_m",
    )

    for orig_idx, group in joined.groupby(joined.index):
        # Take the closest match (sjoin_nearest may return multiple if ties)
        best = group.nsmallest(1, "_dist_m").iloc[0]
        if pd.notna(best.get("pnu_right", np.nan)):
            plants_df.at[orig_idx, "matched_pnu"] = str(best["pnu_right"])

    n_matched = plants_df["matched_pnu"].notna().sum()
    n_total = len(plants_df)
    n_unmatched = n_total - n_matched
    logger.info(
        "Plant-to-PNU spatial match: %d matched, %d unmatched (buffer=%.0fm)",
        n_matched,
        n_unmatched,
        buffer_m,
    )
    return plants_df


# ---------------------------------------------------------------------------
# 3. label_parcels
# ---------------------------------------------------------------------------

def label_parcels(
    parcels_gdf: gpd.GeoDataFrame,
    matched_pnus: set[str],
    plants_df: Optional[pd.DataFrame] = None,
) -> gpd.GeoDataFrame:
    """Add is_installed and install_year columns to parcels_gdf.

    Parameters
    ----------
    parcels_gdf : GeoDataFrame with 'pnu' column
    matched_pnus : set of PNU strings that have an installed plant
    plants_df : optional; if provided and has 'matched_pnu' + 'install_year', sets per-PNU year

    Returns
    -------
    GeoDataFrame with new bool column 'is_installed' and int/NaN column 'install_year'
    """
    parcels_gdf = parcels_gdf.copy()
    parcels_gdf["pnu"] = parcels_gdf["pnu"].astype(str)
    parcels_gdf["is_installed"] = parcels_gdf["pnu"].isin(matched_pnus)

    # Build PNU → min install_year mapping
    pnu_year: dict[str, int] = {}
    if plants_df is not None and "matched_pnu" in plants_df.columns and "install_year" in plants_df.columns:
        matched = plants_df.dropna(subset=["matched_pnu", "install_year"])
        for _, row in matched.iterrows():
            pnu = str(row["matched_pnu"])
            year = int(row["install_year"])
            if pnu not in pnu_year or year < pnu_year[pnu]:
                pnu_year[pnu] = year

    parcels_gdf["install_year"] = parcels_gdf["pnu"].map(pnu_year)

    n_installed = parcels_gdf["is_installed"].sum()
    logger.info(
        "Labelled parcels: %d installed (%.2f%% of %d total)",
        n_installed,
        100.0 * n_installed / len(parcels_gdf) if len(parcels_gdf) > 0 else 0.0,
        len(parcels_gdf),
    )
    return parcels_gdf


# ---------------------------------------------------------------------------
# 4. analyze_filter_dropout
# ---------------------------------------------------------------------------

def analyze_filter_dropout(parcels: gpd.GeoDataFrame) -> pd.DataFrame:
    """Show dropout_reason distribution for INSTALLED parcels.

    Returns DataFrame with: filter_name, n_installed_dropped, pct_of_installed
    """
    installed = parcels[parcels["is_installed"].astype(bool)]
    n_installed = len(installed)

    if n_installed == 0:
        logger.warning("No installed parcels found; dropout analysis is empty")
        return pd.DataFrame(columns=["filter_name", "n_installed_dropped", "pct_of_installed"])

    counts = installed["dropout_reason"].value_counts()
    rows = []
    for reason, count in counts.items():
        rows.append({
            "filter_name": reason,
            "n_installed_dropped": int(count),
            "pct_of_installed": round(100.0 * count / n_installed, 2),
        })
    df = pd.DataFrame(rows)
    logger.info(
        "Installed parcel dropout analysis:\n%s",
        df.to_string(index=False),
    )
    return df


# ---------------------------------------------------------------------------
# 5. compute_recall_at_k
# ---------------------------------------------------------------------------

def compute_recall_at_k(
    parcels: gpd.GeoDataFrame,
    k_values: Optional[list[int]] = None,
) -> dict[int, float]:
    """Compute recall@K for each k in k_values.

    ALL parcels (passing and failing) are sorted by score_rule descending (NaN last).
    Recall@K = (installed parcels in top-K) / (total installed parcels)
    """
    if k_values is None:
        k_values = RECALL_K_VALUES

    total_installed = int(parcels["is_installed"].astype(bool).sum())
    if total_installed == 0:
        logger.warning("No installed parcels; recall@K will be 0 for all K")
        return {k: 0.0 for k in k_values}

    # Sort: non-NaN scores descending first, then NaN rows at the end
    sorted_parcels = parcels.sort_values("score_rule", ascending=False, na_position="last")

    recall_dict: dict[int, float] = {}
    for k in k_values:
        top_k = sorted_parcels.iloc[:k]
        n_installed_in_top_k = int(top_k["is_installed"].astype(bool).sum())
        recall = n_installed_in_top_k / total_installed
        recall_dict[k] = round(recall, 4)
        logger.info("Recall@%d = %.4f (%d / %d)", k, recall, n_installed_in_top_k, total_installed)

    return recall_dict


# ---------------------------------------------------------------------------
# 6. compute_score_distribution_test
# ---------------------------------------------------------------------------

def compute_score_distribution_test(parcels: gpd.GeoDataFrame) -> dict:
    """Mann-Whitney U test: installed vs non-installed score_rule distribution.

    Returns dict with statistic, pvalue, and interpretation string.
    """
    valid = parcels.dropna(subset=["score_rule"])
    installed_scores = valid[valid["is_installed"].astype(bool)]["score_rule"].values
    non_installed_scores = valid[~valid["is_installed"].astype(bool)]["score_rule"].values

    if len(installed_scores) == 0 or len(non_installed_scores) == 0:
        return {
            "statistic": float("nan"),
            "pvalue": float("nan"),
            "interpretation": "insufficient data for test",
        }

    result = stats.mannwhitneyu(
        installed_scores,
        non_installed_scores,
        alternative="greater",  # test: installed > non-installed
    )
    statistic = float(result.statistic)
    pvalue = float(result.pvalue)

    if pvalue < 0.05:
        interpretation = "installed parcels score significantly higher (p<0.05)"
    else:
        interpretation = "no significant difference"

    logger.info(
        "Mann-Whitney U: statistic=%.2f, p=%.4f → %s",
        statistic,
        pvalue,
        interpretation,
    )
    return {
        "statistic": statistic,
        "pvalue": pvalue,
        "interpretation": interpretation,
    }


# ---------------------------------------------------------------------------
# 7. plot_feature_distributions
# ---------------------------------------------------------------------------

def plot_feature_distributions(
    parcels: gpd.GeoDataFrame,
    output_path: Path,
) -> None:
    """Boxplots comparing each FEATURES_V2 feature for installed vs not-installed parcels.

    Only uses passing parcels (passes_hard_filter == True) for a cleaner comparison.
    Saves PNG to output_path.
    """
    passing = parcels[parcels["passes_hard_filter"].astype(bool)].copy()

    # Only include features actually present in the data
    available_features = [f for f in FEATURES_V2 if f in passing.columns]

    if not available_features:
        logger.warning("No FEATURES_V2 columns found in parcel data; skipping feature distribution plot")
        return

    n_features = len(available_features)
    ncols = 3
    nrows = (n_features + ncols - 1) // ncols

    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(5 * ncols, 4 * nrows))
    axes_flat = np.array(axes).flatten() if n_features > 1 else [axes]

    installed_label = "Installed"
    not_installed_label = "Not installed"

    for i, feature in enumerate(available_features):
        ax = axes_flat[i]

        installed_vals = passing[passing["is_installed"].astype(bool)][feature].dropna().values
        not_installed_vals = passing[~passing["is_installed"].astype(bool)][feature].dropna().values

        data_to_plot = []
        labels = []
        colors = []

        if len(not_installed_vals) > 0:
            data_to_plot.append(not_installed_vals)
            labels.append(not_installed_label)
            colors.append("#FFA500")  # orange

        if len(installed_vals) > 0:
            data_to_plot.append(installed_vals)
            labels.append(installed_label)
            colors.append("#1F77B4")  # blue

        if data_to_plot:
            bp = ax.boxplot(data_to_plot, patch_artist=True, notch=False, showfliers=False)
            for patch, color in zip(bp["boxes"], colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)
        else:
            ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)

        ax.set_title(feature, fontsize=9)
        ax.set_xticks(range(1, len(labels) + 1))
        ax.set_xticklabels(labels, fontsize=8)
        ax.tick_params(axis="y", labelsize=7)

    # Hide empty subplots
    for j in range(n_features, len(axes_flat)):
        axes_flat[j].set_visible(False)

    fig.suptitle("Feature Distributions: Installed vs Not-Installed Parcels\n(passing hard filter only)", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.97])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved feature distribution plot → %s", output_path)


# ---------------------------------------------------------------------------
# Helper: inline score histogram PNG
# ---------------------------------------------------------------------------

def _make_score_histogram_b64(parcels: gpd.GeoDataFrame) -> str:
    """Generate a score distribution histogram as a base64-encoded PNG string."""
    valid = parcels.dropna(subset=["score_rule"])
    installed = valid[valid["is_installed"].astype(bool)]["score_rule"].values
    not_installed = valid[~valid["is_installed"].astype(bool)]["score_rule"].values

    fig, ax = plt.subplots(figsize=(7, 3.5))
    bins = np.linspace(0, 1, 40)

    if len(not_installed) > 0:
        ax.hist(not_installed, bins=bins, alpha=0.6, color="#FFA500", label="Not installed", density=True)
    if len(installed) > 0:
        ax.hist(installed, bins=bins, alpha=0.7, color="#1F77B4", label="Installed", density=True)

    ax.set_xlabel("score_rule")
    ax.set_ylabel("Density")
    ax.set_title("Score Distribution: Installed vs Not-Installed")
    ax.legend()
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


# ---------------------------------------------------------------------------
# 8. generate_validation_report
# ---------------------------------------------------------------------------

def generate_validation_report(
    parcels: gpd.GeoDataFrame,
    recall_dict: dict[int, float],
    mwu_result: dict,
    dropout_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Generate a self-contained HTML validation report."""

    total_parcels = len(parcels)
    n_installed = int(parcels["is_installed"].astype(bool).sum())
    n_passing = int(parcels["passes_hard_filter"].astype(bool).sum())
    installed_passing = int(
        (parcels["is_installed"].astype(bool) & parcels["passes_hard_filter"].astype(bool)).sum()
    )

    # Recall@K table rows
    recall_rows = "".join(
        f"<tr><td>Recall@{k}</td><td>{v:.4f} ({v*100:.1f}%)</td></tr>"
        for k, v in sorted(recall_dict.items())
    )

    # Dropout table rows
    dropout_rows = ""
    for _, row in dropout_df.iterrows():
        warn_class = ' class="warn"' if row["filter_name"] != "통과" else ""
        dropout_rows += (
            f"<tr{warn_class}><td>{row['filter_name']}</td>"
            f"<td>{row['n_installed_dropped']}</td>"
            f"<td>{row['pct_of_installed']:.1f}%</td></tr>"
        )

    # Top 20 installed parcels
    installed_parcels = parcels[parcels["is_installed"].astype(bool)].copy()
    installed_parcels["_rank"] = (
        parcels.sort_values("score_rule", ascending=False, na_position="last")
        .reset_index(drop=True)
        .index[parcels.sort_values("score_rule", ascending=False, na_position="last")
               ["is_installed"].astype(bool)]
        if False  # skip complex rank calc; use simpler approach below
        else np.nan
    )

    sorted_all = parcels.sort_values("score_rule", ascending=False, na_position="last").reset_index()
    sorted_all["_rank"] = range(1, len(sorted_all) + 1)
    top20_installed = (
        sorted_all[sorted_all["is_installed"].astype(bool)]
        .head(20)[["_rank", "pnu", "score_rule", "passes_hard_filter", "dropout_reason"]]
    )

    top20_rows = ""
    for _, row in top20_installed.iterrows():
        score_str = f"{row['score_rule']:.4f}" if pd.notna(row["score_rule"]) else "N/A"
        passes_str = "Yes" if row["passes_hard_filter"] else "No"
        pnu_val = row.get("pnu", "N/A")
        top20_rows += (
            f"<tr><td>{int(row['_rank'])}</td>"
            f"<td>{pnu_val}</td>"
            f"<td>{score_str}</td>"
            f"<td>{passes_str}</td>"
            f"<td>{row['dropout_reason']}</td></tr>"
        )

    # Inline histogram
    hist_b64 = _make_score_histogram_b64(parcels)

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>Solar MVP — Ground Truth Validation Report</title>
<style>
  body {{ font-family: Arial, sans-serif; font-size: 14px; margin: 32px; color: #222; }}
  h1 {{ background: #1a4a7a; color: #fff; padding: 16px 20px; border-radius: 4px; }}
  h2 {{ color: #1a4a7a; border-bottom: 2px solid #1a4a7a; padding-bottom: 4px; margin-top: 32px; }}
  table {{ border-collapse: collapse; width: 100%; max-width: 760px; margin: 12px 0; }}
  th {{ background: #1a4a7a; color: #fff; padding: 8px 12px; text-align: left; }}
  td {{ padding: 7px 12px; border: 1px solid #ccc; }}
  tr:nth-child(even) {{ background: #f5f7fa; }}
  tr.warn td {{ background: #fff3cd; color: #856404; font-weight: bold; }}
  .metric {{ display: inline-block; background: #e8f0fe; border-radius: 6px;
             padding: 12px 20px; margin: 8px 8px 8px 0; text-align: center; min-width: 140px; }}
  .metric .val {{ font-size: 24px; font-weight: bold; color: #1a4a7a; }}
  .metric .lbl {{ font-size: 11px; color: #555; }}
  .sig {{ color: #d73027; font-weight: bold; }}
  .notsig {{ color: #4a7a1a; }}
  img {{ max-width: 100%; border: 1px solid #ddd; border-radius: 4px; margin-top: 8px; }}
  .note {{ font-size: 12px; color: #888; margin-top: 4px; }}
</style>
</head>
<body>
<h1>SolarFit MVP — Ground Truth Validation Report</h1>
<p>Region: 해남군 (SIGUNGU_CODE={SIGUNGU_CODE}) &nbsp;|&nbsp; Label buffer: {LABEL_BUFFER_M}m</p>

<h2>1. Summary</h2>
<div>
  <div class="metric"><div class="val">{total_parcels:,}</div><div class="lbl">Total parcels</div></div>
  <div class="metric"><div class="val">{n_passing:,}</div><div class="lbl">Passed hard filter</div></div>
  <div class="metric"><div class="val">{n_installed:,}</div><div class="lbl">Installed (GT) parcels</div></div>
  <div class="metric"><div class="val">{installed_passing:,}</div><div class="lbl">Installed AND passing filter</div></div>
</div>

<h3>Recall@K</h3>
<table>
  <tr><th>Metric</th><th>Value</th></tr>
  {recall_rows}
</table>
<p class="note">
  Recall@K = (installed parcels in top-K by score_rule) / (total installed parcels).
  NaN-scored parcels (failed hard filter) rank last.
</p>

<h2>2. Score Distribution Test (Mann-Whitney U)</h2>
<p>
  Comparing score_rule of installed vs non-installed parcels (passing hard filter only used for scoring):
</p>
<table>
  <tr><th>Statistic</th><th>P-value</th><th>Interpretation</th></tr>
  <tr>
    <td>{mwu_result['statistic']:.2f}</td>
    <td>{mwu_result['pvalue']:.4f}</td>
    <td class="{'sig' if mwu_result['pvalue'] < 0.05 else 'notsig'}">{mwu_result['interpretation']}</td>
  </tr>
</table>

<h2>3. Filter Dropout Analysis (Installed Parcels)</h2>
<p>
  Shows how many of the <strong>{n_installed}</strong> installed parcels were rejected by each hard filter.
  Rows highlighted in yellow indicate filters that are dropping actually-installed parcels
  and may warrant threshold review.
</p>
<table>
  <tr><th>Filter</th><th>Installed dropped</th><th>% of installed</th></tr>
  {dropout_rows if dropout_rows else '<tr><td colspan="3">No data</td></tr>'}
</table>

<h2>4. Score Distribution Histogram</h2>
<img src="data:image/png;base64,{hist_b64}" alt="Score distribution histogram" />

<h2>5. Top 20 Installed Parcels by Score Rank</h2>
<table>
  <tr><th>Rank</th><th>PNU</th><th>score_rule</th><th>Passes filter</th><th>Dropout reason</th></tr>
  {top20_rows if top20_rows else '<tr><td colspan="5">No installed parcels found</td></tr>'}
</table>

</body>
</html>
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    logger.info("Saved validation report → %s", output_path)


# ---------------------------------------------------------------------------
# 9. validate_ground_truth (main orchestration function)
# ---------------------------------------------------------------------------

def validate_ground_truth(force: bool = False) -> gpd.GeoDataFrame:
    """Stage 4.5: Ground truth validation.

    Loads parcels_scored_rule.parquet, labels with ground truth data,
    computes recall@K, generates HTML report, and saves parcels_validated.parquet.

    Parameters
    ----------
    force : bool
        If True, re-run even if outputs already exist.

    Returns
    -------
    GeoDataFrame with added is_installed column (parcels_validated.parquet).
    """
    report_path = OUTPUT_DIR / "validation_report.html"
    dropout_gt_path = OUTPUT_DIR / "filter_dropout_stats_gt.csv"
    feature_dist_path = OUTPUT_DIR / "feature_distribution.png"
    validated_path = OUTPUT_DIR / "parcels_validated.parquet"

    if report_path.exists() and validated_path.exists() and not force:
        logger.info(
            "Stage 4.5 outputs already exist — loading cached results. Use --force to rerun."
        )
        return gpd.read_parquet(validated_path)

    # --- Load scored parcels ---
    scored_path = OUTPUT_DIR / "parcels_scored_rule.parquet"
    if not scored_path.exists():
        raise FileNotFoundError(
            f"Input file not found: {scored_path}\n"
            "Run Stage 4 first: python -m solar_mvp.stage4_score"
        )

    logger.info("Loading scored parcels from %s …", scored_path)
    parcels = gpd.read_parquet(scored_path)
    logger.info("Loaded %d parcels", len(parcels))

    # --- Load ground truth ---
    plants_df = load_solar_plants()

    # --- Map plants to PNUs ---
    plants_df = map_plants_to_pnu(plants_df, parcels, buffer_m=LABEL_BUFFER_M)

    matched_pnus: set[str] = set(
        plants_df["matched_pnu"].dropna().astype(str).unique()
    )
    logger.info("Unique matched PNUs: %d", len(matched_pnus))

    # --- Label parcels ---
    parcels = label_parcels(parcels, matched_pnus, plants_df=plants_df)

    # --- Analyse filter dropout for installed parcels ---
    dropout_df = analyze_filter_dropout(parcels)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    dropout_df.to_csv(dropout_gt_path, index=False, encoding="utf-8-sig")
    logger.info("Saved installed-parcel dropout stats → %s", dropout_gt_path)

    # --- Recall@K ---
    recall_dict = compute_recall_at_k(parcels)

    # --- Score distribution test ---
    mwu_result = compute_score_distribution_test(parcels)

    # --- Feature distribution plot ---
    plot_feature_distributions(parcels, feature_dist_path)

    # --- HTML report ---
    generate_validation_report(
        parcels=parcels,
        recall_dict=recall_dict,
        mwu_result=mwu_result,
        dropout_df=dropout_df,
        output_path=report_path,
    )

    # --- Save validated parcels (scored + is_installed) ---
    parcels.to_parquet(validated_path, index=False)
    logger.info("Saved validated parcels → %s", validated_path)

    # --- Summary printout ---
    n_installed = int(parcels["is_installed"].astype(bool).sum())
    print("\n" + "=" * 60)
    print("Stage 4.5 — Ground Truth Validation Summary")
    print("=" * 60)
    print(f"Total parcels:       {len(parcels):,}")
    print(f"Installed (GT):      {n_installed:,}")
    print(f"Matched PNUs:        {len(matched_pnus)}")
    print()
    print("[Recall@K]")
    for k, v in sorted(recall_dict.items()):
        print(f"  Recall@{k:<5} = {v:.4f} ({v*100:.1f}%)")
    print()
    print(f"[Mann-Whitney U] {mwu_result['interpretation']}")
    print(f"  p = {mwu_result['pvalue']:.4f}")
    print()
    print("[Installed parcel filter dropout]")
    if not dropout_df.empty:
        for _, row in dropout_df.iterrows():
            if row["filter_name"] != "통과":
                print(
                    f"  {row['filter_name']:20s}  {row['n_installed_dropped']:4}  ({row['pct_of_installed']:.1f}%)"
                )
    print()
    print(f"Report:    {report_path}")
    print(f"Validated: {validated_path}")
    print("=" * 60 + "\n")

    return parcels


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="Stage 4.5: Ground truth validation and recall@K")
    parser.add_argument("--force", action="store_true", help="Rerun even if outputs already exist")
    args = parser.parse_args()
    validate_ground_truth(force=args.force)
