# Processed Data Summary

The processed layer is now intentionally compact.

- Canonical format: CSV
- Generated on demand: SQLite database at `data/processed/startup202604.sqlite`
- Removed from the tracked data layer: Parquet duplicates, generated workbook sheet exports, local cache files

## Core Tables

| Table | Rows |
| --- | ---: |
| `analysis_hourly.csv` | 87,648 |
| `load_hourly_all_sources.csv` | 113,952 |
| `load_hourly.csv` | 87,648 |
| `smp_hourly.csv` | 52,608 |
| `weather_daily.csv` | 18,992 |
| `dr_hourly.csv` | 17,544 |
| `supply_daily.csv` | 2,192 |
| `renewable_utilization_monthly.csv` | 2,828 |
| `regional_energy_usage_2024.csv` | 2,904 |

## Notes

- The 2025 hourly load duplicates were removed after checksum verification.
- Blank footer rows were removed from hourly load outputs.
- Duplicate daily supply rows were removed.
- Market statistics workbooks are indexed in `market_statistics_sheet_index.csv`; the original Excel files remain in `data/raw/`.
