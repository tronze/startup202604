# China Solar Downstream Industry Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a PhD-level analytical report on China's downstream solar industry evolution (2016-2026) with Korean applicability analysis, supported by verified data and integrated narrative.

**Architecture:** Multi-phase research pipeline:
1. Infrastructure (data schemas, source tracking, scraping tools)
2. Discovery (initial company mapping from public sources)
3. Collection (Wayback Machine, Playwright, Chinese corporate DBs)
4. Verification (confidence grading, multi-source cross-check)
5. Analysis (hypothesis testing, theoretical frameworks)
6. Synthesis (integrated narrative report)
7. Quality review

**Tech Stack:** Python 3.11+, Playwright (headless browser automation), Wayback Machine API (waybackpy), pandas (data processing), aiohttp (async HTTP), pydantic (data validation), Markdown (output format)

---

## File Structure

```
china-solar-downstream/
├── docs/
│   ├── superpowers/
│   │   ├── specs/
│   │   │   └── 2026-05-08-china-solar-downstream-design.md  # Design (already exists)
│   │   └── plans/
│   │       └── 2026-05-08-china-solar-downstream-implementation.md  # This file
│   ├── reports/
│   │   ├── final-report.md            # Main deliverable
│   │   ├── company-profiles/          # Per-company deep-dives
│   │   │   └── <company-slug>.md      # 12-20 files
│   │   ├── segment-analyses/          # Per-segment summaries
│   │   │   └── <segment>.md
│   │   ├── policy-timeline.md         # Government policy chronology
│   │   └── korea-china-comparison.md  # Comparative analysis
│   └── methodology/
│       ├── data-sources.md            # Source documentation
│       ├── confidence-grading.md      # ★ rating criteria
│       └── data-gaps.md               # Known limitations
├── data/
│   ├── raw/
│   │   ├── companies.yaml             # Master company list (initial seeds + discovered)
│   │   ├── policy-events.yaml         # Government policy events with dates/impact
│   │   ├── wayback-snapshots/         # Cached HTML from Wayback Machine
│   │   │   └── <company-slug>/
│   │   │       └── <YYYY-MM>.html
│   │   ├── news-articles/             # Cached scraped articles
│   │   │   └── <source-slug>/
│   │   │       └── <article-id>.json
│   │   └── chinese-db/                # 企查查/天眼查 query results
│   │       └── <company-slug>.json
│   └── processed/
│       ├── company-metrics.csv        # Year × Company × Metric (verified)
│       ├── source-index.csv           # Every claim → source(s) → confidence
│       ├── timeline-events.csv        # Chronological events (policy + market + company)
│       └── market-evolution.csv       # Aggregated segment-level trends
├── scripts/
│   ├── 00_setup.py                    # Initialize directories, install deps
│   ├── 01_seed_companies.py           # Discover initial company list
│   ├── 02_wayback_collector.py        # Wayback Machine snapshot extractor
│   ├── 03_playwright_news_scraper.py  # Headless browser for Chinese media
│   ├── 04_chinese_db_query.py         # 企查查/天眼查 lookup
│   ├── 05_data_validator.py           # Cross-source verification
│   ├── 06_confidence_grader.py        # Auto-assign ★ ratings
│   ├── 07_timeline_builder.py         # Generate event timelines
│   ├── 08_metric_aggregator.py        # Roll up to segment/market level
│   └── 09_report_generator.py         # Compile markdown report from data
├── tests/
│   ├── test_data_schemas.py
│   ├── test_validators.py
│   └── test_confidence_grader.py
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## Critical Pre-Plan Note: Research vs Code

This is a **research project** that produces a written analytical report. Tasks alternate between:
- **Code tasks** (TDD with pytest, building data pipelines)
- **Research tasks** (data collection, hypothesis testing, writing) — these get a "research test" instead: a verification check that the deliverable meets quality criteria before commit.

For research tasks, the "test" is: *"Does this output meet the rigor criteria from the design doc (★★★+ evidence, multi-source verification, falsifiable claims)?"*

---

## Phase 1: Infrastructure Setup

### Task 1.1: Project Bootstrap

**Files:**
- Create: `requirements.txt`
- Create: `pyproject.toml`
- Create: `scripts/00_setup.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Write requirements.txt**

```
playwright>=1.40.0
waybackpy>=3.0.6
pandas>=2.1.0
pydantic>=2.5.0
aiohttp>=3.9.0
pyyaml>=6.0.1
beautifulsoup4>=4.12.0
lxml>=4.9.3
tenacity>=8.2.0
python-dotenv>=1.0.0
pytest>=7.4.0
pytest-asyncio>=0.21.0
rich>=13.6.0
```

- [ ] **Step 2: Write pyproject.toml**

```toml
[project]
name = "china-solar-downstream"
version = "0.1.0"
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

- [ ] **Step 3: Write scripts/00_setup.py**

```python
"""Initialize project directories and install Playwright browsers."""
from pathlib import Path
import subprocess
import sys

DIRS = [
    "data/raw/wayback-snapshots",
    "data/raw/news-articles",
    "data/raw/chinese-db",
    "data/processed",
    "docs/reports/company-profiles",
    "docs/reports/segment-analyses",
    "docs/methodology",
]

def main():
    root = Path(__file__).parent.parent
    for d in DIRS:
        (root / d).mkdir(parents=True, exist_ok=True)
        print(f"✓ {d}")
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
    print("✓ Playwright chromium installed")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run setup**

Run: `cd /Users/limthanh/Documents/startup202604/china-solar-downstream && python3 -m pip install -r requirements.txt && python3 scripts/00_setup.py`
Expected: All directories created, Playwright chromium downloaded.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt pyproject.toml scripts/00_setup.py tests/__init__.py
git commit -m "chore: project bootstrap with deps and directory scaffolding"
```

---

### Task 1.2: Core Data Schemas

**Files:**
- Create: `scripts/lib/__init__.py`
- Create: `scripts/lib/schemas.py`
- Create: `tests/test_data_schemas.py`

- [ ] **Step 1: Write failing test in tests/test_data_schemas.py**

```python
import pytest
from datetime import date
from scripts.lib.schemas import Company, MetricRecord, Source, ConfidenceLevel, Segment

def test_company_minimal():
    c = Company(
        slug="sunrun-china",
        legal_name_cn="中国阳光能源",
        legal_name_en="Sunrun China",
        founded_year=2015,
        primary_segment=Segment.RESIDENTIAL_INSTALLATION,
        status="active",
    )
    assert c.slug == "sunrun-china"
    assert c.founded_year == 2015

def test_metric_record_with_source():
    src = Source(
        url="https://example.com/article",
        accessed_at=date(2026, 5, 8),
        kind="news",
        publisher="36Kr",
        title="Solar growth report",
    )
    rec = MetricRecord(
        company_slug="sunrun-china",
        year=2020,
        metric="revenue_rmb",
        value=500_000_000,
        confidence=ConfidenceLevel.FOUR_STARS,
        sources=[src],
        notes="Cross-verified across 36Kr and company IR.",
    )
    assert rec.value == 500_000_000
    assert rec.confidence == ConfidenceLevel.FOUR_STARS

def test_metric_requires_source():
    with pytest.raises(ValueError):
        MetricRecord(
            company_slug="x",
            year=2020,
            metric="revenue_rmb",
            value=100,
            confidence=ConfidenceLevel.FIVE_STARS,
            sources=[],
        )
```

- [ ] **Step 2: Run test (expect failure)**

Run: `pytest tests/test_data_schemas.py -v`
Expected: ImportError or ModuleNotFoundError (schemas.py doesn't exist).

- [ ] **Step 3: Write scripts/lib/schemas.py**

```python
"""Pydantic schemas for the research data pipeline."""
from datetime import date
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

class ConfidenceLevel(int, Enum):
    ONE_STAR = 1     # Inference/extrapolation only
    TWO_STARS = 2    # Single source or estimate
    THREE_STARS = 3  # 2-3 independent sources
    FOUR_STARS = 4   # Company official + 1 verification
    FIVE_STARS = 5   # Company official + 2+ verification + audit

class Segment(str, Enum):
    RESIDENTIAL_INSTALLATION = "residential_installation"
    FINANCING_LEASING = "financing_leasing"
    ECOMMERCE_MARKETPLACE = "ecommerce_marketplace"
    OM_MONITORING = "om_monitoring"
    OTHER = "other"  # for dynamic segment discovery

