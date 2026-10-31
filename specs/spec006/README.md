# Spec 006 — CFTC Traders in Financial Futures, futures-only

Status: **draft for review; provider contract verified, connector not
implemented**. Created 2026-10-31 on branch `spec006-cftc-tff`.

Capability ID: `cftc-tff-futures-only`. This is the first bounded CFTC slice
under the existing `cftc-cot` pipeline family. It covers only the CFTC's
Traders in Financial Futures (TFF) **Futures Only** report; it does not make
Disaggregated, Legacy, Supplemental, or Futures-and-Options Combined data part
of this connector.

## Objective

Provide a traceable, replayable local research dataset of CFTC TFF futures-only
positions. Preserve the provider's report scope, contract identifiers, report
date, classification, raw payload and observed availability. Let researchers
calculate positioning changes only from adjacent available reports, without
mistaking a CFTC trader classification for a trader's intent or a historical
report date for the date the pipeline knew the data.

The first implementation remains a local, source-owned Bronze → Silver → Gold
vertical slice with invented offline fixtures. A public endpoint does not
authorize a live scheduler, a bulk historical download, a production database,
or investment conclusions.

## Official provider contract

### Chosen report and access route

| Contract item | Decision / evidence |
| --- | --- |
| Provider | U.S. Commodity Futures Trading Commission (CFTC) |
| Report family | Traders in Financial Futures (TFF), which covers financial contracts such as currencies, U.S. Treasury securities, stocks, VIX and Bloomberg commodity index. |
| Scope | **Futures Only**. Every accepted row must report `futonly_or_combined = FutOnly`; combined reports are a different dataset and are rejected. |
| PRE dataset ID | `gpe5-46if` — `TFF - Futures Only`. The dataset metadata and a bounded live read were verified on 2026-10-31. |
| API endpoint | `https://publicreporting.cftc.gov/resource/gpe5-46if.json` |
| Metadata endpoint | `https://publicreporting.cftc.gov/api/views/gpe5-46if` |
| Historical cross-check | CFTC's annual TFF futures-only compressed Text/Excel archives. They are reconciliation evidence only for this slice, not an interchangeable ingestion source. |
| Authentication | The CFTC states that PRE API users generally succeed without a token if they do not overuse the API. No key, account or token is requested or stored. |
| Rate policy | CFTC publishes no numeric quota in the reviewed COT material. The implementation must use a single bounded request plan, conservative pacing and explicit `429` handling; it must not infer an unlimited entitlement. |

The official COT FAQ says PRE permits filtering by reporting date/week and
contract-related fields, and export in CSV, RDF, RSS, TSV and XML. The
2026-10-31 bounded read additionally confirmed that the JSON endpoint accepts
an explicit `limit`, `offset` and deterministic `order`; this observed behavior
must be characterized by injected-transport tests, not treated as an
undocumented permanent pagination promise.

### Semantics and timing

- A COT report is a breakdown of **Tuesday** open interest for markets with at
  least 20 reportable traders at or above CFTC reporting levels.
- Futures-only reports are generally released at **3:30 p.m. Eastern** on
  Friday using the prior Tuesday's data. Federal holidays can delay release;
  the CFTC's schedule is tentative.
- `report_date_as_yyyy_mm_dd` is the Tuesday report-date label. The API returns
  a midnight-formatted value, but this pipeline treats it as a date, not as an
  intraday timestamp.
- The CFTC does not publish a historical list of exact release times. The
  initial pipeline leaves `provider_published_at` null unless row-specific
  timestamp evidence exists; the expected Friday release is not an observed
  publication timestamp. `retrieved_at` and `first_seen_at` are actual UTC
  pipeline clocks.
- The CFTC says historical COT data is not updated once published, while the
  TFF explanatory notes say material classification changes can lead to
  corrections being published. Preserve every observed normalized change as a
  version and do not use either statement as permission to overwrite history.
- TFF historical data is documented back to June 13, 2006. The first vertical
  slice is bounded; it does not assert that a full historical backfill is
  complete or that archived history supplies original publication vintages.

