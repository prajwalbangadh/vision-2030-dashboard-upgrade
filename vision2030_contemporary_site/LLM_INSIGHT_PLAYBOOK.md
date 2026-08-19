# Vision 2030 Dynamic Insight and Visualization Playbook

This file is the operating contract for any LLM, coding assistant, or analyst that adds narrative insights or visualizations to this site.

The objective is not to produce more commentary. The objective is to produce a small number of useful, reproducible observations whose evidence can be traced to the latest audited workbook run.

## 1. Start with the latest run

Work from the project root:

```bash
cd /Users/prajwalbang/Downloads/vision2030_contemporary_site_upgrade
python3 vision2030_contemporary_site/run_vision2030.py --build-only
```

By default, the launcher searches the project root and `output/` for source files matching:

```text
*/vision2030_business_table_*.xlsx
```

It ignores Excel lock files beginning with `~$` and selects the source workbook with the latest timestamp in its filename. Corrected workbooks under `reconciliation/corrected_output/` are historical audit artifacts and are not normal website inputs. Do not hardcode a previously observed timestamp.

To use a specific workbook intentionally:

```bash
python3 vision2030_contemporary_site/run_vision2030.py \
  --workbook /absolute/path/to/workbook.xlsx \
  --mapping-audit /absolute/path/to/division_mapping_audit.csv \
  --build-only
```

Do not generate or publish insights if the build raises an error or if `generated/validation_summary.json` does not contain:

```json
{"auditPass": true}
```

## 2. Source-of-truth order

Use sources in this order:

1. The latest selected `vision2030_business_table_*.xlsx` workbook is the immutable analytical source. Its `Division` cells are never rewritten by the website build.
2. `generated/normalized_record_audit.csv` is the preferred row-level source for analysis and narrative generation.
3. `generated/validation_summary.json` proves which workbook was used and whether normalization passed.
4. `reconciliation/source_mapping/<source timestamp>/division_mapping_audit_*.csv` is the separate matching provenance source. It must contain exactly one attached audit row per detail record and its `Original Division` must exactly match the source workbook.
5. `site_builder.py` defines aliases, units, goal parsing, hierarchy normalization, and conservative derived-status rules.
6. `assets/vision2030.js` defines the current filter cohorts and visualization calculations.

Never use a number from an old screenshot, previous chat response, README example, or prior output directory when a newer audited run exists.

## 3. Fields that must travel together

Never cite a value without preserving its analytical context:

- Business Area
- Metric
- Source Division (unchanged workbook value)
- Matched Division (derived grouping)
- Report Geography
- Mapping Status
- Mapping Confidence
- Location Type
- Location
- Value
- Local Goal
- Derived Goal Status
- Status Basis
- Source Variance
- Source Variance Color
- YTD
- Data As Of

A minimally defensible evidence statement identifies the metric, hierarchy level, cohort or location, reporting date, value, and denominator where applicable.

Good:

> Among 203 FRL Team Member Engagement records reported Mar 2026, 125 of 203 eligible records met their local goal (62%).

Bad:

> Engagement is doing well.

## 4. Hierarchy rules

`Location Type` is an analytical level, not a cosmetic label. Current types include Corporate, Division, Region, Market, Facility, Campus, Hospital, FRL, Costing Company, and Cost Center.

Required rules:

- `Source Division` is the unchanged workbook value. Never rewrite or silently relabel it.
- `Matched Division` is a derived cross-workbook grouping. It may be used by a labeled matched-division filter but must not be presented as a source field.
- `Report Geography` is optional secondary context, not a replacement hierarchy.
- Direct PHD and Corporate parent assignments take precedence over geographic location-name matches.
- Use `Source Division`, `Matched Division`, `Mapping Status`, and `Mapping Evidence` when auditing a match.
- Compare records only within one Location Type.
- Never average or count Corporate, Division, Region, and local records together as if they were independent observations.
- Never relabel Cost Center as Facility, Campus as Hospital, or FRL as Facility.
- Never manufacture a Division result by averaging its Facility, FRL, Cost Center, or other child rows.
- Use direct `Location Type = Division` rows for executive division comparisons.
- Keep unresolved division mappings visible in audit views but out of executive ranking controls.
- When a page permits `All types`, treat it as a raw audit view. Do not calculate or narrate a combined performance rate.
- State the selected Location Type and record count next to every peer statistic.

The preferred first comparison level is defined in `assets/vision2030.js` as `preferredType`. It is a usability default, not permission to discard other levels.

## 5. Goal and status rules

