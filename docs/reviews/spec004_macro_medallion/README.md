# Spec 004 review: existing MacroMedallion FX coverage

Reviewed 2026-10-30, America/New_York. Decision: retain MacroMedallion as the
owner of ECB ingestion. The nine requested currencies already exist; prioritize
upstream contract improvements and an FX Gold product before considering another
connector. This review implements no acquisition, warehouse migration or FX runtime.

The baseline is [Spec 004](../../../specs/spec004/README.md). Findings below are
contract gaps against that specification. MacroMedallion's existing provider-vintage
views have a different temporal contract from Spec 004's captured-as-of requirement.

## Verified coverage and limits

The read-only, repeatable-read warehouse snapshot was taken at
**2026-10-30 22:17:58 America/New_York** (2026-10-31 02:17:58 UTC).
It contains 17 daily ECB EUR-based FX series. All nine scoped quote currencies
(USD, GBP, JPY, CHF, CAD, AUD, NZD, NOK, SEK) have the same profile:

| Measure | Per scoped currency |
| --- | ---: |
| Stored Silver rows | 7,278 |
| Distinct observation dates | 7,188 |
| First / last observation date | 1999-01-04 / 2026-10-30 |
| Rows without a provider vintage date | 129 |
| Dates with both blank and dated vintage keys | 90 |
| Those overlapping dates with different raw values | 0 |
| Null-valued rows / latest dates | 62 / 62 |
| Rows without raw numeric text | 0 |
| Nonpositive non-null latest rates | 0 |

The 90 extra rows are overlapping keys with identical raw values, not evidence
of 90 genuine revisions. Date counts include missing observations; they do not
establish uninterrupted valid-rate coverage. The 62 nulls have no retained
observation-status column explaining their meaning. Their cause was not inferred.
The earlier lookup ended on October 26; the later snapshot contains October 30.
This review issued no provider data request or warehouse write.

## Findings, in priority order

### P1 — High: captured revisions, as-of selection and replay need one temporal contract

**Observed correction history is overwritten.** Silver merges on
`(source, series_id, observation_date, realtime_start)` and updates matching rows
when the content hash changes. With a blank or unchanged provider vintage key,
synthetic A → B → A captures retained **one** Silver row. Identical reruns correctly
preserved the retained capture time, which is useful existing behavior.

**Intraday provider events collapse.** `_valid_time_to_date` truncates provider
`VALID_FROM` and `VALID_TO` timestamps to dates. Two different same-day update
times therefore produced the same merge key and retained one row in the SQLite
probe. Provider update evidence must remain distinct from publication evidence;
unknown observation publication timestamps should stay null.

**Captured-as-of filtering is absent.** `point_in_time_snapshot` and
`_select_vintage` select provider vintage dates without checking `ingested_at`.
The snapshot helper also accepts an observation after the cutoff when its vintage
is blank. A synthetic row captured in 2026 was returned for a 2024 cutoff.
In the live USD data, **7,190** non-null rows satisfy a provider-date eligibility
predicate at 2026-08-01, while **zero** have retained capture times by that cutoff.
This count measures temporal-contract exposure; it is not a claim that all 7,190
provider vintages are invalid. The warehouse's `gold.fred_point_in_time` is a
view of Silver history, not a cutoff-filtered answer by itself.

**Replay changes capture time.** `replay_from_bronze` does not pass the archived
`ingested_at` to `build_silver_rows`; the normalizer uses the replay clock.
A synthetic old Bronze record retained its numeric text but acquired a new Silver
capture time in an empty temporary destination. Capture-based as-of results would
therefore change after recovery.

**Withdrawals are discarded.** An `ACTION=Delete` row is skipped by normalization.
The synthetic previous value remained present after processing a delete-only
payload. No affected live withdrawal was established in this review.

Evidence in the sibling source tree:

- `src/fred_pipeline/io/local_store.py:2040` and `:980`: merge key and update.
- `src/fred_pipeline/io/postgres_store.py:60`, `:350`, `:520`: matching PostgreSQL behavior.
- `src/fred_pipeline/sources/ecb.py:121`, `:155`: timestamp truncation and delete handling.
- `src/fred_pipeline/writer/features.py:335`, `:500`: provider-date selection.
- `src/fred_pipeline/writer/gold.py:231`: SQL provider-date selection, no capture guard.
- `src/fred_pipeline/replay.py:57`: archived capture time omitted.

Remediation: add append-only observed versions with deterministic capture ordering,
retain full provider timestamps separately, represent withdrawals explicitly, and
gate the captured-as-of mode by actual capture plus any verified publication time.
Replay must preserve archived capture/version lineage. Keep separately named
provider-vintage views for their documented purpose. Require A → B → A, same-day
corrections, blank-vintage cutoffs, future observations, withdrawals and replay
as-of equivalence as acceptance tests. Reproduce merge behavior against a dedicated
PostgreSQL test target before migration; no live PostgreSQL merge was attempted.

### P2 — High: exact values and semantic metadata need preservation through promotion

The ECB normalizer calls `parse_value`, which returns Python `float`. SQLite uses
`REAL`; live Silver and Gold use `double precision`. In the precision probe,
synthetic source text `1.123456789012345678900` became `1.1234567890123457` as the
numeric value. The original text remained intact. This proves the implementation
cannot guarantee Spec 004's accepted-value round trip; it does not demonstrate a
material pricing error in the current, shorter ECB quotes.

`OBS_STATUS`, unit multipliers and validated currency dimensions do not appear in
the canonical Silver row or hash. A synthetic status-only change left the hash
unchanged, and a JPY-keyed payload was accepted under the requested USD series ID
by the normalizer. The request uses `detail=dataonly`; metadata must be acquired
and verified separately if that request shape remains. No metadata check elsewhere
in the reviewed ECB ingestion path establishes this contract.

Evidence: `src/fred_pipeline/data/transform.py:30`,
`src/fred_pipeline/sources/ecb.py:155` and `:260`, live schema in
[warehouse_results.json](warehouse_results.json), and
[synthetic_results.json](synthetic_results.json).

Remediation: design an additive FX-specific exact-value representation, preserving
`raw_value` formatting and parsing directly to Decimal. Validate SQL/Parquet
precision and reject unsupported values before promotion. Retain and hash verified
scale, orientation, status and record state; block contradictory dimensions.
Keep native-rate storage independent of the versioned rounding policy for derived
rates. Prove exact SQLite/PostgreSQL/Parquet/replay parity before switching readers.
Existing raw text and Bronze retention provide a recovery path to investigate;
this review does not guarantee reconstruction of every overwritten version.

### P3 — Medium: publish an FX-specific Gold product from existing source data

No FX inverse/cross product is configured in the reviewed source or present in
the inspected Gold inventory. The generic cross-feature table contains only
`real_yield_10y`, `debt_to_gdp` and `macro_activity_index`. Existing native rates
are available through the generic latest-observation interface and FX catalog.

Useful functionality already exists: a daily ratio of same-date synthetic legs
correctly produced **120 JPY per USD** from 150 JPY/EUR and 1.25 USD/EUR. Changing
one leg to a different day produced no cross. The daily ratio helper does not
forward-fill across mismatched dates. Coarser frequency alignment is period-based
and needs separate economic rules.

The generic output contains `feature_name`, `op`, `observation_date`, `value`;
it lacks the requested explicit base/quote orientation, input version IDs,
feature-policy version, availability and null-quality reasons. Inputs and
arithmetic use floats. A separate macro daily feature matrix intentionally
forward-fills; use source-date rate rows for canonical FX calculations.

Evidence: `config/cross_series.yml`,
`src/fred_pipeline/writer/features.py:257`, `:266`, `:383`,
`src/fred_pipeline/data/transform.py:182` and the live feature inventory.