class Source(BaseModel):
    url: str
    accessed_at: date
    kind: str  # "news", "company_official", "wayback", "corporate_db", "report"
    publisher: Optional[str] = None
    title: Optional[str] = None
    archived_url: Optional[str] = None  # Wayback URL if applicable

class Company(BaseModel):
    slug: str
    legal_name_cn: str
    legal_name_en: str
    founded_year: int
    primary_segment: Segment
    secondary_segments: List[Segment] = Field(default_factory=list)
    status: str  # "active", "acquired", "ipo", "defunct"
    headquarters_city: Optional[str] = None
    notes: Optional[str] = None

class MetricRecord(BaseModel):
    company_slug: str
    year: int
    metric: str  # "revenue_rmb", "customers", "funding_rmb", "valuation_rmb", "employees"
    value: float
    confidence: ConfidenceLevel
    sources: List[Source]
    value_range_low: Optional[float] = None  # For estimated ranges
    value_range_high: Optional[float] = None
    notes: Optional[str] = None

    @field_validator("sources")
    @classmethod
    def must_have_source(cls, v):
        if not v:
            raise ValueError("MetricRecord requires at least one source.")
        return v

class TimelineEvent(BaseModel):
    event_date: date
    event_type: str  # "policy", "company_milestone", "market_event"
    company_slug: Optional[str] = None
    title: str
    description: str
    impact_summary: Optional[str] = None
    sources: List[Source]
```

- [ ] **Step 4: Run test (expect pass)**

Run: `pytest tests/test_data_schemas.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/__init__.py scripts/lib/schemas.py tests/test_data_schemas.py
git commit -m "feat: pydantic schemas for companies, metrics, sources, events"
```

---

### Task 1.3: Source Index & Confidence Grader

**Files:**
- Create: `scripts/lib/confidence.py`
- Create: `scripts/06_confidence_grader.py`
- Create: `tests/test_confidence_grader.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_confidence_grader.py
from datetime import date
from scripts.lib.schemas import Source, ConfidenceLevel
from scripts.lib.confidence import grade_sources

def _src(kind, publisher="X"):
    return Source(url=f"https://{publisher}.com", accessed_at=date(2026, 5, 8), kind=kind, publisher=publisher)

def test_five_stars_company_plus_two_verifications():
    sources = [
        _src("company_official", "company"),
        _src("news", "36Kr"),
        _src("news", "Caixin"),
    ]
    assert grade_sources(sources) == ConfidenceLevel.FIVE_STARS

def test_four_stars_company_plus_one():
    sources = [_src("company_official", "company"), _src("news", "36Kr")]
    assert grade_sources(sources) == ConfidenceLevel.FOUR_STARS

def test_three_stars_three_independent_news():
    sources = [_src("news", "36Kr"), _src("news", "Caixin"), _src("news", "Sina")]
    assert grade_sources(sources) == ConfidenceLevel.THREE_STARS

def test_two_stars_single_news():
    sources = [_src("news", "36Kr")]
    assert grade_sources(sources) == ConfidenceLevel.TWO_STARS

def test_one_star_estimate_only():
    sources = [_src("inference", "self")]
    assert grade_sources(sources) == ConfidenceLevel.ONE_STAR
```

- [ ] **Step 2: Run test (expect failure)**

Run: `pytest tests/test_confidence_grader.py -v`
Expected: ImportError on `scripts.lib.confidence`.

- [ ] **Step 3: Implement scripts/lib/confidence.py**

```python
"""Auto-grade sources into ★ levels based on the design rubric."""
from typing import List
from scripts.lib.schemas import Source, ConfidenceLevel

OFFICIAL_KINDS = {"company_official", "audit_report", "ipo_filing"}
INDEPENDENT_KINDS = {"news", "report", "corporate_db"}
INFERENCE_KINDS = {"inference", "estimate"}

def grade_sources(sources: List[Source]) -> ConfidenceLevel:
    if not sources:
        return ConfidenceLevel.ONE_STAR

    has_official = any(s.kind in OFFICIAL_KINDS for s in sources)
    independent_publishers = {s.publisher for s in sources if s.kind in INDEPENDENT_KINDS}
    n_indep = len(independent_publishers)
    only_inference = all(s.kind in INFERENCE_KINDS for s in sources)

    if only_inference:
        return ConfidenceLevel.ONE_STAR
    if has_official and n_indep >= 2:
        return ConfidenceLevel.FIVE_STARS
    if has_official and n_indep >= 1:
        return ConfidenceLevel.FOUR_STARS
    if n_indep >= 3:
        return ConfidenceLevel.THREE_STARS
    if n_indep >= 2:
        return ConfidenceLevel.THREE_STARS
    if n_indep == 1:
        return ConfidenceLevel.TWO_STARS
    return ConfidenceLevel.ONE_STAR
```

- [ ] **Step 4: Run test (expect pass)**

Run: `pytest tests/test_confidence_grader.py -v`
Expected: 5 passed.

- [ ] **Step 5: Write CLI wrapper scripts/06_confidence_grader.py**

```python
"""CLI: grade all metric records in data/processed/company-metrics.csv."""
import pandas as pd
from pathlib import Path
from scripts.lib.confidence import grade_sources
from scripts.lib.schemas import Source
from datetime import date

ROOT = Path(__file__).parent.parent
METRICS = ROOT / "data/processed/company-metrics.csv"
SOURCES = ROOT / "data/processed/source-index.csv"

def main():
    if not METRICS.exists():
        print(f"⚠️ {METRICS} not found yet. Run after data collection.")
        return
    df = pd.read_csv(METRICS)
    src_df = pd.read_csv(SOURCES)
    upgraded = 0
    for idx, row in df.iterrows():
        srcs_for_row = src_df[src_df["metric_id"] == row["metric_id"]]
        sources = [
            Source(
                url=r["url"],
                accessed_at=date.fromisoformat(r["accessed_at"]),
                kind=r["kind"],
                publisher=r.get("publisher"),
            )
            for _, r in srcs_for_row.iterrows()
        ]
        new_level = grade_sources(sources).value
        if new_level != row["confidence"]:
            df.at[idx, "confidence"] = new_level
            upgraded += 1
    df.to_csv(METRICS, index=False)
    print(f"✓ Re-graded {upgraded} records.")

if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Commit**

```bash
git add scripts/lib/confidence.py scripts/06_confidence_grader.py tests/test_confidence_grader.py
git commit -m "feat: confidence grading system for source-backed metrics"
```

---

## Phase 2: Company Discovery & Initial Mapping

### Task 2.1: Seed Company List (Manual + Public Sources)

**Files:**
- Create: `data/raw/companies.yaml`
- Create: `scripts/01_seed_companies.py`
- Create: `docs/methodology/data-sources.md`

This task uses **WebSearch + WebFetch** to discover candidate companies. Output: a YAML seed file.

- [ ] **Step 1: Define discovery queries**

Write `scripts/01_seed_companies.py`:

```python
"""Discover Chinese solar downstream companies from public sources.

Uses curated search queries to identify candidates across 4 segments.
Output: prints candidate companies for manual curation into companies.yaml.
"""
QUERIES = {
    "residential_installation": [
        "China residential rooftop solar installer 2018 2020",
        "中国户用光伏 安装公司 排名",
        "China home solar startup unicorn",
    ],
    "financing_leasing": [
        "China solar financing company lease consumer",
        "中国 光伏 融资租赁 公司",
        "China solar PPA residential startup",
    ],
    "ecommerce_marketplace": [
        "China solar online marketplace platform",
        "中国 光伏 电商平台 B2C",
        "Solar e-commerce China consumer",
    ],
    "om_monitoring": [
        "China solar O&M monitoring SaaS",
        "中国 光伏 运维 监控 平台",
        "China solar IoT monitoring startup",
    ],
}

if __name__ == "__main__":
    for segment, queries in QUERIES.items():
        print(f"\n## {segment}")
        for q in queries:
            print(f"  - {q}")
    print("\n→ Run these queries via WebSearch tool, populate data/raw/companies.yaml")
```

- [ ] **Step 2: Execute discovery queries (manual research task)**

For each segment, run the WebSearch queries from Step 1. For each candidate company found:
- Verify: founded after 2012, grew 2016-2026, has Chinese identity
- Collect: legal name (CN + EN), founded year, segment, current status
- Cross-check on at least 2 sources

Document findings as you go.

- [ ] **Step 3: Write data/raw/companies.yaml**

Format (target: 20-30 candidates initially, will be filtered to 12-20 final):