### Classification and interpretation

TFF reportable categories are `dealer_intermediary`,
`asset_manager_institutional`, `leveraged_funds`, and `other_reportables`.
Non-reportable positions are a distinct residual group, not a fifth reportable
classification. The CFTC classifies traders based on their predominant business
purpose and Form 40 information, not the reason for every individual trade.
Consequently the connector must not label a category as hedging or speculation,
or infer a trader's strategy, from a position value.

Long, short and spreading are contract counts. Spreading is computed from
offsetting long/short positions; it is not a third directional position to add
only once to a net calculation. Suppressed trader counts may appear as a dot
when fewer than four active traders exist. Preserve that state as null plus a
suppression reason; never coerce it to zero. Positions may still be present.

## Source schema and identity

The verified PRE metadata exposes 90 fields. The raw record is retained intact;
the first normalized slice requires these provider fields:

| Purpose | API fields | Contract |
| --- | --- | --- |
| Provider row reference | `id` | Preserve as a non-authoritative provider reference. CFTC explicitly says its dataset has no primary key. |
| Scope / date | `report_date_as_yyyy_mm_dd`, `yyyy_report_week_ww`, `futonly_or_combined` | Date label and scope must parse and scope must be `FutOnly`. |
| Contract identity | `cftc_contract_market_code`, `cftc_market_code`, `cftc_region_code`, `cftc_commodity_code`, `contract_market_name`, `commodity_name`, `commodity_group_name`, `commodity_subgroup_name`, `contract_units` | Codes are strings, including whitespace/leading zeros in raw. Preserve raw code values; create only explicitly documented normalized display fields. Display names never identify a contract alone. |
| Position basis | `open_interest_all` | Nonnegative integer contract count. |
| Four reportable categories | the `dealer_*`, `asset_mgr_*`, `lev_money_*`, and `other_rept_*` long/short/spread fields | Long/short/spread contract counts, with category names mapped explicitly from this table. |
| Residual group | `nonrept_positions_long_all`, `nonrept_positions_short_all` | A separate non-reportable category; spreading is unavailable, not zero. |
| Provider totals and changes | `tot_rept_*`, `change_in_*`, percentages, trader counts and concentration fields | Preserve raw. Promote only features whose formula and timing are specified; never trust provider change values as a substitute for observed-as-of calculations. |

The first Silver position grain is:

```text
(source, dataset, report_family, report_scope, report_date,
 cftc_contract_market_code, cftc_market_code, cftc_region_code,
 cftc_commodity_code, trader_category)
```

`source = cftc`, `dataset = tff-futures-only`, `report_family = tff`, and
`report_scope = futures_only` are explicit dimensions, not inferred from a URL.
The four reportable categories and the non-reportable residual become five
long-form `trader_category` rows. `total_reportable` remains a provider total
for reconciliation, not a sixth independent category. The implementation must
reject duplicate logical keys within one capture and must retain the raw row for
diagnostics.

## Data lifecycle

### Bronze

Archive exact response bytes before parse, with the selected date/code filters,
dataset ID, redacted URL/query metadata, status, nonsecret response headers,
SHA-256, parser version, run ID and UTC retrieval time. Archive HTTP error
payloads when present. No credentials exist for this source and none may be
invented for logs or configuration.

Each bounded page is a Bronze receipt. A request is incomplete until every
planned page is archived and its deterministic key range reconciles. A missing
page, malformed JSON, changed schema, ambiguous timeout or unhandled `429`
produces a visible failed/partial outcome and cannot advance the successful
watermark.

### Silver and observed revisions

Typed Silver preserves integer contract counts, nullable suppressed trader
counts, source codes, raw lineage, `retrieved_at` and `first_seen_at`. A
repeated identical normalized observation creates no new version; an observed
changed row creates an immutable version even if a CFTC narrative says history
is ordinarily fixed. Historical imports are first known at capture time.

