"""Stage 4: Rule-based hard filtering (v2) and weighted soft scoring."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd

from solar_mvp.config import (
    ALLOWED_JIMOK,
    BLOCKED_USE_ZONES,
    BLOCKED_OWNER_TYPES,
    MIN_AREA_M2,
    MAX_SLOPE_DEG,
    MAX_ELEVATION_M,
    BLOCKED_FOREST_AGES,
    REQUIRED_KW,
    HAENAM_RESIDENTIAL_BUFFER_M,
    WEIGHTS_RULE,
    FEATURES_V2,
    OUTPUT_DIR,
    GRID_SATURATION_HARD_LIMIT_KW,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hard filter — row-level (spec-exact)
# ---------------------------------------------------------------------------

def hard_filter_v2(parcel: pd.Series) -> tuple[bool, str]:
    """
    Apply all 13 hard filter conditions.
    Returns: (passes: bool, reason: str)
    'reason' is "통과" if passes, else the dropout reason string.
    """
    # === v1 기존 필터 (6개) ===
    if parcel.get("jimok") not in ALLOWED_JIMOK:
        return False, "지목"
    if parcel.get("area_m2", 0) < MIN_AREA_M2:
        return False, "면적<1000㎡"
    if parcel.get("slope_mean", 0) > MAX_SLOPE_DEG:
        return False, "경사>15°"
    if parcel.get("use_zone") in BLOCKED_USE_ZONES:
        return False, "용도지역"
    if parcel.get("intersects_protected_area", False):
        return False, "보전구역"
    if parcel.get("nearest_building_dist_m", 9999) < HAENAM_RESIDENTIAL_BUFFER_M:
        return False, "이격거리"
    # === v2 신규 필터 (7개) ===
    if parcel.get("owner_type") in BLOCKED_OWNER_TYPES:
        return False, "소유구분"
    if not parcel.get("has_road_access_3m", True):
        return False, "현황도로<3m"
    if parcel.get("in_agricultural_promotion_zone", False):
        return False, "농업진흥지역"
    if parcel.get("substation_remaining_kw", 9999) < REQUIRED_KW:
        return False, "계통포화"
    if parcel.get("forest_age_class", "") in BLOCKED_FOREST_AGES:
        return False, "임상영급"
    if parcel.get("elevation_m", 0) > MAX_ELEVATION_M:
        return False, "고도>600m"
    if parcel.get("aspect_class", "") == "북향":
        return False, "북향"
    # === v3 계통 필터 (2개) ===
    if parcel.get("intersects_hvline_buffer", False):
        return False, "고압송전선이격"
    if parcel.get("existing_solar_kw_5km", 0) >= GRID_SATURATION_HARD_LIMIT_KW:
        return False, "배전구역포화"
    return True, "통과"


# ---------------------------------------------------------------------------
# Hard filter — vectorized
# ---------------------------------------------------------------------------

def apply_hard_filter(parcels: pd.DataFrame) -> pd.DataFrame:
    """
    Apply hard_filter_v2 to all rows, adding 'passes_hard_filter' and 'dropout_reason' columns.
    Uses vectorized pandas operations, not row-by-row iteration.
    Returns DataFrame with two new columns.
    """
    parcels = parcels.copy()
    parcels["dropout_reason"] = "통과"
    parcels["passes_hard_filter"] = True

    def _apply_mask(mask: pd.Series, reason: str) -> None:
        """Mark rows that newly fail (haven't failed a prior filter) with this reason."""
        new_fail = mask & parcels["passes_hard_filter"]
        parcels.loc[new_fail, "dropout_reason"] = reason
        parcels.loc[mask, "passes_hard_filter"] = False

    # === v1 기존 필터 (6개) ===
    if "jimok" in parcels.columns:
        _apply_mask(~parcels["jimok"].isin(ALLOWED_JIMOK), "지목")
    else:
        _apply_mask(pd.Series(True, index=parcels.index), "지목")

    if "area_m2" in parcels.columns:
        _apply_mask(parcels["area_m2"].fillna(0) < MIN_AREA_M2, "면적<1000㎡")
    # if column missing, default 0 < MIN_AREA_M2 → always fails → conservative; keep optimistic: skip

    if "slope_mean" in parcels.columns:
        _apply_mask(parcels["slope_mean"].fillna(0) > MAX_SLOPE_DEG, "경사>15°")

    if "use_zone" in parcels.columns:
        _apply_mask(parcels["use_zone"].isin(BLOCKED_USE_ZONES), "용도지역")

    if "intersects_protected_area" in parcels.columns:
        _apply_mask(parcels["intersects_protected_area"].fillna(False).astype(bool), "보전구역")

    if "nearest_building_dist_m" in parcels.columns:
        _apply_mask(parcels["nearest_building_dist_m"].fillna(9999) < HAENAM_RESIDENTIAL_BUFFER_M, "이격거리")

    # === v2 신규 필터 (7개) ===
    if "owner_type" in parcels.columns:
        _apply_mask(parcels["owner_type"].isin(BLOCKED_OWNER_TYPES), "소유구분")

    if "has_road_access_3m" in parcels.columns:
        _apply_mask(~parcels["has_road_access_3m"].fillna(True).astype(bool), "현황도로<3m")

    if "in_agricultural_promotion_zone" in parcels.columns:
        _apply_mask(parcels["in_agricultural_promotion_zone"].fillna(False).astype(bool), "농업진흥지역")

    if "substation_remaining_kw" in parcels.columns:
        _apply_mask(parcels["substation_remaining_kw"].fillna(9999) < REQUIRED_KW, "계통포화")

    if "forest_age_class" in parcels.columns:
        _apply_mask(parcels["forest_age_class"].isin(BLOCKED_FOREST_AGES), "임상영급")

    if "elevation_m" in parcels.columns:
        _apply_mask(parcels["elevation_m"].fillna(0) > MAX_ELEVATION_M, "고도>600m")

    if "aspect_class" in parcels.columns:
        _apply_mask(parcels["aspect_class"] == "북향", "북향")

    # === v3 계통 필터 (2개) ===
    if "intersects_hvline_buffer" in parcels.columns:
        _apply_mask(parcels["intersects_hvline_buffer"].fillna(False).astype(bool), "고압송전선이격")

    if "existing_solar_kw_5km" in parcels.columns:
        _apply_mask(
            parcels["existing_solar_kw_5km"].fillna(0) >= GRID_SATURATION_HARD_LIMIT_KW,
            "배전구역포화",
        )

    return parcels


# ---------------------------------------------------------------------------
# Soft scoring
# ---------------------------------------------------------------------------

def compute_score_rule(parcels: pd.DataFrame) -> pd.Series:
    """
    Compute rule-based score for parcels that passed hard filter.
    Normalizes each feature to [0, 1] range across the dataset before weighting.
    Returns Series of scores (NaN for parcels that failed hard filter).

    Formula: score = sum(normalize(feature_i) * weight_i for feature_i in FEATURES_V2)
    where positive weights: higher raw value → higher normalized score
          negative weights: lower raw value → higher normalized score (1 - normalized)
    """
    scores = pd.Series(np.nan, index=parcels.index)

    passing_mask = parcels["passes_hard_filter"].astype(bool)
    passing = parcels.loc[passing_mask]

    if passing.empty:
        logger.warning("No parcels passed hard filter — score_rule will be all NaN")
        return scores

    total_abs_weight = sum(abs(w) for w in WEIGHTS_RULE.values())
    if total_abs_weight == 0:
        logger.warning("WEIGHTS_RULE sum of abs values is 0 — returning 0.5 for all passing parcels")
        scores.loc[passing_mask] = 0.5
        return scores

    weighted_sum = pd.Series(0.0, index=passing.index)

    for feature in FEATURES_V2:
        weight = WEIGHTS_RULE.get(feature, 0.0)
        if weight == 0.0:
            continue

        if feature not in passing.columns:
            logger.debug("Feature %s missing from data; skipping in score computation", feature)
            continue

        col = passing[feature].astype(float)
        if col.isna().all():
            logger.warning("Feature %s is all NaN — skipping (see data_requirements.py)", feature)
            continue
        if col.isna().any():
            col = col.fillna(col.median())

        col_min = col.min()
        col_max = col.max()

        if col_max == col_min:
            # All values identical — normalized value is 0.5 (no discrimination)
            norm = pd.Series(0.5, index=passing.index)
        else:
            norm = (col - col_min) / (col_max - col_min)

        if weight < 0:
            # Lower raw value is better → invert
            contribution = (1.0 - norm) * abs(weight)
        else:
            contribution = norm * abs(weight)

        weighted_sum += contribution

    scores.loc[passing_mask] = weighted_sum / total_abs_weight
    return scores


# ---------------------------------------------------------------------------
# Dropout statistics
# ---------------------------------------------------------------------------

def compute_dropout_stats(parcels: pd.DataFrame) -> pd.DataFrame:
    """
    Compute filter dropout statistics.
    Returns DataFrame with columns: filter_name, count, pct_of_total
    """
    total = len(parcels)
    counts = parcels["dropout_reason"].value_counts()
    rows = []
    for reason, count in counts.items():
        rows.append({
            "filter_name": reason,
            "count": int(count),
            "pct_of_total": round(count / total * 100, 2) if total > 0 else 0.0,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Main pipeline function
# ---------------------------------------------------------------------------

def score_parcels(force: bool = False) -> gpd.GeoDataFrame:
    """
    Stage 4: Apply hard filters and rule-based scoring.
    Loads parcels_enriched.parquet, applies filters, scores, saves parcels_scored_rule.parquet.
    Also saves filter_dropout_stats.csv.
    """
    output_path = OUTPUT_DIR / "parcels_scored_rule.parquet"
    stats_path = OUTPUT_DIR / "filter_dropout_stats.csv"

    if output_path.exists() and not force:
        logger.info("Stage 4 output already exists — loading cache. Use --force to rerun.")
        return gpd.read_parquet(output_path)

    input_path = OUTPUT_DIR / "parcels_enriched.parquet"
    if not input_path.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_path}\n"
            "Run Stage 3 first: python -m solar_mvp.stage3_enrich"
        )

    logger.info("Loading %s …", input_path)
    gdf = gpd.read_parquet(input_path)
    total = len(gdf)
    logger.info("Loaded %d parcels", total)

    # Hard filter
    logger.info("Applying hard_filter_v2 (13 conditions) …")
    gdf = apply_hard_filter(gdf)

    passing_count = gdf["passes_hard_filter"].sum()
    passing_pct = passing_count / total * 100 if total > 0 else 0.0
    logger.info("Passed hard filter: %d / %d (%.1f%%)", passing_count, total, passing_pct)

    # Soft scoring
    logger.info("Computing rule-based scores for %d passing parcels …", passing_count)
    gdf["score_rule"] = compute_score_rule(gdf)

    # Dropout stats
    dropout_stats = compute_dropout_stats(gdf)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    dropout_stats.to_csv(stats_path, index=False, encoding="utf-8-sig")
    logger.info("Saved dropout stats → %s", stats_path)

    # Save output
    gdf.to_parquet(output_path, index=False)
    logger.info("Saved scored parcels → %s", output_path)

    # Print summary
    print("\n" + "=" * 60)
    print("Stage 4 — Score Summary")
    print("=" * 60)
    print(f"Total parcels:         {total:,}")
    print(f"Passed hard filter:    {passing_count:,}  ({passing_pct:.1f}%)")
    print(f"Rejected:              {total - passing_count:,}  ({100 - passing_pct:.1f}%)")

    print("\n[Dropout breakdown — top 5 filters]")
    reject_stats = dropout_stats[dropout_stats["filter_name"] != "통과"].nlargest(5, "count")
    if reject_stats.empty:
        print("  (none)")
    else:
        for _, row in reject_stats.iterrows():
            print(f"  {row['filter_name']:20s}  {row['count']:6,}  ({row['pct_of_total']:.1f}%)")

    print("\n[Top 10 parcels by score_rule]")
    top10 = (
        gdf[gdf["passes_hard_filter"]]
        .nlargest(10, "score_rule")[["pnu", "score_rule"]]
        if "pnu" in gdf.columns
        else gdf[gdf["passes_hard_filter"]].nlargest(10, "score_rule")[["score_rule"]]
    )
    print(top10.to_string(index=False))
    print("=" * 60 + "\n")

    return gdf


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="Stage 4: Hard filter v2 + rule-based scoring")
    parser.add_argument("--force", action="store_true", help="Rerun even if output exists")
    args = parser.parse_args()
    score_parcels(force=args.force)