```yaml
# Initial seed companies for China solar downstream analysis
# Each company gets verified during Phase 3 collection.
companies:
  - slug: <unique-slug>
    legal_name_cn: <Chinese name>
    legal_name_en: <English name>
    founded_year: <YYYY>
    primary_segment: residential_installation | financing_leasing | ecommerce_marketplace | om_monitoring
    status: active | acquired | ipo | defunct
    headquarters_city: <city>
    discovery_sources:
      - <url1>
      - <url2>
    initial_notes: <one-line description of why this company matters>
```

Aim: 5-8 candidates per segment.

- [ ] **Step 4: Document methodology in docs/methodology/data-sources.md**

```markdown
# Data Sources Inventory

## Tier 1: Company Official
- Company websites (current + Wayback Machine snapshots)
- IPO prospectuses (HKEX, SSE, NYSE for Chinese listings)
- Annual reports / IR releases

## Tier 2: Independent Media (Chinese)
- 36Kr (36氪) — tech/startup news
- Caixin (财新) — financial journalism
- Tencent Tech (腾讯科技)
- Sina Tech (新浪科技)
- 中国能源报 (China Energy News)
- 钛媒体 (TMTPost)

## Tier 3: Industry Reports
- BloombergNEF (BNEF) — solar market reports
- IEA Photovoltaic Power Systems
- China Photovoltaic Industry Association (CPIA) annual reports
- 国家能源局 (NEA) statistics

## Tier 4: Corporate Databases
- 企查查 (Qcc.com) — registration, capital structure
- 天眼查 (Tyc.com) — financing rounds, litigation
- Crunchbase — international funding records (limited China coverage)

## Tier 5: Web Archives
- Wayback Machine (archive.org) — historical website snapshots
- Common Crawl — supplementary archives

## Discovery Queries Used
[Document Phase 2.1 queries here]
```

- [ ] **Step 5: Verify seed list against design criteria**

Self-check (no test file — manual verification):
- Each candidate is a *new entrant* (not pre-2012 incumbent)?
- Each has at least 1 verifiable signal of "tangible market impact"?
- Coverage across all 4 segments?
- Mix of successes + interesting failures included?

If any candidate fails: remove or replace.

- [ ] **Step 6: Commit**

```bash
git add data/raw/companies.yaml scripts/01_seed_companies.py docs/methodology/data-sources.md
git commit -m "research: seed company list (20-30 candidates) across 4 downstream segments"
```

---

### Task 2.2: Policy Timeline Foundation

**Files:**
- Create: `data/raw/policy-events.yaml`
- Create: `docs/reports/policy-timeline.md`

The policy overlay is the *backbone* of the analysis — markets respond to policy. Build it first.

- [ ] **Step 1: Identify key policy events 2014-2026**

Use WebSearch + WebFetch on:
- 国家能源局 (NEA) policy announcements page
- 中国光伏行业协会 (CPIA) historical archives
- BNEF / IEA China policy reports

Target events:
- Solar feed-in tariff (FIT) introduction & schedule
- Distributed generation policies
- Residential solar subsidy launches/reforms (especially 2018-2019 changes)
- 530新政 (May 31, 2018 policy) — major industry shock
- "Whole-county" rooftop pilot (整县推进, 2021)
- Carbon neutrality goal (2060) and "1+N" policy framework
- Market parity (平价上网) milestones
- 2022-2024 reforms

- [ ] **Step 2: Write data/raw/policy-events.yaml**

```yaml
events:
  - date: 2013-08-26
    title: "Distributed PV Subsidy Policy (国发〔2013〕24号)"
    title_cn: "光伏发电有关价格政策"
    issuer: "NDRC"
    impact_summary: "Established 0.42 RMB/kWh distributed solar subsidy. Foundation for residential growth."
    sources:
      - url: "<url>"
        accessed_at: 2026-05-08
        publisher: "NDRC"
        kind: "company_official"  # using as 'official_govt'
    confidence: 5

  - date: 2018-05-31
    title: "530 New Policy (530新政)"
    title_cn: "关于2018年光伏发电有关事项的通知"
    issuer: "NEA + NDRC + MoF"
    impact_summary: "Sudden cap on subsidized capacity + reduced FIT. Killed many small installers."
    sources: [...]
    confidence: 5

  # ... 15-25 events total
```

- [ ] **Step 3: Generate readable timeline at docs/reports/policy-timeline.md**

Render the YAML as a chronological narrative grouped by phase:
- 2013-2017: Subsidy-driven boom
- 2018-2019: 530 shock & reform
- 2020-2021: Carbon goals + whole-county
- 2022-2024: Market parity transition
- 2025-2026: Post-subsidy maturity

For each phase: 2-3 paragraphs explaining what happened, why, and which downstream segments it affected most.

- [ ] **Step 4: Verify policy timeline (research test)**

Each event must:
- ✅ Have a specific date (YYYY-MM-DD or YYYY-MM)
- ✅ Reference the actual policy document (not just news coverage)
- ✅ Have an impact summary tied to downstream effects
- ✅ Have ≥ 2 sources (1 official + 1 analytical)

If any event fails — fix or remove.

- [ ] **Step 5: Commit**

```bash
git add data/raw/policy-events.yaml docs/reports/policy-timeline.md
git commit -m "research: policy timeline 2013-2026 with downstream impact analysis"
```

---

## Phase 3: Multi-Layer Data Collection

### Task 3.1: Wayback Machine Collector

**Files:**
- Create: `scripts/02_wayback_collector.py`
- Create: `scripts/lib/wayback.py`
- Create: `tests/test_wayback.py`

- [ ] **Step 1: Write failing test for snapshot picker**

```python
# tests/test_wayback.py
from scripts.lib.wayback import pick_yearly_snapshots

def test_pick_yearly_snapshots_returns_one_per_year():
    available = [
        "20160315000000", "20160601000000", "20161220000000",
        "20170105000000", "20170815000000",
        "20180601000000",
    ]
    picked = pick_yearly_snapshots(available, target_years=[2016, 2017, 2018, 2019])
    assert set(picked.keys()) == {2016, 2017, 2018}  # 2019 has no snapshot
    # Prefer snapshots closest to mid-year (June)
    assert picked[2016] == "20160601000000"
    assert picked[2017] == "20170815000000"
```

- [ ] **Step 2: Run test (expect failure)**

Run: `pytest tests/test_wayback.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement scripts/lib/wayback.py**

```python
"""Wayback Machine helper utilities."""
from typing import List, Dict, Optional
from datetime import datetime
from waybackpy import WaybackMachineCDXServerAPI

def pick_yearly_snapshots(
    timestamps: List[str],
    target_years: List[int],
) -> Dict[int, str]:
    """Pick one snapshot per target year, preferring those closest to mid-year (June 30)."""
    picks = {}
    for year in target_years:
        candidates = [t for t in timestamps if t.startswith(str(year))]
        if not candidates:
            continue
        target = datetime(year, 6, 30)
        best = min(
            candidates,
            key=lambda t: abs((datetime.strptime(t, "%Y%m%d%H%M%S") - target).days),
        )
        picks[year] = best
    return picks

def fetch_snapshot_list(url: str, user_agent: str = "research-bot/0.1") -> List[str]:
    """Return all available snapshot timestamps for a URL."""
    cdx = WaybackMachineCDXServerAPI(url=url, user_agent=user_agent)
    return [s.timestamp for s in cdx.snapshots()]
```

- [ ] **Step 4: Run test (expect pass)**

Run: `pytest tests/test_wayback.py -v`
Expected: 1 passed.

- [ ] **Step 5: Implement CLI scripts/02_wayback_collector.py**

```python
"""For each company in companies.yaml, fetch yearly Wayback snapshots."""
import yaml
import asyncio
import aiohttp
from pathlib import Path
from scripts.lib.wayback import fetch_snapshot_list, pick_yearly_snapshots

ROOT = Path(__file__).parent.parent
COMPANIES = ROOT / "data/raw/companies.yaml"
SNAPSHOT_DIR = ROOT / "data/raw/wayback-snapshots"
TARGET_YEARS = list(range(2016, 2027))

async def fetch_html(session, url):
    async with session.get(url, timeout=30) as r:
        return await r.text()

