# Data Inventory

This repository now keeps a compact, analysis-oriented data layout.

## What Matters Now

- `data/raw/`: retained source datasets needed to rebuild the analysis tables.
- `data/processed/*.csv`: canonical cleaned tables for analysis and SQL import.
- `data/docs/README.md`: document index with `current` and `legacy` separation.
- `data/docs/current/data_reference/현재_보유자료_및_분석각도.md`: current inventory and analysis directions in Korean.
- `data/docs/current/research/연구노트_actual_pvout_생성_20260427.md`: how regional actual PVOUT was derived from KPX generation and capacity data.
- `scripts/process_all_raw.py`: rebuilds the processed CSV layer from raw files.
- `scripts/build_analysis_table.py`: rebuilds the hourly master table.
- `scripts/build_sqlite_db.py`: creates `data/processed/startup202604.sqlite` on demand.

## Main Processed Tables

| Table | Rows | Purpose |
| --- | ---: | --- |
| `analysis_hourly.csv` | 87,648 | Hourly master table for load, SMP, DR, supply, and weather features |
| `load_hourly_all_sources.csv` | 113,952 | Full nationwide hourly load history across retained source files |
| `load_hourly.csv` | 87,648 | Core load subset used by the current hourly master pipeline |
| `smp_hourly.csv` | 52,608 | Hourly SMP, 2020-2025 |
| `weather_daily.csv` | 18,992 | Daily weather by city, 2013-2025 |
| `dr_hourly.csv` | 17,544 | Hourly Plus DR activity, 2020-2021 |
| `supply_daily.csv` | 2,192 | Daily supply-demand summary, 2020-2025 |
| `renewable_utilization_monthly.csv` | 2,828 | Monthly renewable utilization |
| `regional_energy_usage_2024.csv` | 2,904 | Regional monthly energy usage for 2024 |

## Kept But Secondary

- Market-statistics workbooks remain in `data/raw/` as original Excel sources.
- `market_statistics_sheet_index.csv` lists workbook sheets without exporting hundreds of generated sheet files.
- KPX notice CSVs are retained; raw archived HTML pages were removed as generated crawl artifacts.
- Workflow manifests and request queues are retained because they explain where data came from and what to collect next.

## Removed

- Duplicate 2025 hourly load raw files with identical checksums.
- Generated `market_statistics_sheets/` CSV/Parquet exports.
- Generated KPX HTML archives and exploratory download folders.
- Parquet duplicates in `data/processed`.
- Local SQLite database files, `.DS_Store`, and Python bytecode caches.

## SQL Use

Build the local database when needed:

```bash
python3 scripts/build_sqlite_db.py
sqlite3 data/processed/startup202604.sqlite
```

The SQLite file is generated and ignored by Git.
