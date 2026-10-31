# Spec 004 — Daily official FX reference rates

Status: **initial scope accepted 2026-10-30; connector not implemented**. Created 2026-10-30.
Capability ID: `fx-reference-rates`. Proposed first dataset: `ecb-fx-reference`.
User-confirmed scope: **daily official reference rates**.

## Objective and decisions

Give quant researchers reproducible official currency reference-rate history,
explicit quote orientation and research conversions, with immutable raw captures
and observed revisions. Success is a bounded offline-to-live ECB vertical slice
with SQLite/PostgreSQL parity, typed Parquet, availability-aware Gold and replay.
Ingestion alone does not establish predictive value.

Use the ECB's daily euro reference rates first. Start with EUR as base and
USD, GBP, JPY, CHF, CAD, AUD, NZD, NOK and SEK as quotes, subject to metadata
verification. Keep other currencies opt-in. The initial offline fixture covers
USD and JPY; live verification should use at most two series over 31 calendar
days. The user-confirmed historical backfill start is **1999-01-01**. For a
series that begins later, retain its actual first available observation; do not
fabricate earlier rates. No claim of uniform history or a complete G10 trading feed.

This is independent of [Spec 005](../spec005/README.md) and does not replace
[AAII completion](../spec003/README.md) or the remaining Spec 001 backlog.
Use the existing [architecture](../../docs/deployment/architecture.md): a pure
Python 3.12 core, strict source manifests, Bronze → Silver → Gold, transactional
warehouse promotion, committed Parquet pointer, CLI and Dagster wrappers.
The current manifest and warehouse implementations are AAII-specific; new
source contracts and tables must be implemented explicitly, preserving AAII.

## Official source review

Documentation reviewed 2026-10-30; no live FX response or account was tested.
The following provider statements support source selection, not a claim that a
new connector or fixture already works.

