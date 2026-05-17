"""Generate synthetic Haenam-gun parcel data for local testing."""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box

from solar_mvp.config import OUTPUT_DIR, FEATURES_V2

N = 1000
SEED = 42


def generate_synthetic_parcels(n: int = N, seed: int = SEED) -> gpd.GeoDataFrame:
    """Generate n synthetic parcels with all required columns."""
    rng = np.random.default_rng(seed)

    # --- Grid layout ---
    lats = np.linspace(34.38, 34.68, 32)  # 32 rows
    lons = np.linspace(126.47, 126.78, 32)  # 32 cols → 1024 total, use first n
    lat_grid, lon_grid = np.meshgrid(lats, lons, indexing="ij")
    lat_flat = lat_grid.flatten()[:n]
    lon_flat = lon_grid.flatten()[:n]

    # --- FEATURES_V2 columns ---
    slope_mean = np.clip(rng.normal(8, 5, n), 0, 45)
    slope_std = np.clip(rng.normal(2, 1.5, n), 0, 10)
    aspect_south = rng.choice([0, 1], n, p=[0.65, 0.35])
    annual_ghi = np.clip(rng.normal(1400, 60, n), 1100, 1700)
    area_m2 = np.exp(rng.normal(8.5, 0.8, n))
    dist_to_substation_km = np.clip(rng.exponential(8, n), 0.5, 40)
    substation_remaining_kw = rng.choice([5000, 8000, 15000, 20000], n)
    dist_to_road_m = np.clip(rng.exponential(150, n), 0, 2000)
    nearest_building_dist_m = np.clip(rng.exponential(400, n), 10, 3000)
    official_land_price = np.exp(rng.normal(9.5, 0.6, n))
    elevation_m = np.clip(rng.normal(120, 80, n), 0, 700)

    # --- Hard filter input columns ---
    jimok = rng.choice(
        ["임야", "전", "답", "잡종지", "목장용지", "대", "공장용지"],
        n,
        p=[0.35, 0.20, 0.15, 0.10, 0.05, 0.10, 0.05],
    )
    use_zone = rng.choice(
        ["계획관리지역", "생산관리지역", "농림지역", "자연환경보전지역", "보전산지"],
        n,
        p=[0.50, 0.20, 0.15, 0.08, 0.07],
    )
    owner_type = rng.choice(
        ["사유", "국유", "공유", "종중"],
        n,
        p=[0.80, 0.10, 0.06, 0.04],
    )
    has_road_access_3m = (dist_to_road_m < 50).astype(bool)
    in_agricultural_promotion_zone = rng.random(n) < 0.08
    intersects_protected_area = rng.random(n) < 0.05

    # --- forest_age_class: only for 임야, empty string for others ---
    forest_age_class = np.full(n, "", dtype=object)
    forest_mask = jimok == "임야"
    n_forest = int(forest_mask.sum())
    if n_forest > 0:
        forest_age_class[forest_mask] = rng.choice(
            ["I", "II", "III", "IV", "V", "VI"],
            size=n_forest,
            p=[0.20, 0.25, 0.20, 0.15, 0.12, 0.08],
        )

    # --- 계통 피처 (한전 관련) ---
    # dist_to_powerline_m: 대체로 도로 근처(배전주 따라 설치), 약간 노이즈 추가
    dist_to_powerline_m = np.clip(dist_to_road_m * rng.uniform(0.8, 1.2, n) + rng.exponential(30, n), 0, 3000)

    # existing_solar_kw_5km: 반경 5km 기존 설치량. 대부분 낮고 일부 포화 지역 존재
    existing_solar_kw_5km = np.clip(
        rng.exponential(3000, n),  # 중앙값 ~3 MW
        0, 80_000,                 # 최대 80 MW (포화 시나리오 포함)
    )

    # intersects_hvline_buffer: 약 3% 필지가 고압선 이격거리 내 위치
    intersects_hvline_buffer = rng.random(n) < 0.03

    # grid_saturation_ratio (표시용 — FEATURES_V2 아님)
    grid_saturation_ratio = existing_solar_kw_5km / np.clip(substation_remaining_kw, 1, None)

    # --- aspect_class: consistent with aspect_south ---
    aspect_class = np.where(
        aspect_south == 1,
        "남향",
        rng.choice(["동향", "서향", "북향"], n, p=[0.35, 0.35, 0.30]),
    )

    # --- Administrative columns ---
    eup_myeon_options = [
        "해남읍", "삼산면", "화산면", "현산면", "송지면", "북평면",
        "북일면", "옥천면", "계곡면", "마산면", "황산면", "산이면",
        "문내면", "화원면",
    ]
    eup_myeon = rng.choice(eup_myeon_options, n)
    jibun_address = [f"전남 해남군 {eup_myeon[i]} {i + 1}" for i in range(n)]

    # --- PNU: 14-digit string "46810" + zero-padded 9-digit sequential ---
    pnu = [f"46810{str(i + 1).zfill(9)}" for i in range(n)]

    # --- Build DataFrame ---
    df = pd.DataFrame(
        {
            "pnu": pnu,
            "jibun_address": jibun_address,
            "eup_myeon": eup_myeon,
            # FEATURES_V2
            "slope_mean": slope_mean,
            "slope_std": slope_std,
            "aspect_south": aspect_south,
            "annual_ghi": annual_ghi,
            "area_m2": area_m2,
            "dist_to_substation_km": dist_to_substation_km,
            "substation_remaining_kw": substation_remaining_kw,
            "dist_to_road_m": dist_to_road_m,
            "nearest_building_dist_m": nearest_building_dist_m,
            "official_land_price": official_land_price,
            "elevation_m": elevation_m,
            # 계통 피처 (한전 관련)
            "dist_to_powerline_m": dist_to_powerline_m,
            "existing_solar_kw_5km": existing_solar_kw_5km,
            "grid_saturation_ratio": grid_saturation_ratio,
            # Hard filter inputs
            "jimok": jimok,
            "use_zone": use_zone,
            "owner_type": owner_type,
            "has_road_access_3m": has_road_access_3m,
            "in_agricultural_promotion_zone": in_agricultural_promotion_zone,
            "intersects_protected_area": intersects_protected_area,
            "intersects_hvline_buffer": intersects_hvline_buffer,
            "forest_age_class": forest_age_class,
            "aspect_class": aspect_class,
        }
    )

    # --- Apply hard filter and rule score ---
    from solar_mvp.stage4_score import apply_hard_filter, compute_score_rule

    df = apply_hard_filter(df)
    df["score_rule"] = compute_score_rule(df)

    # --- Add 20 installed ground truth parcels ---
    passing_idx = df[df["passes_hard_filter"] == True].index
    installed_idx = rng.choice(
        passing_idx, size=min(20, len(passing_idx)), replace=False
    )
    df["is_installed"] = False
    df.loc[installed_idx, "is_installed"] = True
    df["install_year"] = np.nan
    df.loc[installed_idx, "install_year"] = rng.choice(
        range(2015, 2024), size=len(installed_idx)
    )

    # --- Build geometry ---
    geometries = [
        box(lon_flat[i], lat_flat[i], lon_flat[i] + 0.001, lat_flat[i] + 0.001)
        for i in range(n)
    ]

    gdf = gpd.GeoDataFrame(df, geometry=geometries, crs="EPSG:4326")
    return gdf


def save_test_data(force: bool = False) -> None:
    """Generate and save synthetic parquet files to output/."""
    scored_path = OUTPUT_DIR / "parcels_scored_rule.parquet"
    validated_path = OUTPUT_DIR / "parcels_validated.parquet"

    if scored_path.exists() and validated_path.exists() and not force:
        print("Already exists, use --force to regenerate")
        return

    gdf = generate_synthetic_parcels()

    OUTPUT_DIR.mkdir(exist_ok=True)

    # Stage 4 output (used by Stage 4.5)
    gdf.to_parquet(scored_path)

    # Stage 4.5 output (used by Stage 4.6) — add score_ml placeholder
    gdf["score_ml"] = np.nan
    gdf["score_ensemble"] = np.nan
    gdf.to_parquet(validated_path)

    print(f"Generated {N} synthetic parcels")
    print(f"  Passing hard filter: {gdf['passes_hard_filter'].sum()}")
    print(f"  Installed (ground truth): {gdf['is_installed'].sum()}")
    print(f"  Saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic test data")
    parser.add_argument("--n", type=int, default=N)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    save_test_data(force=args.force)