The workbook's source variance fields and the site's derived goal status answer different questions. Preserve both.

- `Derived Goal Status` is `met`, `missed`, or `unavailable`.
- Goal attainment denominator = `met + missed` only.
- Unavailable rows must remain visible but must not enter the attainment denominator.
- Use the local goal on the same row. Do not substitute the enterprise goal for a local record.
- Respect goal direction. Some metrics are better when lower; do not assume higher is better.
- Use financial source variance only where `site_builder.py` explicitly permits it.
- Forecast and Hire below enterprise remains unavailable because the workbook repeats an enterprise goal below enterprise level.
- Internal Leader Fill Rate, Mortality, Length of Stay O/E, Community Impact, and Mission Integration remain unavailable unless a comparable numeric goal is supplied in a future workbook.
- Enterprise clinical aggregate shares remain status-unavailable unless an aggregate threshold is supplied.
- Gray or unavailable is not neutral performance. It means the comparison cannot be defended.
- Never invent yellow status or an arbitrary red/green threshold.

Always show an attainment result as both numerator and denominator. A percentage without `N` is insufficient.

## 6. Time rules

- `Data As Of` belongs to each metric record. Do not replace mixed dates with one dashboard date.
- A Current-versus-YTD pair is not a time series and must not be called a trend.
- Words such as “improved,” “declined,” “accelerated,” or “continued” require at least two comparable dated observations; a trend claim should normally require three or more consistent time points.
- Do not compare two periods if the hierarchy, scope definition, unit, or metric definition changed.
- When dates are mixed, show the range or filter to a single reporting label.
- `Coming Soon` and `N/A` are not zero.

## 7. Relationship and causal language

- Pair metrics only on the exact normalized scope identifier and the same Location Type.
- Apply the selected Division and date filters consistently to both metrics.
- Require at least five matched, varying numeric pairs before calculating Pearson correlation.
- Always report correlation as `r` and `N`.
- Correlation is descriptive and must never be presented as a driver, cause, impact, or intervention result.
- Do not generate regression, forecast, or causal claims without an explicitly approved method and supporting fields.

Allowed:

> Team Member Engagement and Leader Effectiveness have a strong positive descriptive relationship across 203 matched FRL records (r = 0.71); this identifies a question for investigation, not a causal driver.

Not allowed:

> Improving leader effectiveness will increase engagement.

## 8. Dynamic insight generation procedure

For every proposed narrative insight:

1. Rebuild from the latest workbook and confirm the audit passes.
2. Choose one page and one decision question.
3. Define the exact cohort: Business Area, Metric, Location Type, Division, and Data As Of.
4. Remove nonnumeric rows only when the statistic requires numeric values; continue reporting how many were unavailable.
5. Compute the statistic from the normalized rows. Do not copy a previously rendered number.
6. Check goal direction and the row-level status basis.
7. Calculate and state the denominator.
8. Attach the relevant caveat: mixed date, unavailable goal, small sample, directionality, or noncausal relationship.
9. Phrase the observation neutrally.
10. Recalculate after every filter change and every new workbook run.

Recommended structured object for machine-generated narrative:

```json
{
  "id": "stable-machine-readable-id",
  "page": "briefing|insights|data-explorer",
  "headline": "Short factual finding",
  "statement": "One or two evidence-backed sentences",
  "evidence": {
    "businessArea": "Team",
    "metric": "Team Member Engagement",
    "locationType": "FRL",
    "division": "All",
    "dataAsOf": "Mar 2026",
    "records": 203,
    "eligible": 203,
    "numerator": 125,
    "statistic": 62,
    "unit": "percent"
  },
  "caveat": "Attainment uses local goals and excludes status-unavailable rows.",
  "sourceWorkbook": "relative path from validation_summary.json"
}
```

Every number in `headline` or `statement` must appear in `evidence` or be directly recomputable from it.

## 9. Visualization selection rules

Add a chart only if it answers a question more clearly than a KPI or table.

### Appropriate charts

- Horizontal bar: ranked peers, division attainment, record counts, reporting-date counts, or normalized goal gaps.
- Stacked bar: met/missed/unavailable composition where the denominator is explicit.
- Histogram: numeric distribution with at least five records; include range and middle-50% values.
- Donut: only for the three goal-status categories. Show the eligible attainment rate and counts alongside it.
- Heatmap: direct Division-by-metric status only; missing records remain missing.
- Scatterplot: matched scopes only, at least five varying pairs, with `r`, `N`, and a noncausal warning.
- Table: exact values, local goals, source variance, status basis, dates, and audit investigation.