An observed-as-of query first selects the latest version with
`first_seen_at <= cutoff`, then derives positions and changes. It never turns
the Tuesday report date or a scheduled Friday release into a historical
availability guarantee.

### Gold, first slice only

First Gold outputs are explicitly scoped to:

- latest long, short and nullable spreading positions by contract/category;
- category net position, `long - short`, only when both inputs are present;
- net position as a share of matching `open_interest_all`, null for missing or
  zero denominator; and
- change from the prior **available** report for the same logical category,
  including prior date and calendar gap.

No cross-contract aggregation, market-share inference, rolling signal,
backtest, trader recommendation, option reconstruction, or financial advice is
part of the first slice.

## Access, attribution and boundaries

The CFTC web policy states that government information is public domain and
may be copied/distributed, while requesting appropriate CFTC acknowledgement;
it also warns that third-party contributed content can have different rights.
This supports use of the identified CFTC dataset with attribution, but the
implementation still records the source-policy review date and does not assume
rights over unrelated linked material.

Always:

- identify the report as CFTC TFF Futures Only and acknowledge CFTC in output;
- use only bounded, rate-conscious read requests and offline fixtures in tests;
- preserve report date, availability clocks, scope, provider codes, raw lineage,
  observed revisions and missing/suppressed states;
- keep `cftc_tff` proposed as its own package under
  `src/market_data_pipeline/pipelines/` if implementation is approved.

Ask first:

- adding another COT report family/scope, expanding to bulk history, choosing a
  schedule/production warehouse, adding a dependency, or deriving a new
  research signal;
- treating the API's observed `limit`/`offset` behavior as a production
  pagination guarantee without a fixture-backed contract;
- using a CFTC release schedule for an exact historical publication timestamp.

Never:

- query a combined dataset and label it futures-only;
- use names rather than provider codes as the contract identity;
- treat missing/suppressed values as zero, or calculate a net from one side;
- overwrite historical observations, backdate `first_seen_at`, or claim
  point-in-time historical knowledge without captured versions;
- copy sibling database settings, secrets, datasets, Docker volumes or Git
  history.

## Delivery sequence and acceptance criteria

This specification completes only the provider-contract discovery step. The
next implementation phases require a reviewed plan and tasks document.

1. Create provider-shaped invented fixtures for a bounded multi-page response,
   a suppressed trader count, an absent category field, a duplicate logical key,
   a changed historical row and `429`/timeout/schema failures.
2. Build the pure source-owned normalizer and manifest validation before any
   live command.
3. Add local Bronze/Silver/Gold/audit/replay behavior using the fixtures.
4. Prove SQLite first; add PostgreSQL/Parquet and stopped Dagster only after
   the local semantics pass.
5. Request an explicit, bounded live smoke run separately. It must compare the
   live payload against this contract and archive no more data than approved.

The first implementation cannot start until a reviewer accepts the following:

- [ ] Dataset `gpe5-46if`, scope check and the source identity/grain above.
- [ ] CFTC code preservation and no-primary-key policy.
- [ ] Null `provider_published_at` policy and observed-version behavior.
- [ ] Category, spreading and suppression semantics.
- [ ] Offline-only test strategy and no schedule/bulk backfill scope.
- [ ] A source-specific package name and manifest shape, without changing AAII.

## Official sources reviewed

- [CFTC Commitments of Traders FAQ and report families](https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm)
- [CFTC COT release schedule](https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm)
- [TFF Futures Only PRE dataset](https://publicreporting.cftc.gov/Commitments-of-Traders/TFF-Futures-Only/gpe5-46if)
- [TFF Futures Only dataset metadata](https://publicreporting.cftc.gov/api/views/gpe5-46if)
- [CFTC TFF explanatory notes](https://www.cftc.gov/sites/default/files/idc/groups/public/%40commitmentsoftraders/documents/file/tfmexplanatorynotes.pdf)
- [CFTC historical compressed reports](https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm)
- [CFTC web policy and copyright](https://www.cftc.gov/sites/default/files/cftc/cftcprivacy.htm)
