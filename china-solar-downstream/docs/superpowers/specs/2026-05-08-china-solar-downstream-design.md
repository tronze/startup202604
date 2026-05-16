# Design Spec: China Solar Downstream Business Model Analysis
## Comprehensive 10-Year Timeline & Korean Applicability Study

**Project**: Startup202605 / China Solar Downstream  
**Author**: Research Team  
**Date**: 2026-05-08  
**Scope**: 4-segment analysis, 12-20 companies, 2016-2026 timeline, PhD-level rigor  

---

## Executive Summary

This research aims to produce a **doctoral-level analytical report** on how China's downstream solar industry evolved from 2016-2026, tracking business model innovation, market consolidation, and competitive dynamics across four key segments. The output will inform whether Korean market can replicate or adapt Chinese success models.

**Key Deliverables**:
1. Comprehensive 10-year business model evolution timeline (policy overlaid)
2. Deep-dive analysis of 12-20 companies (new market entrants only)
3. Competitive landscape evolution (from fragmentation to consolidation)
4. Failure case studies (what didn't work)
5. Korea-China comparative analysis with applicability framework
6. Integrated narrative explaining industry lifecycle

---

## Section 1: Research Scope & Segment Definition

### Four Downstream Segments (Initial Hypothesis)

**Segment 1: Residential Solar Installation & Sales**
- Direct-to-consumer residential rooftop solar sales and installation
- Timeline focus: DIY/small-scale installer era (2016-2019) → regional chain expansion (2019-2022) → platform transformation (2022-2026)
- Expected players: Local installers → regional leaders → national platforms

**Segment 2: Solar Financing & Leasing**
- Alternative consumer financing models (lease, ESCO, power-purchase agreements)
- Timeline focus: Emerging segment (2016-2019) → explosive growth with policy support (2019-2022) → market maturation (2022-2026)
- Expected players: Finance startups → specialized solar lease companies → IPOs

**Segment 3: Online Solar Marketplace & E-commerce**
- Online platforms for solar equipment, services, and consumer education
- Timeline focus: B2B marketplaces (2016-2019) → B2C expansion (2019-2022) → ecosystem integration (2022-2026)
- Expected players: Equipment resellers → comprehensive platforms → mega-platforms

**Segment 4: Solar O&M & Monitoring Services**
- Post-installation operation, maintenance, and performance monitoring
- Timeline focus: Local service providers (2016-2019) → cloud-based platforms (2019-2022) → AI-driven predictive O&M (2022-2026)
- Expected players: Garage-style shops → tech-enabled service companies → AI platforms

### Dynamic Segment Adjustment Principle
- **These segments are hypothetical starting points, not dogma**
- During research, if evidence shows another segment is more important, we pivot
- If a company straddles multiple segments, we track it holistically (boundary-crossing innovation is itself a finding)
- Final segment count may be 3-5 (not fixed at 4)
- **Priority: Industrial significance over initial classification**

---

## Section 2: Company Selection & Research Framework

### Discovery & Selection Process

**Phase 1: Initial Mapping**
- Identify 15-25 candidate companies across 4 segments from public sources (news, industry reports, patent databases)
- Target: **New market entrants only** (founded after 2012, grew primarily 2016-2026)
- Exclude: State-owned enterprises, pre-2012 established corporates leveraging existing infrastructure

**Phase 2: Significance Filtering**
- Criteria for inclusion:
  1. **Clear growth evidence**: 3x+ revenue growth or 5x+ customer growth during any 3-year window
  2. **Business model innovation**: Demonstrable shift from standard model (e.g., first to introduce financing, first online marketplace, first AI monitoring)
  3. **Market impact**: 3+ independent sources noting company as "market shaper" or "disruptor"
  4. **Information availability**: Sufficient public data for 10-year reconstruction

**Phase 3: Final Selection (12-20 companies)**
- Aim: 3-5 per segment (flexible based on significance)
- Mix: market leaders (5), fast-growth challengers (5), interesting failures (2-3)

### Research Principle: Data-Driven Re-segmentation
- If a company reveals a 5th important segment not initially identified → add it
- If a segment proves marginal → deprioritize or remove
- Final analysis driven by what markets actually did, not pre-conceived categories

---

## Section 3: Data Collection Methodology (PhD-Level Rigor)

### Multi-Layer Collection Strategy

#### A. Web Archive & Historical Reconstruction
- **Wayback Machine (archive.org)**
  - Company website snapshots (all range.)
  - Service descriptions, pricing models, feature evolution, business model pivot
  - Extract: What did they offer? How did positioning change?

- **Headless Playwright Automation**
  - Auto-scrape Chinese media archives (新华网, 人民网, 36氪, 钛媒体)
  - Query: "[Company Name] + [2017-2019 keywords: 融资, 成长, 模式, etc.]"
  - Extract: News timeline, funding announcements, strategy pivots

- **Chinese Corporate Databases**
  - 企查查 (Qcc.com): Registration data, capital structure, investor relations
  - 天眼查 (Tyc.com): Financing rounds, executive changes, litigation
  - 融360 (Rong360): Loan/lease product database with historical snapshots
  - Extract: Funding timeline, growth metrics, business registration changes

- **Chinese Media Archives**
  - Tech media deep-dives: 36氪, 钛媒体, 中国能源报, 新能源情报
  - Government announcements: 国家能源局 (NEA), 工信部 (MIIT) policy documents
  - Extract: Policy changes, market events, company announcements

#### B. Quantitative Data Extraction
- **Metrics to track per company per year**:
  - Revenue (RMB, with confidence level)
  - Customer count / installations
  - Funding raised (round by round)
  - Valuation (if available)
  - Market share % (calculated from segment size estimates)
  - Key product/service launches
  - M&A activity (buyer/seller/price)

- **Data source hierarchy**:
  1. Company official IR releases / annual reports (★★★★★)
  2. Audited financial statements (if IPO/listed) (★★★★★)
  3. News articles with specific figures from 2+ independent sources (★★★☆☆)
  4. Industry analyst reports (IEA, BNEF, etc.) (★★★☆☆)
  5. Estimated/reverse-engineered from market size - company share (★★☆☆☆)
  6. Inference from comparable companies (★★☆☆☆)

#### C. Business Model Evolution Tracking
- **Annual snapshots** (per company):
  - Service offering (what, to whom, how)
  - Revenue model (direct sales, commission, subscription, etc.)
  - Customer acquisition channels
  - Partnerships
  - Technology positioning (hardware, software, AI/IoT adoption)

- **Data sources for model evolution**:
  - Wayback Machine website evolution
  - Press releases & investor decks (Wayback Machine archived)
  - Competitor comparisons (news articles contrasting approaches)
  - Patent filings (timing of innovation)
  - Executive interviews / articles (what they say about strategy)

#### D. Trustworthiness Validation
- **Multi-source verification**:
  - Same claim appearing in ≥2 independent sources = medium confidence
  - Same claim + company official confirmation = high confidence
  - Quantitative fact (e.g., "2020 revenue 500M RMB"):
    - Check across 3+ sources, note discrepancies
    - If discrepant: use range ("estimated 400-600M RMB")

- **Anomaly detection**:
  - Sudden 10x growth → investigate root cause (policy? IPO? M&A? Product launch?)
  - Market exit → document reason (bankruptcy, acquisition, strategic pivot)
  - Model shift → identify trigger event

- **Source documentation standard**:
  - Every claim gets notation: `[Source: Wayback 2019-06 snapshot, Verified: 2 news articles]`
  - Data grades applied: ★★★★★ down to ★☆☆☆☆
  - Data gaps flagged: "2017-2018 revenue not public, estimated via market size model"

---

## Section 4: Analysis Framework (Hypothesis & Inference)

### Theoretical Frameworks Applied

#### A. Disruptive Innovation Lens
**Central question**: How did new entrants create foothold while incumbents dominated?

**Hypothesis to test**:
- Incumbents focused on large, profitable segments (utility-scale, industrial rooftops)
- New entrants targeted overlooked segments (small residential, underserved rural areas, first-time solar buyers)
- New entrant advantage: lower cost structure, specialized offering, direct consumer relationship
- Incumbent counter-response: 2020+ acquisitions, own consumer brands, model copying

**Evidence to collect**:
- Initial target customer profile (geographic, income, building type) for each founder company
- Compare new entrant target vs incumbent target in 2016-2018
- Track when incumbents entered residential/leasing (and what they paid/invested)
- Document which incumbent models succeeded vs failed

#### B. Industry Lifecycle (S-Curve)
**Central question**: Where was each segment on adoption curve each year?

**Hypothesis to test**:
- Residential solar: Early adoption (2016-2018) → Rapid growth (2019-2021) → Market saturation (2022-2026)
- Financing: Embryonic (2016-2018) → Explosive growth (2019-2021) → Market consolidation (2022-2026)
- E-commerce: Emerging (2016-2018) → Rapid adoption (2019-2022) → Platform maturity (2022-2026)
- O&M: Nascent (2016-2019) → Growth phase (2020-2023) → Still expanding in 2026

**Evidence to collect**:
- Market size estimates per segment, per year (from industry reports)
- # of active companies per segment (fragmentation index)
- M&A activity (consolidation wave timing)
- New entrant rate (when did founders slow down)
- Profitability trends (are incumbents profitable? when do margins compress)

#### C. Network Effects & Platformization
**Central question**: Which companies achieved platform economics, and how?

**Hypothesis to test**:
- Early installers were pure service providers (captured value = installation fee only)
- Winners shifted to platform models (ecosystem of installers, financiers, O&M providers)
- Platform shift enabled 5-10x valuation multiples
- Non-platformable segments (pure installation services) faced commoditization pressure

**Evidence to collect**:
- Timeline: when does each company announce "open platform" or "third-party partners"
- Business model data: % revenue from direct services vs platform commission
- Valuation multiples (revenue × multiple) before/after platformization
- IPO positioning: do successful IPOs emphasize "platform" narrative? Do failed companies claim they didn't?

---

### Section 5: Verification Rigor & Analytical Standards

#### A. Hypothesis Verification Framework

**For every major claim: Require Evidence Structure**

| Claim Type | Verification Required | Acceptable Evidence | Insufficient Evidence |
|------------|----------------------|-------------------|----------------------|
| **Growth fact** (e.g., "2020 revenue doubled") | 3 independent sources OR company official + audit | ① Company IR + ② 2 news sources ③ matching figures | Only 1 news source, or range varies >30% |
| **Market shift** (e.g., "financing became dominant model") | ① Timing pinpointed ② Market share quantified ③ Causal mechanism | ① Policy change date + ② competitor strategy announcements + ③ customer behavior data | "Financing became popular" without dates/numbers/causation |
| **Business model change** (e.g., "pivoted to platform") | ① Before/after service comparison ② Timing clear ③ Revenue structure change | ① Wayback site evolution ② investor deck 2019 vs 2022 ③ IPO S-1 business segment breakdown | Marketing claims only, no operational evidence |
| **Failure/exit** (e.g., "company folded due to policy") | ① Timeline documented ② Root cause hypotheses ranked ③ Counterfactual scenarios | ① Last funding date, IPO attempt, acquisition/bankruptcy filing ② Policy timeline overlap ③ competitor analysis | "Company disappeared, probably ran out of money" |

#### B. Data Confidence Grading System

```
★★★★★ (Highest): Company official + 2+ media sources + audited report (if applicable)
        Example: IPO filing with SEC/CSRC + 2+ news articles + investor confirmation

★★★★☆ (High): Company official + 1 media verification
        Example: Press release + news article with matching figures

★★★☆☆ (Medium): 2-3 independent media sources in agreement, OR company official but unverified
        Example: 3 tech media articles citing same revenue figure (no company source)

★★☆☆☆ (Low): 1 media source only, OR estimates from market models
        Example: "Market size X, company has Y% share, therefore revenue = X × Y"

★☆☆☆☆ (Very Low): Inference/extrapolation only, significant uncertainty
        Example: "Estimated from patent filing trends + competitor salary data"
```

**Final report standard**: Main arguments supported by ★★★+ evidence. Supporting points can use ★★ evidence if clearly flagged. Any ★☆ evidence highlighted as "high uncertainty" with error ranges.

#### C. Integrated Analysis (Not List-of-Facts)

**Forbidden structure**: 
```
Company A: Founded 2015, IPO 2023, revenue 2B RMB
Company B: Founded 2017, revenue 1B RMB, still private
Company C: Founded 2016, acquired 2021
(Pattern: ???)
```

**Required structure**:
```
MARKET HYPOTHESIS: "2016-2019 = Fragmentation, 2019-2022 = Specialization, 2022-2026 = Consolidation"

EVIDENCE THREAD 1 - Policy Trigger (2019):
- Government solar subsidy reform (date: 2019-06) → Residential market eligible for first time
- [Source: 国家能源局 official document]
- [Consequence]: Consumer purchasing power ↑ 300% in first year
- [Company response]: All 5 studied companies announced financing partnerships in 2019-2020

EVIDENCE THREAD 2 - Competitive Fragmentation (2019-2021):
- Number of active companies: 2018 ~45 → 2020 ~150 → 2021 ~180 (peak)
- Why? Low barriers to entry + high customer demand = gold rush
- [Source: 企查查 registration data + news coverage of "solar startups"]

EVIDENCE THREAD 3 - Consolidation Wave (2021-2023):
- M&A activity: 2021 ~8 deals → 2022 ~25 deals → 2023 ~40 deals
- Acquirers: 100% from top-5 companies (concentration)
- Valuations: Acquisition multiples 3-5x revenue (suggests efficiency gains expected)
- [Source: Crunchbase, local VC news, company announcements]

SYNTHESIS:
Policy ↑ demand → Entry ↑ → Competition ↑ → Margin ↓ → Consolidation ↑ → Platform winners emerge

Why some companies succeeded:
- Company A: First to integrate financing + installation = ecosystem lock-in
- Company B: Built B2C brand while competitors stayed B2B
- Company C: Focused on rural, ignored by top-3 = blue ocean (until 2023)

Why some failed:
- Company X: Pure installation play, commoditized by 2021
- Company Y: Tried platformization too late, losing 60% margin to integrate
- Company Z: Over-leveraged on 2019 boom, couldn't adapt to 2022 subsidy reduction
```

#### D. Uncertainty & Limitations Disclosure

**Required format for ambiguous data points**:

❌ **Bad**: "Market size was 50 billion RMB in 2020"

✅ **Good**: 
- "Market size estimated at 45-55 billion RMB in 2020 (±10% range) based on: [Source A: 45B] [Source B: 55B] [Source C: industry survey]"
- "Estimates assume installed capacity 20GW with average system cost 2.5M RMB/MW; if actual cost 2.0-3.0M, range widens to 40-60B"
- "⚠️ This estimate has HIGH UNCERTAINTY because [government subsidy effect unclear / pricing data from only 3 vendors / etc.]"

**Data gap documentation**:
- Years 2017-2019: Insufficient public data for Company X (firm was private, pre-Series B) → Reconstructed from [Wayback site copy] + [competitor benchmarking] (★★☆☆☆ confidence)

#### E. Falsifiable Logic (Robust Arguments)

**For each main hypothesis: Include counter-hypothesis & how we'd know if wrong**

Example:

**Hypothesis**: "Financing leasing business model was THE key innovation, not installation or O&M"

**Counter-hypothesis 1**: "Actually, platformization (ecosystem integration) was more important than financing"
- **How we'd know**: If platform companies without financing grew faster than financing companies without platform
- **Our evidence**: [Data on platform-first vs financing-first company growth rates]

**Counter-hypothesis 2**: "Market was driven by policy/subsidies, not business model innovation"
- **How we'd know**: If all companies grew equally regardless of model, or if growth stopped when subsidies ended
- **Our evidence**: [Companies with better models grew 3-5x more than commodity players even controlling for policy phases]

**Counter-hypothesis 3**: "Chinese success doesn't transfer to Korea due to market structure"
- **How we'd know**: Detailed Korea-China differences in [regulation, consumer preference, capital access, ecosystem maturity]
- **Our evidence**: [Comparative analysis in Section 6]

---

## Section 6: Report Structure & Output Format

### Final Deliverable: Integrated Analytical Report

**Target structure**:

```
1. EXECUTIVE SUMMARY (2-3 pages)
   - 3-4 key findings
   - Core business model innovations identified
   - Korea applicability verdict (yes/no/conditional)

2. THEORETICAL FRAMEWORK (3-4 pages)
   - Why Chinese downstream solar evolved this way
   - S-curve dynamics, disruptive innovation, network effects
   - How theory predicts market evolution

3. MARKET EVOLUTION TIMELINE (6-8 pages)
   - Policy overlay (dates, impact)
   - Segmented market evolution (size, fragmentation, consolidation)
   - Graphical representation (charts/timeline)

4. COMPANY DEEP-DIVES (2 pages × 12-20 companies = 24-40 pages)
   - Each company: Founding → Growth → Inflection → Current status
   - Hypothesis about success/failure + evidence
   - Positioning relative to competitors

5. COMPETITIVE LANDSCAPE EVOLUTION (4-6 pages)
   - Year-by-year: Who led, who exited, who pivoted
   - Market share evolution (top 5, top 10)
   - Consolidation wave analysis

6. FAILURE CASE STUDIES (3-4 pages)
   - 2-3 companies that lost: Why? What to avoid?
   - Lessons for Korean market entrants

7. KOREA-CHINA COMPARATIVE ANALYSIS (5-8 pages)
   - Structural differences (market, policy, consumer, capital)
   - Model-by-model applicability (which Chinese BM works in Korea?)
   - Risk factors (what could go wrong)
   - Success factors (what's essential to replicate)

8. CONCLUSION & FORECAST (2-3 pages)
   - What China learned (next evolution stage?)
   - Korea's strategic options
   - High-conviction recommendations

9. APPENDICES
   - Data tables (all company metrics by year)
   - Source documentation (every claim → source → confidence level)
   - Methodology notes
   - Unexplored leads (what we couldn't verify, why, future research)
```

**Writing standard**: Each section must advance a coherent argument. Not a data dump—a narrative with evidence.

---

## Section 7: Quality Gates & Verification Checklist

### Pre-Submission Self-Review (Rigor Checks)

- [ ] Every major claim has ≥2 independent sources OR company official + verification
- [ ] No data points marked ★☆☆☆☆ without explicit "high uncertainty" flag
- [ ] All 12-20 companies have ≥5 years of tracked data (2016-2021 minimum)
- [ ] Causal claims are labeled "inferred" vs "documented"
- [ ] Counter-hypotheses documented for all main arguments
- [ ] Data gaps explicitly disclosed (don't hide 2-year unknowns)
- [ ] Policy timeline matches market evolution (causation story is plausible)
- [ ] Korea comparison is deep (not just "market size is 1/20th of China")
- [ ] Failed companies get same rigor as successful ones (no cherry-picking)
- [ ] Report reads as integrated narrative, not company factsheets

### Final Review: Decision Quality Standard

**Test**: If a Korean VC or executive were deciding whether to invest based on this report, would they have confidence?

- If the analysis hedges on important questions → research more
- If contradictions exist between sections → resolve or document explicitly
- If key metrics are speculative → collect better data or mark "insufficient evidence"
- If a conclusion relies on a ★★☆☆☆ fact → either upgrade the fact or downgrade the conclusion

---

## Project Structure

```
china-solar-downstream/
├── README.md                          # Project overview
├── docs/
│   ├── superpowers/
│   │   └── specs/
│   │       └── 2026-05-08-china-solar-downstream-design.md  # This document
│   └── reports/
│       └── final-report.md           # Output: Integrated analytical report
├── data/
│   ├── raw/
│   │   ├── company-profiles.csv      # Company founding, segment, founding team
│   │   ├── financial-data.csv        # Revenue, customers, funding per year
│   │   ├── policy-timeline.csv       # Government policy changes by date
│   │   └── source-index.xlsx         # All sources with URLs, access dates, confidence grades
│   ├── processed/
│   │   ├── company-metrics-clean.csv # Verified, confidence-graded dataset
│   │   ├── market-evolution-summary.csv
│   │   └── korea-china-comparison.csv
│   └── archives/
│       └── wayback-snapshots/        # Archived web snapshots (references)
└── scripts/
    ├── data-validation.py            # Verify data consistency, flag anomalies
    ├── confidence-grading.py         # Auto-grade data sources
    └── timeline-generator.py         # Generate market evolution visualizations
```

---

## Success Criteria

This research is **complete & credible** when:

1. ✅ All 12-20 companies have documented 10-year timelines (with data gaps explicitly flagged)
2. ✅ Market evolution narrative is supported by policy + quantitative data + company behavior
3. ✅ Each main conclusion backed by ≥3 independent evidence threads
4. ✅ Failure cases analyzed with same rigor as successes
5. ✅ Korea applicability is granular (not just "yes" or "no", but "model X works if Y conditions exist")
6. ✅ Report is readable as integrated narrative, with appendices for detail
7. ✅ All sources documented with confidence grades
8. ✅ Uncertainty ranges given for quantitative claims
9. ✅ Methodology transparent enough for peer review
10. ✅ An executive could make a business decision based on findings with confidence

---

## Notes for Implementation

- **Timeline**: No fixed deadline. Quality > speed. Research until confidence reaches ≥★★★ for all major claims.
- **Flexibility**: If research reveals that "business model innovation" differs from expected segments → restructure accordingly.
- **Tool permissions**: Will use Wayback Machine, Playwright headless browsing, multiple API sources, and Chinese corporate databases. All automated transparently.
- **Handoff**: Deliver structured data spreadsheets + final report markdown file + source index (for verification).