async def collect_company(session, company):
    slug = company["slug"]
    url = company.get("website")
    if not url:
        print(f"⚠️  {slug}: no website")
        return
    out_dir = SNAPSHOT_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamps = fetch_snapshot_list(url)
    picks = pick_yearly_snapshots(timestamps, TARGET_YEARS)
    for year, ts in picks.items():
        out_file = out_dir / f"{year}.html"
        if out_file.exists():
            continue
        archived_url = f"https://web.archive.org/web/{ts}/{url}"
        try:
            html = await fetch_html(session, archived_url)
            out_file.write_text(html)
            print(f"  ✓ {slug} {year} ({ts})")
        except Exception as e:
            print(f"  ✗ {slug} {year}: {e}")

async def main():
    data = yaml.safe_load(COMPANIES.read_text())
    async with aiohttp.ClientSession() as session:
        for c in data["companies"]:
            await collect_company(session, c)

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 6: Run collector for first 3 companies (smoke test)**

Run: `python3 scripts/02_wayback_collector.py 2>&1 | head -50`
Expected: HTML files saved to `data/raw/wayback-snapshots/<slug>/<year>.html`. Some companies may have no Wayback presence — that's data, not a bug.

- [ ] **Step 7: Commit**

```bash
git add scripts/lib/wayback.py scripts/02_wayback_collector.py tests/test_wayback.py
git commit -m "feat: Wayback Machine snapshot collector with yearly picking"
```

---

### Task 3.2: Playwright News Scraper

**Files:**
- Create: `scripts/03_playwright_news_scraper.py`
- Create: `scripts/lib/news_extract.py`
- Create: `tests/test_news_extract.py`

- [ ] **Step 1: Write test for article extractor**

```python
# tests/test_news_extract.py
from scripts.lib.news_extract import extract_article_metadata

def test_extracts_36kr_metadata():
    html = """
    <html><head>
        <meta property="og:title" content="某光伏公司2020年营收增长100%">
        <meta property="og:url" content="https://36kr.com/p/12345">
        <meta property="article:published_time" content="2020-06-15T10:00:00+08:00">
    </head><body>
        <article><p>2020年, 该公司营收达到5亿元人民币...</p></article>
    </body></html>
    """
    meta = extract_article_metadata(html, source_url="https://36kr.com/p/12345")
    assert meta["title"] == "某光伏公司2020年营收增长100%"
    assert meta["published_at"].year == 2020
    assert "5亿元" in meta["body_text"]
```

- [ ] **Step 2: Run test (expect failure)**

Run: `pytest tests/test_news_extract.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement scripts/lib/news_extract.py**

```python
"""Extract structured metadata from news article HTML."""
from datetime import datetime
from bs4 import BeautifulSoup

