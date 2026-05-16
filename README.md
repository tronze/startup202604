# DR Project

This workspace currently contains collected raw data for analyzing Korea's electricity market, system demand, and demand response (DR) activity.

## Dataset Inventory

| Domain | File | Format | Coverage | Grain | Key Fields | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Daily supply-demand | `data/raw/EPSIS_전력수급실적.csv` | CSV (`cp949`) | 2020-01-01 to 2025-12-31 | Daily | `년`, `월`, `일`, `설비용량(MW)`, `공급능력(MW)`, `최대전력(MW)`, `최소전력(MW)`, `공급예비력(MW)`, `공급예비율(%)` | EPSIS daily system summary with peak/min timestamps. |
| Hourly SMP | `data/raw/EPSIS_SMP_시간별.csv` | CSV (`cp949`) | 2020-01-01 to 2025-12-31 | Daily row with 24 hourly values | `기간`, `01시`-`24시`, `최대`, `최소`, `가중평균` | Needs reshape to long format for hourly analysis. |
| Daily weather | `data/raw/기상_전국주요도시_일별_2013_2025.csv` | CSV (`utf-8-sig`) | 2013-01-01 to 2025-12-31 | Daily by city | `날짜`, `도시`, `최고기온`, `최저기온`, `평균기온`, `강수량mm`, `일사량MJm2`, `최대풍속ms`, `평균풍속ms` | Cities observed: `서울`, `인천`, `부산`, `대구`. |
| DR bids and awards | `data/raw/플러스DR_입낙찰_2020_2021.csv` | CSV (`cp949`) | 2020-01-01 to 2021-12-31 | Hourly | `날짜`, `시간`, `경제성DR입찰건수`, `피크수요입찰건수`, `미세먼지입찰건수`, `경제성DR낙찰건수`, `피크수요낙찰건수`, `미세먼지낙찰건수` | Event-style DR activity table. |
| Hourly load history | `data/raw/2013-2020-수요관리후-발전단-전력수요실적.csv` | CSV (`cp949`) | 2013-01-01 to 2020-12-31 | Daily row with 24 hourly values | `날짜`, `1시`-`24시` | Load after demand-management adjustments. |
| Hourly load history | `data/raw/2021년-1-12월-수요관리후-발전단-수요실적.csv` | CSV (`cp949`) | 2021-01-01 to 2021-12-31 | Daily row with 24 hourly values | `날짜`, `1시`-`24시` | Same schema as the 2013-2020 file. |
| Hourly load history | `data/raw/KPX_시간별전국전력수요량_2025.csv` | CSV (`cp949`) | 2025-01-01 to 2025-12-31 | Daily row with 24 hourly values | `날짜`, `1시`-`24시` | 2025 national hourly demand. |
| Annual market statistics | `data/raw/2022년도_전력시장통계.xlsx` to `data/raw/2025년도_전력시장통계.xlsx` | Excel | Multi-year historical tables | Mixed | Sheet-dependent | Reference workbooks for market capacity, trading volume, settlement prices, SMP, and annual summaries. |
| Renewable utilization | `data/raw/EPSIS_신재생이용률.xlsx`, `data/raw/EPSIS_재생에너지이용률.xlsx` | Excel | Monthly | Monthly by region and source | `기간`, `지역`, `이용률`, `연료원` | The two files currently appear to share the same schema. |
| Supplemental raw/reference | Remaining raw `.csv`/`.xlsx` files | Mixed | Varies | Varies | Varies | Includes alternative downloads, 제주 Plus DR, and source reference files. |

## Current Project State

- `data/raw` is populated with source files.
- `data/processed` contains normalized CSV outputs plus processing manifests.
- `scripts/process_all_raw.py` rebuilds the processed file layer from raw inputs.
- `scripts/build_sqlite_db.py` builds a local SQL database from the processed CSVs.

## Recommended Analysis Tables

- `supply_daily`: normalized daily supply-demand table from `EPSIS_전력수급실적.csv`
- `smp_hourly`: long-format hourly SMP table from `EPSIS_SMP_시간별.csv`
- `weather_daily`: cleaned weather observations by city and date
- `dr_hourly`: hourly DR bids and awards
- `load_hourly`: combined long-format hourly demand table across the load-history files

## Starter Code

Install the Python dependencies before running the pandas-based ETL or hypothesis scripts.

```bash
python3 -m pip install -r requirements.txt
```

Use `scripts/load_datasets.py` to load the main datasets with the correct encodings and normalized columns.

Example:

```python
from pathlib import Path

from scripts.load_datasets import load_core_datasets

datasets = load_core_datasets(Path("."))
print(datasets["supply_daily"].head())
print(datasets["smp_hourly"].head())
```

Use `scripts/build_analysis_table.py` to create an analysis-ready hourly master table in `data/processed`.

```bash
python3 scripts/build_analysis_table.py
```

This pipeline creates:

- `data/processed/analysis_hourly.csv`

The merged hourly table includes:

- hourly load
- hourly SMP and daily SMP summary values
- hourly DR bids and awards
- daily supply-demand context
- daily weather aggregates across all tracked cities
- city-specific daily weather features for `서울`, `인천`, `부산`, `대구`

## SQL Workflow

For analysis work, use SQL against the generated SQLite database instead of opening large CSVs in Excel.

```bash
python3 scripts/build_sqlite_db.py
sqlite3 data/processed/startup202604.sqlite
```

Useful starting queries:

```sql
SELECT table_name, row_count, column_count
FROM _table_inventory
ORDER BY row_count DESC;

SELECT *
FROM v_quality_issues;

SELECT year, month, AVG(load_mw) AS avg_load_mw, AVG(smp_krw_per_kwh) AS avg_smp
FROM v_analysis_hourly_clean
GROUP BY year, month
ORDER BY year, month;
```

The SQLite file is generated output and is ignored by Git. Rebuild it whenever processed CSVs change.
