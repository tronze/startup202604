# SolarFit MVP

Detect and score solar-suitable land parcels in Haenam-gun (해남군), South Korea.

## Overview

SolarFit MVP combines rule-based filtering with machine learning to identify optimal locations for 100kW+ solar installations. The project uses:

- **Hard filters**: Land use (jimok), zoning restrictions, ownership, slope, elevation, forest age
- **Feature scoring**: Slope, aspect, GHI (Global Horizontal Irradiance), grid proximity, road access, land price
- **ML validation**: XGBoost ensemble with spatial K-fold cross-validation (읍면-level)
- **Ensemble**: 50% rule-based + 50% ML-based scoring

## Target Region

- **Sigungu**: 해남군 (code: 46810), 전라남도
- **Min viable area**: 1,000 m² (100kW)
- **Max slope**: 15°
- **Max elevation**: 600m

## Project Structure

```
solar_mvp/
├── pyproject.toml           # Build config, dependencies
├── .env                      # API keys (not committed)
├── data/
│   ├── dem/                 # DEM raster (haenam_slope.tif)
│   └── protected/           # Protected area shapefiles
├── cache/                    # Intermediate .parquet files
├── output/                   # Final results
├── src/
│   └── config.py            # Central configuration
└── tests/
    └── ...
```

## Setup

```bash
pip install -e ".[dev]"
cp .env.example .env
# Fill in VWORLD_API_KEY and DATA_GO_KR_API_KEY
```

## References

- **도시계획조례 이격거리**: Day 0 research (see `config.HAENAM_RESIDENTIAL_BUFFER_M`)
- **VWorld API**: Land parcel data (PNU), land use, zoning
- **data.go.kr**: Solar plant registry for labels (2018-2024)