def extract_article_metadata(html: str, source_url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    title = (soup.find("meta", property="og:title") or {}).get("content") or (soup.title.string if soup.title else "")
    pub = (soup.find("meta", property="article:published_time") or {}).get("content")
    published_at = datetime.fromisoformat(pub) if pub else None
    article = soup.find("article") or soup
    body_text = "\n".join(p.get_text(strip=True) for p in article.find_all("p"))
    return {
        "title": title,
        "url": source_url,
        "published_at": published_at,
        "body_text": body_text,
    }
```

- [ ] **Step 4: Run test (expect pass)**

Run: `pytest tests/test_news_extract.py -v`
Expected: 1 passed.

- [ ] **Step 5: Implement scraping CLI scripts/03_playwright_news_scraper.py**

```python
"""Use headless Playwright to search Chinese tech media for company mentions.

For each company, query 36Kr, Caixin, Sina Tech, etc.
Save raw article metadata as JSON in data/raw/news-articles/<source>/<id>.json.
"""
import asyncio
import json
import yaml
from pathlib import Path
from playwright.async_api import async_playwright
from scripts.lib.news_extract import extract_article_metadata

ROOT = Path(__file__).parent.parent
COMPANIES = ROOT / "data/raw/companies.yaml"
NEWS_DIR = ROOT / "data/raw/news-articles"

SEARCH_TARGETS = [
    {"slug": "36kr", "search_url_template": "https://36kr.com/search/articles/{q}"},
    {"slug": "caixin", "search_url_template": "https://search.caixin.com/search/search.jsp?keyword={q}"},
    {"slug": "sinatech", "search_url_template": "https://search.sina.com.cn/?q={q}&c=news&range=title"},
]

async def scrape_for_company(page, company, target):
    name = company["legal_name_cn"]
    url = target["search_url_template"].format(q=name)
    await page.goto(url, timeout=30000)
    await page.wait_for_load_state("domcontentloaded")
    # Extract article links — selectors are site-specific; update as needed.
    links = await page.locator("a").evaluate_all("els => els.map(e => e.href).filter(h => h.includes('article') || h.includes('/p/'))")
    return links[:20]  # top 20 per source per company

async def main():
    data = yaml.safe_load(COMPANIES.read_text())
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(locale="zh-CN")
        page = await ctx.new_page()
        for company in data["companies"]:
            for target in SEARCH_TARGETS:
                try:
                    links = await scrape_for_company(page, company, target)
                    out_dir = NEWS_DIR / target["slug"]
                    out_dir.mkdir(parents=True, exist_ok=True)
                    (out_dir / f"{company['slug']}.json").write_text(
                        json.dumps({"company": company["slug"], "links": links}, ensure_ascii=False, indent=2)
                    )
                    print(f"  ✓ {company['slug']} on {target['slug']}: {len(links)} links")
                except Exception as e:
                    print(f"  ✗ {company['slug']} on {target['slug']}: {e}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 6: Smoke test on 1 company**

Run: `python3 scripts/03_playwright_news_scraper.py 2>&1 | head -20`
Expected: At least 1 source returns links. If a source blocks the scraper, document the limitation in `docs/methodology/data-gaps.md` and try alternates.

- [ ] **Step 7: Commit**

```bash
git add scripts/lib/news_extract.py scripts/03_playwright_news_scraper.py tests/test_news_extract.py
git commit -m "feat: Playwright-based Chinese tech media scraper"
```

---

### Task 3.3: Article Content Fetcher & Indexer

**Files:**
- Modify: `scripts/03_playwright_news_scraper.py` (extend with content fetch phase)
- Create: `scripts/lib/dedupe.py`

- [ ] **Step 1: Add second-pass article fetcher**

Extend `03_playwright_news_scraper.py` with a function that, given the link lists from Step 5 above, visits each article URL and saves the extracted metadata + body text to `data/raw/news-articles/<source>/<article-hash>.json`.

Code:

```python
import hashlib

async def fetch_articles(page, source_slug, company_slug, links):
    out_dir = NEWS_DIR / source_slug
    out_dir.mkdir(parents=True, exist_ok=True)
    for link in links:
        h = hashlib.sha1(link.encode()).hexdigest()[:12]
        out_path = out_dir / f"{company_slug}_{h}.json"
        if out_path.exists():
            continue
        try:
            await page.goto(link, timeout=30000)
            html = await page.content()
            meta = extract_article_metadata(html, source_url=link)
            meta["source"] = source_slug
            meta["company"] = company_slug
            out_path.write_text(json.dumps(meta, ensure_ascii=False, default=str, indent=2))
        except Exception as e:
            print(f"    ✗ {link}: {e}")
```

Wire it into `main()` after each company's link discovery.

- [ ] **Step 2: Add dedupe utility scripts/lib/dedupe.py**

```python
"""Detect near-duplicate articles (republished press releases)."""
from typing import List, Dict
from difflib import SequenceMatcher

def find_duplicates(articles: List[Dict], threshold: float = 0.85) -> List[List[str]]:
    """Return groups of article-ids that are near-duplicates."""
    groups = []
    used = set()
    for i, a in enumerate(articles):
        if a["id"] in used:
            continue
        group = [a["id"]]
        for b in articles[i + 1:]:
            if b["id"] in used:
                continue
            ratio = SequenceMatcher(None, a["body_text"][:500], b["body_text"][:500]).ratio()
            if ratio >= threshold:
                group.append(b["id"])
                used.add(b["id"])
        if len(group) > 1:
            groups.append(group)
            used.add(a["id"])
    return groups
```

- [ ] **Step 3: Run extended scraper**

Run: `python3 scripts/03_playwright_news_scraper.py`
Expected: `data/raw/news-articles/<source>/<company>_<hash>.json` populated. Some sites will rate-limit; add delays as needed.

- [ ] **Step 4: Document any data gaps in docs/methodology/data-gaps.md**

```markdown
# Known Data Gaps

## Sources Blocked
- <source-slug>: <reason — Cloudflare, login wall, rate limit>

## Companies with Limited Coverage
- <company-slug>: <which years/metrics are unavailable>

## Mitigation Strategies
- <how we'll work around the gap (e.g., use Wayback Machine of the source itself)>
```

- [ ] **Step 5: Commit**

```bash
git add scripts/03_playwright_news_scraper.py scripts/lib/dedupe.py docs/methodology/data-gaps.md
git commit -m "feat: article body fetcher + dedupe + data-gaps documentation"
```

---

### Task 3.4: Chinese Corporate Database Lookup

**Files:**
- Create: `scripts/04_chinese_db_query.py`

⚠️ **Note:** 企查查 / 天眼查 require accounts and have anti-bot protections. This task captures *publicly visible* data only. For deeper records, manual lookups + screenshots are documented as fallback.

- [ ] **Step 1: Implement scripts/04_chinese_db_query.py with Playwright**

```python
"""Public-tier scrape of 企查查 / 天眼查 for Chinese company registration data.

Scope: registration date, registered capital, legal representative, change history.
"""
import asyncio
import json
import yaml
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).parent.parent
COMPANIES = ROOT / "data/raw/companies.yaml"
DB_DIR = ROOT / "data/raw/chinese-db"

async def query_qcc(page, name_cn):
    await page.goto(f"https://www.qcc.com/web/search?key={name_cn}", timeout=30000)
    await page.wait_for_load_state("domcontentloaded")
    # Best-effort: capture top result card
    try:
        first = page.locator("a.title").first
        href = await first.get_attribute("href")
        await page.goto(href, timeout=30000)
        await page.wait_for_load_state("domcontentloaded")
        return await page.content()
    except Exception:
        return None

async def main():
    data = yaml.safe_load(COMPANIES.read_text())
    DB_DIR.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(locale="zh-CN")
        page = await ctx.new_page()
        for c in data["companies"]:
            html = await query_qcc(page, c["legal_name_cn"])
            if html:
                (DB_DIR / f"{c['slug']}_qcc.html").write_text(html)
                print(f"  ✓ {c['slug']}")
            else:
                print(f"  ⚠️  {c['slug']}: no public result")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Run; expect partial success**

Run: `python3 scripts/04_chinese_db_query.py`
Expected: Some companies retrieved, some blocked. Document blocked ones.

- [ ] **Step 3: Add manual lookup fallback procedure to docs/methodology/data-gaps.md**

```markdown
## Manual Corporate DB Lookup Protocol
For companies blocked by 企查查/天眼查 anti-bot:
1. Open browser, log into account
2. Navigate to company page
3. Save full page HTML via Cmd+S
4. Place in `data/raw/chinese-db/<slug>_qcc.html` manually
5. Note in source-index.csv: `kind=corporate_db`, `accessed_at=<date>`
```

- [ ] **Step 4: Commit**

```bash
git add scripts/04_chinese_db_query.py docs/methodology/data-gaps.md
git commit -m "feat: Chinese corporate DB scraper with manual fallback protocol"
```

---

## Phase 4: Per-Company Deep Research

This phase is the core. Each of the 12-20 companies gets a structured deep-dive. **One subtask per company.**

### Task 4.X: Company Deep-Dive Template (repeat per company)

For each company in `companies.yaml`, execute the following template. The first time, do this for the **2 highest-significance companies** to validate the workflow, then iterate.

**Files (per company):**
- Modify: `data/processed/company-metrics.csv` (append rows)
- Modify: `data/processed/source-index.csv` (append rows)
- Create: `docs/reports/company-profiles/<slug>.md`

- [ ] **Step 1: Read all collected raw data for this company**

Sources:
- `data/raw/wayback-snapshots/<slug>/*.html`
- `data/raw/news-articles/*/<slug>_*.json`
- `data/raw/chinese-db/<slug>_*.html`

Skim each, note interesting events with dates and metrics.

- [ ] **Step 2: Construct year-by-year business model snapshot**

For each year 2016-2026 where data exists:
- Service offering (what & to whom)
- Revenue model (how money flows in)
- Customer acquisition (channels)
- Key partnerships
- Tech positioning
- Notable events (funding, product launch, hire, M&A)

Use Wayback snapshots as primary source (what the company said at the time).

- [ ] **Step 3: Extract quantitative metrics**

For each year, attempt to find:
- Revenue (RMB)
- Customer count / installations
- Funding raised (round, amount, lead investor)
- Valuation (if announced)
- Employees
- Geographic footprint

Cross-verify each metric across sources. Mark confidence per the rubric. If a metric appears in only one source — flag as ★★ and note the limitation.

- [ ] **Step 4: Write metrics to data/processed/company-metrics.csv**

CSV schema:
```
metric_id,company_slug,year,metric,value,value_range_low,value_range_high,confidence,notes
```

Each new row should reference one or more `source_id`s in `source-index.csv`.

- [ ] **Step 5: Append sources to data/processed/source-index.csv**

CSV schema:
```
source_id,metric_id,url,accessed_at,kind,publisher,title,archived_url,quoted_text
```

`quoted_text` is the specific sentence(s) supporting the claim (in original language). This is *evidence preservation* — critical for peer review.

- [ ] **Step 6: Write company profile docs/reports/company-profiles/<slug>.md**

Template:

```markdown
# <Company Name> (slug)

**Segment:** <primary segment>
**Founded:** <year>
**Status:** active | acquired | ipo | defunct
**HQ:** <city>

## Founding Story
[Who, what problem, what gap they spotted — 2-3 paragraphs]

## Business Model Evolution
| Year | Service Offering | Revenue Model | Key Move |
|------|------------------|---------------|----------|
| 2016 | ... | ... | ... |
| ...  | ... | ... | ... |

## Key Metrics (Year-by-Year)
| Year | Revenue (RMB) | Customers | Funding | Valuation | Confidence |
|------|---------------|-----------|---------|-----------|------------|
| ...  | ... | ... | ... | ... | ★★★★ |

## Inflection Points
1. **<year> — <event>**: [What happened, why it mattered, how the company responded]
2. ...

## Hypothesis: Why This Company [Succeeded/Failed/Plateaued]
[One paragraph hypothesis — calibrated to evidence strength.]

### Supporting Evidence
- [Evidence 1] [★★★★, source A + B]
- [Evidence 2] [★★★, sources C, D, E]

### Counter-Hypothesis & Falsification
- Could this success/failure be explained by [alternate hypothesis]?
- We checked [data X] — result favors/disfavors counter.

## Data Gaps & Uncertainty
- [What we couldn't find, why, how it affects conclusions]

## Sources
[Linked from source-index.csv via metric_ids — list source_ids used in this profile]
```

- [ ] **Step 7: Self-review against rigor checklist**

For this profile, verify:
- ✅ Each main claim has ≥ 2 independent sources OR official + 1 verification
- ✅ No ★ or ★★ claims without explicit "high uncertainty" flag
- ✅ Causal claims are labeled "inferred" vs "documented"
- ✅ Counter-hypothesis is documented
- ✅ At least one specific Wayback Machine URL cited (proves website evolution)
- ✅ Profile reads as integrated narrative (not just a fact dump)

If any check fails — return to Step 1.

- [ ] **Step 8: Commit**

```bash
git add data/processed/company-metrics.csv data/processed/source-index.csv docs/reports/company-profiles/<slug>.md
git commit -m "research: company deep-dive — <Company Name>"
```

**Repeat Task 4.X for each of the 12-20 companies. Recommend processing in this order:**
1. The 2 highest-impact companies first (validate workflow)
2. Companies with most public data next (build momentum)
3. Companies with sparse data last (so unknowns are constrained)

**Mid-phase checkpoint:** After 5 companies, re-evaluate segment definitions. If evidence suggests a segment refinement → update design doc + this plan.

---

## Phase 5: Cross-Company Analysis

### Task 5.1: Segment-Level Synthesis

**Files:**
- Create: `docs/reports/segment-analyses/residential-installation.md`
- Create: `docs/reports/segment-analyses/financing-leasing.md`
- Create: `docs/reports/segment-analyses/ecommerce-marketplace.md`
- Create: `docs/reports/segment-analyses/om-monitoring.md`
- Create: `scripts/07_timeline_builder.py`
- Create: `scripts/08_metric_aggregator.py`

- [ ] **Step 1: Build aggregation script scripts/08_metric_aggregator.py**

```python
"""Aggregate per-company metrics into segment-level trends.

Output: data/processed/market-evolution.csv with year × segment × aggregate metric.
"""
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent.parent
METRICS = ROOT / "data/processed/company-metrics.csv"
COMPANIES = ROOT / "data/raw/companies.yaml"
OUT = ROOT / "data/processed/market-evolution.csv"

def main():
    import yaml
    cdata = yaml.safe_load((COMPANIES).read_text())
    company_segment = {c["slug"]: c["primary_segment"] for c in cdata["companies"]}
    df = pd.read_csv(METRICS)
    df["segment"] = df["company_slug"].map(company_segment)
    agg = df.pivot_table(
        index=["year", "segment"],
        columns="metric",
        values="value",
        aggfunc="sum",
    ).reset_index()
    agg.to_csv(OUT, index=False)
    print(f"✓ Wrote {OUT}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Build timeline builder scripts/07_timeline_builder.py**

```python
"""Build a chronological timeline merging policy events + company milestones."""
import pandas as pd
import yaml
from pathlib import Path

ROOT = Path(__file__).parent.parent
POLICY = ROOT / "data/raw/policy-events.yaml"
METRICS = ROOT / "data/processed/company-metrics.csv"
OUT = ROOT / "data/processed/timeline-events.csv"

def main():
    events = []
    pdata = yaml.safe_load(POLICY.read_text())
    for e in pdata["events"]:
        events.append({"date": e["date"], "kind": "policy", "title": e["title"], "company": None})
    mdf = pd.read_csv(METRICS)
    funding = mdf[mdf["metric"] == "funding_rmb"]
    for _, r in funding.iterrows():
        events.append({
            "date": f"{r['year']}-06-30",
            "kind": "funding",
            "title": f"{r['company_slug']} raised {r['value']:,.0f} RMB",
            "company": r["company_slug"],
        })
    pd.DataFrame(events).sort_values("date").to_csv(OUT, index=False)
    print(f"✓ Wrote {OUT}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run aggregations**

```
python3 scripts/08_metric_aggregator.py
python3 scripts/07_timeline_builder.py
```

Expected: `market-evolution.csv` and `timeline-events.csv` populated.

- [ ] **Step 4: Write segment analysis: residential-installation.md**

Structure each segment file as:

```markdown
# Segment: <Name>

## Market Lifecycle Phases
1. **Phase 1 — <years>**: <fragmentation/growth/consolidation/etc.>
   - Aggregate metrics: <total companies active, total revenue, market size>
   - Driving forces: <policy events, tech enablers>
   - Representative players: <2-3 with brief why>
2. **Phase 2 — ...**

## Business Model Innovations Timeline
| Year | Innovation | First-mover | Followers |
|------|-----------|-------------|-----------|
| 2017 | Direct-to-consumer rooftop sales | Company A | B, C |
| ...

## Competitive Landscape Evolution
- 2016: ~N companies, top-3 share X%
- 2020: ~N companies, top-3 share X%
- 2024: ~N companies, top-3 share X% (consolidation evidence)
- [Cite sources for company counts]

## Segment-Level Hypotheses

### Hypothesis 1: <Statement>
**Evidence:**
- [...]
**Counter-hypothesis & test:**
- [...]
**Verdict:** Supported / Partially supported / Insufficient evidence.

### Hypothesis 2: ...

## Key Insights for Korea Comparison
- [What's segment-specific that matters for adaptation]
```

Repeat for the other 3 segments.

- [ ] **Step 5: Self-review each segment file**

- ✅ Aggregate metrics traceable to company-level data
- ✅ Hypotheses are testable and tested
- ✅ Phase boundaries justified by data, not arbitrary
- ✅ Counter-hypotheses documented

- [ ] **Step 6: Commit**

```bash
git add scripts/07_timeline_builder.py scripts/08_metric_aggregator.py docs/reports/segment-analyses/
git commit -m "research: segment-level synthesis with lifecycle analysis (4 segments)"
```

---

### Task 5.2: Competitive Landscape Evolution

**Files:**
- Create: `docs/reports/competitive-landscape.md`

- [ ] **Step 1: Build year-by-year market share estimates**

For each year 2016-2026 and each segment:
- Identify the top 3-5 players (by revenue or customer count from `company-metrics.csv`)
- Compute approximate share (top-3 share, top-5 share) — use ranges if precise share unknown
- Note exits (acquisitions, defunct) and entries

- [ ] **Step 2: Write docs/reports/competitive-landscape.md**

```markdown
# Competitive Landscape Evolution (2016-2026)

## Methodology
[How shares were estimated, confidence levels, limitations]

## Year-by-Year Leadership

### 2016
**Residential Installation**: Top-3 = X, Y, Z (combined share ~Z%)
**Financing**: ...
[etc.]

### 2017
[same structure]

[... through 2026]

## Consolidation Wave Analysis
**Evidence of consolidation:**
- M&A deal count by year (from timeline-events)
- Top-3 share trend by segment
- Number of active companies trend

**Verdict:** Consolidation occurred most strongly in segment <X> during <years>, driven by <causal mechanism>.

## Cross-Segment Migrations
**Companies that crossed segments:**
- <Company> moved from <segment A> to <segment B> in <year> — driver: <reason>

[Document evidence for each crossing]
```

- [ ] **Step 3: Self-review**

- ✅ Share estimates have explicit error ranges
- ✅ Consolidation claim is quantified, not asserted
- ✅ Cross-segment migrations cited from company profiles

- [ ] **Step 4: Commit**

```bash
git add docs/reports/competitive-landscape.md
git commit -m "research: competitive landscape & consolidation wave analysis"
```

---

### Task 5.3: Failure Case Studies

**Files:**
- Create: `docs/reports/failure-cases.md`

- [ ] **Step 1: Identify 2-3 failed/exited companies**

From the 12-20 deep-dives, select companies with:
- Status = defunct, OR
- Status = acquired below founding valuation, OR
- Status = active but in long-term decline (revenue/customers shrinking 3+ years)

- [ ] **Step 2: Write docs/reports/failure-cases.md**

For each failure:

```markdown
## <Company Name>

### Trajectory
[Founding → peak → decline → exit, with dates and metrics]

### Hypothesized Failure Drivers (ranked by evidence)
1. **<driver>** [evidence: ★★★★]
2. **<driver>** [evidence: ★★★]
3. **<driver>** [evidence: ★★]

### Counterfactual Test
"If <factor X> had been different, would the outcome have changed?"
- [Comparison with similar company that survived]
- [What that company did differently]

### Lessons for Korean Market
- [Specific implication, e.g., "Don't over-leverage on 2018-style subsidies"]
```

- [ ] **Step 3: Self-review**

- ✅ Failure analysis is *evidence-based*, not narrative
- ✅ Counterfactual test grounds the analysis
- ✅ Lessons are specific and actionable for Korea

- [ ] **Step 4: Commit**

```bash
git add docs/reports/failure-cases.md
git commit -m "research: 2-3 failure case studies with counterfactual analysis"
```

---

## Phase 6: Theoretical Framework Application

### Task 6.1: Disruptive Innovation Analysis

**Files:**
- Create: `docs/reports/theory-disruptive-innovation.md`

- [ ] **Step 1: Map each company against Christensen disruption framework**

For each company:
- Initial target: low-end / underserved / mainstream?
- Performance trajectory: did they move upmarket?
- Incumbent response: ignored / dismissed / acquired?

Build a matrix.

- [ ] **Step 2: Write docs/reports/theory-disruptive-innovation.md**

```markdown
# Theoretical Lens: Disruptive Innovation

## Framework Application
[Brief Christensen recap, then how it applies to Chinese solar downstream]

## Disruption Pattern Findings

### Pattern 1: Low-end disruption (rural residential)
**Companies fitting:** A, B, C
**Evidence:** [Initial customer profile data, pricing strategies, incumbent dismissal quotes]
**Outcome:** [Did these companies move upmarket? Did incumbents respond?]

### Pattern 2: New-market disruption (financing-enabled new buyers)
**Companies fitting:** D, E
**Evidence:** [...]

### Pattern 3: Sustaining innovation (incumbent platforms upgrading)
**Companies fitting:** [if any incumbents adapted successfully]

## Theory Verdict
**Did the framework predict outcomes well?**
- [Where it predicted: which winners/losers it called]
- [Where it failed: anomalies the framework didn't capture]
- [What this tells us about Chinese market specifics]
```

- [ ] **Step 3: Commit**

```bash
git add docs/reports/theory-disruptive-innovation.md
git commit -m "research: disruptive innovation framework applied to data"
```

---

### Task 6.2: S-Curve & Industry Lifecycle

**Files:**
- Create: `docs/reports/theory-s-curve.md`

- [ ] **Step 1: Plot adoption curves per segment**

Using `market-evolution.csv`, identify each segment's S-curve position:
- Innovators (~2.5%): which years?
- Early adopters (~13.5%): which years?
- Early majority (~34%): which years?
- (Beyond, if applicable)

Use installed capacity, customer counts, or market size as the y-axis.

- [ ] **Step 2: Write docs/reports/theory-s-curve.md**

```markdown
# Theoretical Lens: S-Curve & Industry Lifecycle

## S-Curve Position by Segment (as of 2026)

| Segment | Curve Phase | Estimated % adoption | Evidence |
|---------|-------------|---------------------|----------|
| Residential install | Late majority | ~50% of addressable market | <data> |
| Financing | Early majority | ~25% | <data> |
| ... | ... | ... | ... |

## Phase Transition Analysis
**When did each segment cross the chasm (early adopter → early majority)?**
- Segment X: ~2019-2020. Trigger: <event>
- Segment Y: ~2021-2022. Trigger: <event>

## Lifecycle-Stage Strategy Implications
[For each segment phase, what strategies tend to win]

## Theory Verdict
[Where the lifecycle model predicted; where it didn't]
```

- [ ] **Step 3: Commit**

```bash
git add docs/reports/theory-s-curve.md
git commit -m "research: S-curve / lifecycle analysis across segments"
```

---

### Task 6.3: Network Effects & Platformization

**Files:**
- Create: `docs/reports/theory-platformization.md`

- [ ] **Step 1: Identify platform vs pipeline business models**

Per company:
- Pipeline: Linear value chain (buy materials → service → sell)
- Platform: Multi-sided (matches consumers ↔ installers ↔ financiers)

Mark transition years if applicable.

- [ ] **Step 2: Write docs/reports/theory-platformization.md**

```markdown
# Theoretical Lens: Platformization

## Platform Companies in the Sample
| Company | Pipeline → Platform Year | Platform Sides | Network Effect Type |
|---------|-------------------------|----------------|--------------------|
| ... | ... | ... | direct / indirect / data |

## Valuation Multiplier Effect
[Did platform companies achieve higher revenue multiples on exit/IPO?]

## Failed Platformizations
[Companies that tried but couldn't achieve liquidity]

## Theory Verdict
[Was platformization a winning strategy? Conditional on what?]
```

- [ ] **Step 3: Commit**

```bash
git add docs/reports/theory-platformization.md
git commit -m "research: platformization & network effect analysis"
```

---

## Phase 7: Korea-China Comparative Analysis

### Task 7.1: Structural Differences Audit

**Files:**
- Create: `docs/reports/korea-china-comparison.md` (Section 1)

- [ ] **Step 1: Build structural comparison table**

| Dimension | China | Korea | Implication |
|-----------|-------|-------|-------------|
| Total addressable rooftops | ~300M households | ~21M households | 14x scale gap |
| Government solar subsidy regime | Aggressive then tapered | Moderate, RPS-driven | Different incentive curves |
| Distributed PV regulation | Permissive | Restrictive (apt complexes) | BM A may not transfer |
| Consumer financing culture | Widely accepted | Conservative | Lease/PPA harder |
| Online B2C maturity | Very high (Alibaba, Pinduoduo) | High (Coupang) | E-commerce models translatable |
| Installer fragmentation | High → consolidating | Moderate, fragmented | Different starting point |
| Electricity market structure | Mixed grid | KEPCO-dominant | KEPCO is a key gatekeeper |
| ... | ... | ... | ... |

For each row, cite sources for both China and Korea numbers.

- [ ] **Step 2: Self-review**

- ✅ Each dimension has data (not opinion)
- ✅ Implications are specific (not generic "be careful")
- ✅ Korea data sources documented (KEPCO publications, MOTIE, KIER, etc.)

- [ ] **Step 3: Commit**

```bash
git add docs/reports/korea-china-comparison.md
git commit -m "research: Korea-China structural differences audit"
```

---

### Task 7.2: Model-by-Model Applicability

**Files:**
- Modify: `docs/reports/korea-china-comparison.md` (add Section 2)

- [ ] **Step 1: For each Chinese business model, assess Korean applicability**

Model template:

```markdown
## Model: <Name> (e.g., Whole-county distributed solar leasing)

**Chinese exemplar:** <Company name>
**How it works in China:** [2-3 sentences]
**Why it succeeded in China:** [Drivers from earlier analysis]

### Korean Applicability Analysis

#### Required preconditions
1. <Precondition>: <China value> vs <Korea value> — Met / Partially met / Not met
2. ...

#### Adaptations needed
- <Adaptation 1>: <why and what>
- ...

#### Risk factors
- <Risk 1>: <impact on viability>

#### Verdict
**Confidence:** ★★★★ Highly applicable / ★★★ Adaptable / ★★ Difficult / ★ Not viable
**Reasoning:** [One paragraph integrating preconditions, adaptations, risks]
```

Cover at least 5-7 distinct business models.

- [ ] **Step 2: Self-review**

- ✅ Each model verdict is justified by Chinese evidence + Korean preconditions
- ✅ Confidence ratings are calibrated to evidence strength
- ✅ Adaptation suggestions are specific (not "needs to be localized")

- [ ] **Step 3: Commit**

```bash
git add docs/reports/korea-china-comparison.md
git commit -m "research: model-by-model Korean applicability analysis"
```

---

## Phase 8: Final Report Synthesis

### Task 8.1: Executive Summary & Final Report Compilation

**Files:**
- Create: `docs/reports/final-report.md`
- Create: `scripts/09_report_generator.py`

- [ ] **Step 1: Optional — Build report assembler scripts/09_report_generator.py**

If desired, write a script that concatenates all sub-reports into a single `final-report.md` with proper section numbering and TOC.

```python
"""Concatenate sub-reports into final-report.md with TOC."""
from pathlib import Path

ROOT = Path(__file__).parent.parent
REPORTS = ROOT / "docs/reports"
OUT = REPORTS / "final-report.md"

ORDER = [
    ("# 1. Executive Summary", "executive-summary.md"),
    ("# 2. Theoretical Framework", None),
    ("## 2.1 Disruptive Innovation", "theory-disruptive-innovation.md"),
    ("## 2.2 S-Curve / Lifecycle", "theory-s-curve.md"),
    ("## 2.3 Platformization", "theory-platformization.md"),
    ("# 3. Policy Timeline", "policy-timeline.md"),
    ("# 4. Segment Analyses", None),
    ("## 4.1 Residential Installation", "segment-analyses/residential-installation.md"),
    ("## 4.2 Financing & Leasing", "segment-analyses/financing-leasing.md"),
    ("## 4.3 E-commerce Marketplace", "segment-analyses/ecommerce-marketplace.md"),
    ("## 4.4 O&M & Monitoring", "segment-analyses/om-monitoring.md"),
    ("# 5. Company Deep-Dives", None),
    # ... company profiles inserted here
    ("# 6. Competitive Landscape", "competitive-landscape.md"),
    ("# 7. Failure Case Studies", "failure-cases.md"),
    ("# 8. Korea-China Comparative Analysis", "korea-china-comparison.md"),
    ("# 9. Conclusions & Forecast", "conclusions.md"),
]

def main():
    parts = []
    for header, filename in ORDER:
        parts.append(header + "\n")
        if filename:
            parts.append((REPORTS / filename).read_text())
        parts.append("\n---\n")
    # Append company profiles
    for prof in sorted((REPORTS / "company-profiles").glob("*.md")):
        parts.append(f"\n## {prof.stem}\n")
        parts.append(prof.read_text())
        parts.append("\n---\n")
    OUT.write_text("\n".join(parts))
    print(f"✓ Wrote {OUT}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write executive-summary.md**

3-page max. Structure:

```markdown
# Executive Summary

## Research Question
[Restate the question]

## Methodology Brief
[1 paragraph: 4 segments × 12-20 companies × 10 years × multi-source verification]

## Key Findings
1. **<Finding 1>**: [1-paragraph statement with confidence level + main evidence]
2. **<Finding 2>**: [...]
3. **<Finding 3>**: [...]
4. **<Finding 4>**: [...]

## Key Business Model Innovations Identified
- <Innovation 1>: <originator, year, mechanism>
- ...

## Korea Applicability Verdict
[Top 3 most-applicable models, top 3 risks, summary recommendation]

## Caveats & Limitations
[Honest disclosure of data gaps and confidence limits]
```

- [ ] **Step 3: Write conclusions.md**

```markdown
# Conclusions & Forecast

## What China Has Learned (2016-2026)
[Synthesis of evolution: what worked, what didn't, where the market is now]

## Forecasted Next-Phase Evolution (2026-2030)
- [Prediction 1] [Confidence ★★★]
- [Prediction 2] [Confidence ★★]

## Strategic Options for Korea
1. **Option A: <Direct adoption>** — [where, how, who]
2. **Option B: <Adaptation>** — [where, how, who]
3. **Option C: <Net-new model>** — [where, how, who]

## High-Conviction Recommendations
[Top 3 recommendations with reasoning grounded in earlier sections]
```

- [ ] **Step 4: Run report assembler**

```
python3 scripts/09_report_generator.py
```

Expected: `docs/reports/final-report.md` exists, all sections present.

- [ ] **Step 5: Commit**

```bash
git add scripts/09_report_generator.py docs/reports/executive-summary.md docs/reports/conclusions.md docs/reports/final-report.md
git commit -m "research: final report synthesis with executive summary and conclusions"
```

---

## Phase 9: Quality Review & Final Polish

### Task 9.1: Rigor Audit

**Files:**
- Create: `docs/methodology/rigor-audit.md`

This is the final gate before declaring the report complete.

- [ ] **Step 1: Run automated checks**

Write `scripts/10_rigor_audit.py`:

```python
"""Audit the report against rigor criteria from the design doc."""
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent.parent
METRICS = ROOT / "data/processed/company-metrics.csv"
SOURCES = ROOT / "data/processed/source-index.csv"

def audit():
    df = pd.read_csv(METRICS)
    src = pd.read_csv(SOURCES)
    issues = []

    # Check: every metric has ≥ 1 source
    metrics_without_source = df[~df["metric_id"].isin(src["metric_id"])]
    if len(metrics_without_source):
        issues.append(f"❌ {len(metrics_without_source)} metrics without sources")

    # Check: ★★★+ for non-flagged claims
    low_conf = df[(df["confidence"] <= 2) & (~df["notes"].fillna("").str.contains("uncertain|estimate"))]
    if len(low_conf):
        issues.append(f"⚠️  {len(low_conf)} ★★ or below metrics without uncertainty flag")

    # Check: each company has ≥ 5 years of data
    by_company = df.groupby("company_slug")["year"].nunique()
    sparse = by_company[by_company < 5]
    if len(sparse):
        issues.append(f"⚠️  Companies with <5 years data: {list(sparse.index)}")

    return issues

if __name__ == "__main__":
    issues = audit()
    if not issues:
        print("✓ All rigor checks passed.")
    else:
        for i in issues:
            print(i)
```

Run: `python3 scripts/10_rigor_audit.py`

- [ ] **Step 2: Run manual review checklist**

For the final report, verify each item from the design doc Section 7:

- [ ] Every major claim has ≥2 independent sources OR company official + verification
- [ ] No data points marked ★ without explicit "high uncertainty" flag
- [ ] All 12-20 companies have ≥5 years of tracked data
- [ ] Causal claims labeled "inferred" vs "documented"
- [ ] Counter-hypotheses documented for all main arguments
- [ ] Data gaps explicitly disclosed
- [ ] Policy timeline matches market evolution
- [ ] Korea comparison is granular, not generic
- [ ] Failed companies get same rigor as successful ones
- [ ] Report reads as integrated narrative

- [ ] **Step 3: Document audit in docs/methodology/rigor-audit.md**

```markdown
# Rigor Audit Report (final)

## Automated Checks
[Output of 10_rigor_audit.py]

## Manual Checklist Review
[For each of the 10 items above: ✓ Pass with evidence, or ⚠️ Issue + remediation]

## Outstanding Limitations
[What we honestly couldn't resolve]

## Sign-off
- Audit performed: <date>
- Total claims reviewed: <count>
- Total ★★★+ claims: <count> (<%>)
- Total ★★ or lower (with flags): <count>
- Total ★ unflagged: <count> (must be 0)
```

- [ ] **Step 4: Address any issues found**

For each ⚠️ or ❌ in the audit:
- Either upgrade evidence (find more sources)
- Or downgrade the claim (mark "inferred" / add uncertainty range)
- Or remove the claim if neither is possible

- [ ] **Step 5: Commit**

```bash
git add scripts/10_rigor_audit.py docs/methodology/rigor-audit.md
git commit -m "research: rigor audit pass with all critical issues resolved"
```

---

### Task 9.2: Final Read-Through

- [ ] **Step 1: Read final-report.md end to end**

As if for the first time. Watch for:
- Inconsistencies between sections (Section 5 contradicts Section 8?)
- Unsupported assertions (every "increased significantly" needs a number)
- Generic platitudes (replace with specific findings)
- Korean section quality (is it as deep as the Chinese sections?)

Make edits inline.

- [ ] **Step 2: Decision-quality test**

Ask: *"If a Korean VC read this and made a $10M decision, would they have what they need?"*
- If hedging on a key question → research more or downgrade the claim
- If two sections contradict → resolve or document explicitly
- If a key metric is ★★ → either upgrade or downgrade conclusion

- [ ] **Step 3: Final commit**

```bash
git add docs/reports/final-report.md docs/reports/<any-edited-files>
git commit -m "research: final read-through with decision-quality polish"
```

- [ ] **Step 4: Tag the release**

```bash
git tag -a v1.0-research-complete -m "China solar downstream analysis: research complete, decision-grade"
```

---

## Self-Review Notes (Plan Author)

### Spec Coverage Check
- ✅ 4-segment definition + dynamic adjustment → Phase 2.1, mid-Phase-4 checkpoint
- ✅ 12-20 companies, new entrants only → Phase 2.1 selection criteria, Phase 4 deep-dives
- ✅ 10-year timeline (2016-2026) → All metric records, segment phase analyses
- ✅ Wayback Machine + Playwright + Chinese DBs → Phases 3.1-3.4
- ✅ Confidence grading system → Task 1.3, applied in every Phase 4 task
- ✅ Causal vs correlational distinction → Required in profile templates
- ✅ Counter-hypotheses → Required in profiles, segments, theory sections
- ✅ Disruptive Innovation, S-curve, Platformization → Tasks 6.1-6.3
- ✅ Policy timeline overlay → Task 2.2, threaded through all analyses
- ✅ Failure case studies → Task 5.3
- ✅ Korea-China structural + model-level comparison → Tasks 7.1-7.2
- ✅ Final report structure (9 sections) → Task 8.1 with 09_report_generator.py
- ✅ Rigor audit → Task 9.1 with both automated + manual checks
- ✅ Decision-quality standard → Task 9.2

### Placeholder Scan
- No "TBD" or "implement later" present.
- All code blocks contain actual code (not pseudo-stubs).
- All research tasks specify required deliverable structure.

### Type Consistency
- `Company.slug`, `MetricRecord.company_slug`, `TimelineEvent.company_slug` — all consistent.
- `ConfidenceLevel` enum used consistently across grader, schema, and audits.
- `Segment` enum names consistent in YAML, CSV, and reports.

### Known Limitations of This Plan
1. **Chinese DB scraping may be heavily rate-limited.** Manual fallback is documented; expect to spend significant time on manual lookups for ★★★★+ corporate data.
2. **Wayback Machine coverage is uneven.** Some Chinese sites have weak archive coverage; we document gaps rather than fabricate data.
3. **Translation accuracy.** Chinese sources require careful translation. Quoted text should be preserved in original + translation, especially for nuanced business model descriptions.
4. **Time horizon.** This is not a 1-week project. Realistic: 6-12 weeks of focused work to reach decision-grade quality.

---

## Execution Recommendations

**Order of execution:**
1. Phase 1 (infrastructure) — 1-2 days
2. Phase 2 (discovery + policy timeline) — 3-5 days
3. Phase 3 (collection scripts + initial run) — 3-5 days
4. Phase 4 (deep-dives) — bulk of project, 4-6 weeks (1-2 companies/week with rigor)
5. Phases 5-7 (synthesis + theory + Korea) — 2-3 weeks
6. Phase 8-9 (final report + audit) — 1 week

**Mid-project pivot points:**
- After Phase 2.1: re-evaluate seed list against Phase 1 schemas
- After Phase 4 task 5: re-evaluate segment definitions
- After Phase 5: decide if any segment needs more company coverage

**Quality > Speed**, per user direction.