Remediation: build a source-owned FX Gold module in MacroMedallion using the
existing ECB series. Specify native/inverse/cross orientations, an explicit pair
list, exact-date joins, input lineage, null/withdrawal behavior and derived precision.
Add previous-reference-date changes with elapsed days. Gate its captured-as-of
claims on P1 and its exact numeric claims on P2. No new historical ECB acquisition
is required merely to establish dataset coverage.

## Spec 004 disposition

| Contract area | Review result |
| --- | --- |
| Nine requested native ECB series and history | Already present; no duplicate ingester justified |
| Source numeric text | Retained in inspected Silver rows and synthetic replay |
| Exact native numeric storage/export | Gap confirmed; Spark/Parquet runtime not executed |
| Currency/scale/status validation and semantic comparison | Gap in reviewed normalizer and schema |
| Append-only observed corrections and reversion | Gap reproduced for unchanged provider key |
| Captured-as-of cutoff and future-date exclusion | Gap reproduced in pure helper |
| Intraday provider timing and withdrawals | Gap reproduced with synthetic payloads |
| Replay preserves original capture time | Gap reproduced with temporary SQLite |
| Same-date daily ratio, no mismatched-day filling | Existing helper passes synthetic check |
| FX-specific native/inverse/cross output with lineage | Product absent from reviewed config/live inventory |
| Current local coverage | Through 2026-10-30 in this snapshot |
| Production schedules, alerts, retention and licensing | Full operational audit outside this review |

The current local branch `feature/spec004-ecb-fx` remains a reserved review/follow-up
branch. No FX implementation has been added to MarketMedallion. Existing AAII
changes remain in their working tree. The review does not change the CFTC backlog
or authorize upstream fixes, deployments or schedule changes.

## Verification and evidence

- **48 existing offline tests passed**: `test_ecb_client.py`, `test_transform.py`,
  `test_features.py`. These characterize the current contract and do not establish
  compliance with the stricter Spec 004 criteria.
- Eight synthetic probe groups reproduce the gaps and verify useful existing
  behavior. They call original code with synthetic inputs and disposable SQLite
  files; no sibling runtime config, secrets or live database is loaded.
- [warehouse_checks.sql](warehouse_checks.sql) ran under explicit read-only,
  repeatable-read transaction settings with a 20-second statement timeout.
  [warehouse_results.json](warehouse_results.json) contains aggregate evidence.
- [source_checksums.json](source_checksums.json) records the reviewed source
  revision and hashes. The review does not copy sibling implementation files,
  databases, runtime configuration or Git history.
- Spark/Delta execution, PostgreSQL write-path parity and a fresh provider API
  extraction were not exercised. PostgreSQL update behavior is source-inspected;
  runtime correction/replay probes use SQLite.

Reproduce with the sibling checkout's Python, passing its path explicitly:

```bash
MACRO_CHECKOUT="/path/to/fred-bronze-to-gold-pipeline"
"$MACRO_CHECKOUT/.venv/bin/python" -B \
  docs/reviews/spec004_macro_medallion/checks.py --checkout "$MACRO_CHECKOUT"
# Run these tests from that checkout with bytecode/cache writes disabled:
# .venv/bin/python -B -m pytest tests/test_ecb_client.py tests/test_transform.py \
#   tests/test_features.py -p no:cacheprovider --basetemp /tmp/spec004-macro-review-pytest
```

## Official provider context checked

The [ECB API documentation](https://data.ecb.europa.eu/help/api/data) documents
previous-version retrieval with `includeHistory`, changes including deletions
with `updatedAfter`, and exclusion of attributes with `detail=dataonly`.
Direct portal requests returned 503 during this review; the search-indexed
primary documentation was accessible. The selected dataset's complete historical
publication-vintage semantics were not newly verified.

The [official reference-rate page](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html)
confirms EUR as base and describes informational reference rates, normally updated
around 16:00 CET on working days except TARGET closures. A timetable does not
establish an observation-specific publication timestamp. No stored quotes were
reconciled numerically with that page in this review.