### Inappropriate charts

- Pie or donut with many locations or metrics.
- Ranking raw values when metric direction is unknown without stating that highest is not necessarily best.
- Line chart from Current and YTD alone.
- Combined chart across mixed Location Types.
- Performance chart using record count as though it were workforce, patient, revenue, or facility volume.
- Geographic map without validated coordinates or geographic keys.

### Map gate

The current workbook does not provide validated latitude/longitude, state/county FIPS, or an approved facility-to-geography reference table. Do not add a geographic map from names alone. A map becomes permissible only when a governed mapping table is supplied and unmatched/ambiguous locations are explicitly reported.

## 10. Page contracts

### Briefing

- System or direct Division scope only.
- Focus on attainment, gaps, strengths, freshness, and missing comparability.
- Keep the number of narrative callouts small, neutral, and evidence-backed.
- The executive readout must select its Attention, Protect, and Data Confidence evidence deterministically from the current scope before any LLM writes prose.
- Every readout number must retain value, local goal, reporting date, status basis, and scope context where applicable.
- Division composition must show met, missed, and unavailable direct Division records; the eligible attainment denominator remains met plus missed.
- The detailed scorecard remains grouped by aspiration, but every metric keeps its own reporting date and unavailable reason.
- No lower-level rollups masquerading as division performance.

### Insights

- Metric-first and one Location Type at a time.
- Always show record count, numeric count, eligible denominator, Division selection, and reporting selection.
- Use distribution, local-goal gap, division comparison, Current-versus-YTD, and matched relationship views only when their required fields exist.
- Do not show empty decorative charts; show a clear insufficiency message.

### Data Explorer

- Preserve all source-aligned rows and filters.
- Preserve the Division Basis control. `Source division` must use the workbook value verbatim; `Matched division` must use only the attached sidecar audit.
- `All types` is allowed for auditing and export.
- Suppress combined attainment when multiple metrics or hierarchy levels would make it misleading.
- Record-composition charts describe available rows, not expected coverage or organizational size.
- CSV export must include all filtered rows even when the browser table is capped.

## 11. Language rules

Prefer:

- “reported value”
- “met the local goal”
- “eligible records”
- “available rows”
- “descriptive relationship”
- “reporting selection”
- “status unavailable”

Avoid unless proven:

- “performance improved”
- “drives” or “causes”
- “significant” unless a statistical test was specified and performed
- “coverage” without a known expected denominator
- “facility” as a generic term for every location
- “underperforming” when no defensible goal exists
- “latest” without resolving the latest source workbook at runtime

## 12. Pre-publication checklist

Before saving an insight or chart:

- [ ] Latest workbook was resolved at runtime.
- [ ] Validation audit passed.
- [ ] Mapping audit contains and attaches exactly one row for every detail record.
- [ ] Source Division is unchanged and Matched Division is clearly labeled as derived.
- [ ] Matched Division is not replaced by Report Geography in calculations or labels.
- [ ] Metric name and unit match the normalized model.
- [ ] Exactly one analytical Location Type is used.
- [ ] Division and date filters are applied consistently.
- [ ] Numerator, denominator, and unavailable count are correct.
- [ ] Goal direction and local goal are respected.
- [ ] Mixed hierarchy levels are not aggregated.
- [ ] YTD is not described as a trend.
- [ ] Correlation is matched-scope, has sufficient `N`, and is noncausal.
- [ ] Record counts are not mislabeled as population or completeness.
- [ ] No unsupported map or geographic inference is present.
- [ ] Empty or insufficient data produces an explicit message, not a fabricated visual.
- [ ] The page still passes `node --check assets/vision2030.js`.
- [ ] The site rebuild completes with `auditPass: true`.

## 13. Implementation locations

- Workbook parsing and normalization: `site_builder.py`
- Immutable source-side matching audit: `reconciliation/build_source_mapping_audit.py`
- Historical corrected-workbook comparison only: `reconciliation/build_corrected_workbook.py`
- Division normalization used by future extractions: `vision2030_extraction.py`
- Launcher and localhost server: `run_vision2030.py`
- Dynamic charts, filters, and page insights: `assets/vision2030.js`
- Shared visual language: `assets/vision2030.css`
- Audited row export: `generated/normalized_record_audit.csv`
- Build verification: `generated/validation_summary.json`

Keep reusable calculations in JavaScript functions or the Python normalization layer. Do not paste workbook-specific numbers into HTML templates. The generated pages must remain dynamic when a new workbook becomes the latest run.