| Candidate | Evidence and decision |
| --- | --- |
| ECB, first slice | [Reference-rate page](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html) documents EUR as base, working-day releases around 16:00 CET except TARGET closures, and an approximately 14:10 CET concertation. These are informational reference rates. Retain the documented convention; never infer an actual publication timestamp from the timetable. |
| ECB access | [API data documentation](https://data.ecb.europa.eu/help/api/data) and [examples](https://data.ecb.europa.eu/help/api/data-examples) document EXR series keys, bounded periods, CSV output, conditional retrieval, changes and history options. Capture the actual CSV schema and SDMX metadata before coding its parser. |
| ECB use conditions | [Copyright conditions](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html) require accurate source attribution and identification of modifications, with additional conditions for sold documents. Record the reviewed terms and dataset-specific exceptions. No numeric request-rate entitlement was verified. |
| Bank of Canada, later optional | [Valet guide](https://www.bankofcanada.ca/valet-api-how-to/) documents a free API without a key, daily/monthly/annual rates and caching/backoff guidance. It would be a separately named source with its own CAD conventions and terms, never an invisible ECB fallback. |
| BIS, later optional | [Bilateral rates](https://data.bis.org/topics/XRU) offer broader USD-based histories assembled from multiple sources; [BIS FAQ](https://data.bis.org/faq) describes weekly release/update timing. A daily observation frequency does not establish daily availability. Defer until incremental coverage and provenance justify it. |

Proposed verified-documentation request shape, **not executed in this work**:

```text
GET https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A
    ?startPeriod=2026-10-01&endPeriod=2026-10-30&format=csvdata
```

The key order is frequency, currency, denominator currency, rate type and
suffix. Here `D.USD.EUR.SP00.A` means a daily USD-per-EUR series. Resolve the
flow structure, code lists, unit multipliers, observation status and series
attributes before implementation; do not guess CSV column order or treat the
series suffix as a unit scale. Store the metadata response and content hash.
ECB documentation exposes `updatedAfter` and `includeHistory`, but neither
establishes a complete publication-vintage service for this selected dataset.

## Bounded scope and exclusions

First delivery: authorized local provider-shaped CSV → versioned Silver →
native/inverse/cross reference-rate Gold → replay → SQLite/PostgreSQL/Parquet;
then injected-transport ECB extraction and a stopped Dagster definition.
Schedules remain stopped until separate operational readiness is verified.

Exclude intraday/tick prices, OHLC, bid/ask spreads, trade execution, forwards,
carry, total returns, implied volatility and vendor failover. ECB references
cannot substitute for executable prices or a market close. No FRED runtime,
database, secrets or deployment identifiers may be imported from a sibling repo.

## Proposed manifest and source boundary

Use `manifests/ecb-fx-reference.yml` only when the new manifest type is built.
The following is a **proposed contract fragment**, not valid input to today's
AAII-only validator:

```yaml
contract_version: fx-reference-v1
source: ecb
dataset: ecb-fx-reference
format: sdmx-csv
flow: EXR
series_keys:
  - D.USD.EUR.SP00.A
  - D.JPY.EUR.SP00.A
base_currency: EUR
frequency: D
rate_type: reference
quote_convention: quote_units_per_one_base
unit_multiplier_policy: from_verified_metadata
access:
  method: official-api
  source_url: https://data-api.ecb.europa.eu/service/
  terms_url: https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html
  automation: explicit-bounded-run
```

Reject unknown fields, duplicate keys, unverified series, mixed frequencies,
contradictory currency dimensions, reversed bounds and unsupported contracts
before network or warehouse writes. Runtime selection bounds, request limits and
credential-free transport settings belong outside the semantic manifest.

## Bronze, Silver and timing contracts

Bronze retains exact response bytes, manifest snapshot, metadata/code-list
artifacts, SHA-256, source/series identifiers, parser version, run ID, UTC
retrieval time, requested date range and HTTP status/allowlisted headers.
Preserve failed schema/DQ payloads and request/chunk completeness evidence.
HTTP Last-Modified or a response-level update time is not automatically an
observation publication time.

Silver logical key:

```text
(source, dataset, series_key, rate_date)
```

| Field | Contract |
| --- | --- |
| `series_key`, `base_currency`, `quote_currency` | Provider key plus validated explicit orientation; identifiers stay strings. |
| `rate_date` | Provider's daily observation label, without shifting to retrieval/publication date. |
| `raw_value`, `unit_multiplier`, `rate` | Preserve the exact source numeric text, including supplied decimal places, and scale metadata. Parse directly to Decimal without binary floating-point conversion. Normalize units exactly using verified metadata; never round or truncate source values. Missing/suppressed values have null rate and an explicit status. |
| `observation_status`, `record_state` | Preserve provider status, including any verified withdrawal; never interpret an absent row as deletion. |
| `provider_published_at` | Nullable, populated only from verified observation-specific evidence. |
| `provider_updated_at` | Nullable with its scope and precision; separate from publication time. |
| `retrieved_at`, `first_seen_at` | Actual UTC capture time and first capture of this version; a backfill does not backdate either field. |
| `version_id`, `content_hash`, `raw_run_id` | Immutable version and raw/metadata lineage; hash semantic content, not volatile HTTP metadata. |

### Numeric precision — user decision, 2026-10-30

Preserve source values losslessly throughout ingestion, persistence, export and
replay. Bronze preserves original bytes; Silver retains the source numeric text
and an exact decimal value. Unit normalization must not discard significant
digits. SQL and Parquet representations must round-trip every accepted source
value exactly; do not impose a fixed number of decimal places that rounds or
truncates provider precision. Preserve source formatting such as trailing zeros
in `raw_value`, even where a numeric representation formats it differently.
If a value exceeds the configured storage precision or scale, preserve Bronze
and reject promotion with an explicit error rather than silently changing it.

Inverse/cross rates and changes can have nonterminating decimal expansions.
Their calculation precision and rounding must be documented separately under a
versioned derived-feature policy; that policy must never modify source values.
The implementing agent selects suitable storage types and derived precision,
subject to these lossless source-value requirements.

Unchanged data creates no new Silver version. A → B → A creates three observed
versions. Currency, scale, status and value changes participate in comparison.
Reject contradictory duplicates within one extraction. Deterministic capture
ordering must resolve timestamp ties without inventing provider timing. New
parser/contract versions require an explicit migration/replay policy.

Observed-as-of selects only versions captured by the cutoff and, where a verified
publication time exists, published by it; then derives features. It never reads
today's latest rates before calculating an older as-of result. Availability of
a cross is the latest availability of its inputs. A future-dated observation is
quarantined; a future publication time cannot become an available observation.

## Gold definitions

Publish source-specific `fx_reference_latest` and observed-as-of views with
input version IDs, feature version, date, orientation and quality flags.

Let `r_X` be X per EUR, and `r_Y` be Y per EUR on the same reference date:

- Native EUR/X: `r_X`; inverse X/EUR: `1 / r_X`.
- Derived X/Y: `r_Y / r_X`, expressed as Y per X, explicitly labelled derived.
  Example with invented rates: 1 EUR = 1.25 USD and 1 EUR = 150 JPY implies
  1 USD = 120 JPY (the USD/JPY pair). EUR's synthetic identity leg is 1 and is flagged.
- Change: `current / previous - 1` for an identical pair and convention, with
  predecessor date and elapsed calendar days. It is a reference-rate change,
  not a funded trading return.

Align both cross legs by exact rate date and compatible reference methodology;
never combine different dates/providers to fill a missing leg. No forward-fill
in canonical Silver/Gold. Null/status legs yield null features with reasons.
Decimal arithmetic and a versioned precision/rounding policy govern derived
calculations. Native source rates remain exact; Parquet/SQL storage follows the
lossless source-value contract above.
Longer-horizon changes/rolling volatility are later extensions requiring exact
window, missing-data and annualization contracts.

## Extraction, DQ and operations

Use bounded date chunks (default maximum 31 calendar days per live request),
explicit series lists, timeouts, response-size limits and conservative sequential
requests. Proposed ceiling: one request/second, at most three attempts per
request, exponential backoff with jitter and Retry-After support. This is an
application limit, not a verified provider quota. Do not retry permanent schema
or permission errors; treat a 404 as no-data only if that meaning is verified.

Start incremental runs with a configurable 10-calendar-day overlap. Schedule
periodic bounded reconciliation of older intervals to detect older corrections;
the overlap alone cannot guarantee discovery of all revisions. Defer deltas
until additions/revisions/deletions and cursor semantics have fixtures. Store
extraction checkpoints per dataset/series and requested coverage. Advance only
after complete validated extraction and successful warehouse promotion; report
Parquet publication state separately and use existing recovery semantics.

Blocking checks: dimension/metadata mismatch, malformed date, nonpositive or
nonfinite rate, unknown scale, conflicting duplicate, truncated body, missing
required columns or unexpected HTML. Metadata-supported missing observations
are explicit nulls, never zero. Empty results distinguish legitimate closures,
unsupported/discontinued series and upstream errors. Maintain series validity
intervals; stopped rates must not trigger endless missing-day backfills.

Monitor expected releases using the verified TARGET calendar, publication
convention, configurable grace and last successful capture. Do not equate every
weekday with a release day or convert a fixed CET string into an assumed DST
rule. Before scheduling, verify its operational timezone, calendar, worker
storage, lock topology, credentials if any, recovery and alert destination.

## Proposed files, interfaces and style

| Location | Responsibility when implemented |
| --- | --- |
| `src/market_data_pipeline/fx_reference_rates/source.py` | Pipeline-owned injected HTTP/clock boundary and bounded ECB extraction. |
| `src/market_data_pipeline/fx_reference_rates/manifest.py` | Typed FX manifest; preserve AAII validation in its own package. |
| `src/market_data_pipeline/fx_reference_rates/data/` | Immutable normalized records, DQ and pure Decimal/native/inverse/cross transforms. |
| `src/market_data_pipeline/fx_reference_rates/` | Pipeline execution, configuration, CLI, replay and Dagster definitions. |
| `src/market_data_pipeline/fx_reference_rates/io/` | FX-owned archive, tables, warehouse adapters and typed snapshots. |
| `tests/fixtures/ecb/`, `tests/test_fx_*.py` | Synthetic provider-shaped files, provenance README, transport and end-to-end cases. |
| `resources/`, `docs/deployment/` | Stopped Dagster config and tested FX runbook. |

Illustrative pure-core style, **not implemented**:

```python
from decimal import Decimal


def cross_rate(quote_per_eur: Decimal, base_per_eur: Decimal) -> Decimal:
    if not quote_per_eur.is_finite() or not base_per_eur.is_finite():
        raise ValueError("reference rates must be finite")
    if quote_per_eur <= 0 or base_per_eur <= 0:
        raise ValueError("reference rates must be positive")
    return quote_per_eur / base_per_eur
```

Use frozen records, explicit names/units, small pure functions and parameterized
SQL. Keep optional Dagster/PostgreSQL imports at integration boundaries. Use a
separate root, e.g. `data/fx-reference/`, and source-owned tables/schema. Never
point the first FX migration or test at the live AAII warehouse. Reuse existing
archive/transaction/publication behavior only after compatibility is proven.

## Proposed commands and verification

These FX commands are **planned, not executable today**. Follow the
[pipeline package layout](../../docs/development/pipeline_layout.md): FX owns
`fx_reference_rates/`, including its manifest, CLI, persistence and orchestration.
Only provider-independent helpers belong in `shared/`; never import AAII
internals. The pipeline module provides its source-scoped entrypoint; any later
root dispatcher must preserve legacy AAII commands and defaults:

```bash
.venv/bin/python -m market_data_pipeline.fx_reference_rates validate --manifest manifests/ecb-fx-reference.yml
.venv/bin/python -m market_data_pipeline.fx_reference_rates run --manifest manifests/ecb-fx-reference.yml \
  --input tests/fixtures/ecb/reference.csv --root data/fx-demo
.venv/bin/python -m market_data_pipeline.fx_reference_rates run --manifest manifests/ecb-fx-reference.yml \
  --live --start 2026-10-01 --end 2026-10-30 --root data/fx-smoke
.venv/bin/python -m market_data_pipeline.fx_reference_rates gold --root data/fx-demo \
  --as-of 2026-10-30T20:00:00Z
.venv/bin/python -m market_data_pipeline.fx_reference_rates replay --source-root data/fx-demo \
  --root data/fx-replayed
```

Existing verification commands to run during implementation:

```bash
python3 scripts/verify_agent_skills.py
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m build --no-isolation
```

Use provider-shaped offline fixtures before semantic implementation, injected
transport/clock and pytest. A fixture README identifies invented versus captured
values, exact shape source and redistribution permission. No CI live dependency.
Use a dedicated empty PostgreSQL test database for backend parity.

## Build sequence and acceptance criteria

Suggested slices for a later source-scoped plan: metadata/fixtures → local
normalization and DQ → SQLite/Silver/Gold/replay → PostgreSQL/Parquet → bounded
HTTP → Dagster/runbook. Do not overwrite the active AAII task files.

- [ ] Metadata, CSV columns, scale/status meanings, calendar and usage review
  are captured with evidence before a parser is implemented.
- [ ] Invalid manifests fail before I/O; existing AAII manifests and archives
  preserve their behavior without reinterpretation.
- [ ] A two-currency fixture writes exact Bronze bytes, typed Silver, native,
  inverse and cross Gold, audit and one committed Parquet snapshot.
- [ ] Source values with varying decimal places, trailing zeros and many
  significant digits round-trip exactly through parsing, SQLite/PostgreSQL,
  Parquet and replay, retaining their original numeric text. No binary-float
  conversion, rounding or truncation changes an accepted source value; storage
  overflow/scale mismatch preserves Bronze and blocks promotion explicitly.
- [ ] Nonterminating inverse/cross calculations follow the documented derived
  precision/rounding policy without modifying native source rates.
- [ ] Orientation examples, nulls, precision, holiday gaps and mismatched dates
  pass tests; no hidden filling or cross-provider substitution occurs.
- [ ] Identical reruns create zero new versions; correction and reversion retain
  all observed versions; past as-of outputs ignore later captures.
- [ ] Schema drift, invalid scale, duplicates, truncation and 429/retry exhaustion
  preserve evidence and cannot advance a success checkpoint or publish bad data.
- [ ] Partial extraction leaves the prior committed publication intact; a
  warehouse-success/publication-failure outcome is visible and recoverable.
- [ ] Replay in an empty destination reproduces values, statuses, original
  first-seen/version lineage and as-of results without network access.
- [ ] SQLite/PostgreSQL and Parquet agree on decimal precision, null/status
  semantics and version selection; concurrent AAII regression checks pass.
- [ ] Offline Dagster materialization exercises the same core and keeps its
  schedule stopped. A separately requested bounded live smoke run validates
  actual provider behavior, attribution and comparison to the official page.

## Boundaries and remaining decisions

Always preserve payloads, dimension/status metadata, quote orientation, observed
availability, version history, deterministic replay and source isolation.
Review before expanding: currencies/history, a different provider, new dependency,
shared schema migration, recurring acquisition or cloud publication. Never
fabricate quotes on closed days, claim an executable market feed or reconstruct
historical publication vintages from a new full-history download.

### Initial scope acceptance — 2026-10-30

The user confirmed that the proposed scope covers the initial need:

- ECB first, with EUR as base and USD, GBP, JPY, CHF, CAD, AUD, NZD, NOK and
  SEK as the initial quote-currency universe.
- Historical backfill start **1999-01-01**, explicitly confirmed by the user
  on 2026-10-30, following bounded sample verification. Later-starting series
  retain their actual coverage without filling earlier history.
- Native, inverse and same-date derived reference rates with observed revisions
  and availability-aware features, as specified above.

The user additionally confirmed that numeric precision must preserve source
values. The implementing agent should choose lossless storage representations,
document precision/rounding for derived features only, and select/document the
initial derived cross-pair list.
Verify the provider schema, metadata, status meanings and access conditions
before implementing the parser. Coordinate shared manifest/CLI/warehouse changes
with the active AAII work. These are engineering responsibilities rather than
unresolved initial research requirements.

Before scheduling, settle the verified release calendar/timezone/grace,
reconciliation cadence, hosting, storage and monitoring. Scope acceptance records
the research requirements; no implementation was requested in this exchange,
and acquisition or deployment is not authorized by this specification alone.
