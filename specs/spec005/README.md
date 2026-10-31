# Spec 005 — Company and competitor web traffic estimates

Status: **draft for review; connector not implemented**. Created 2026-10-30.
Capability ID: `company-web-traffic`. Proposed optional paid dataset:
`similarweb-website-traffic`.
User-confirmed scope: **company/competitor traffic estimates**, with **free
sources preferred and a paid option documented**.

## Objective and source decision

Create a traceable research panel of website visit estimates with provider,
domain, geography, device, coverage, observation period and capture availability
kept explicit. A researcher can compare a site's complete months and examine
revisions without confusing missing coverage with zero traffic. Estimated visits
are a research input, not measured revenue, customers, conversions or proof of
predictive value.

Default spending is zero. This review has **not verified a free source of
company-site visit estimates with suitable recurring access, history and
retention rights**. Do not invent one or silently replace visits with a
popularity rank. The free-first build starts with source feasibility and
synthetic provider-shaped fixtures. Authorized local exports may be supported
once their schema and archival rights are verified; their availability is not
assumed. If no suitable free source is found, record acquisition as blocked on
source selection while retaining a usable offline contract.

Similarweb is the documented optional paid candidate for estimated visits.
No subscription, API entitlement, price, credit balance or customer agreement
was inspected. A purchase or credit-consuming request requires a later explicit
decision. A free ranking/attention proxy requires a separate dataset contract
and user selection; it cannot satisfy the visits acceptance criteria below.

This source capability is independent of [FX](../spec004/README.md). Keep the
existing pure-Python [medallion architecture](../../docs/deployment/architecture.md)
and [AAII completion scope](../spec003/README.md) intact. The current manifest,
warehouse and CLI are AAII-specific; proposed fields and commands below require
new source dispatch and source-owned tables, not a change in AAII meaning.

## Official source review and alternatives

Reviewed 2026-10-30. Documentation verification is separate from a live schema
or account test; no competitor data was acquired during this spec work.

| Candidate | Fit, access evidence and decision |
| --- | --- |
| Similarweb visits, optional paid | [Traffic & Engagement reference](https://docs.similarweb.com/api-v5/similarweb-api/website-analysis-api/batch-api/traffic-and-engagement) describes visits and engagement metrics, device/geography filters and `api-key` authentication. [Available data](https://docs.similarweb.com/api-v5/guides/available-data) recommends account-specific `/describe` discovery. Candidate for visits, not an assumed free API. |
| Similarweb economics | [Credit guide](https://docs.similarweb.com/api-v5/guides/data-credits-calculations) describes consumption by returned metric/result and a six-month single-domain/single-country visits example of six credits. Do not request every metric by default or infer a dollar price from credits. |
| Similarweb rights | [Terms](https://www.similarweb.com/corp/legal/terms/) say a negotiated agreement can govern service use. Inspect the actual entitlement for automation, warehouse copies, immutable historical captures, backup/replay, derived outputs, retention after termination and redistribution before acquisition. Public documentation is not an account license. |
| Cloudflare Radar, separate proxy only | [Ranking methodology](https://developers.cloudflare.com/radar/investigate/domain-ranking-datasets/) describes DNS-resolver-based ordered top-100 ranks and larger unordered buckets. This is domain popularity, not site visits or unique visitors. [Licensing policy](https://radar.cloudflare.com/about) identifies API/download data as CC BY-NC 4.0; commercial suitability or an exception must be resolved. Do not assume a free commercial substitute. |
| GA4, unsuitable for this request | [Official quickstart](https://developers.google.com/analytics/devguides/reporting/data/v1/quickstart) requires authenticated property access. It can support authorized owned-site analytics, not arbitrary competitors' measured traffic. No GA4 connector in this spec. |

Public traffic-checker pages, search-interest series and SEO visibility do not
establish a permitted bulk visits feed. Further discovery may add a candidate
with explicit evidence; it must pass the same rights, coverage and schema checks.
No scraping around subscriptions, authentication or access controls.

### Optional Similarweb API contract

The [v5 first-request guide](https://docs.similarweb.com/api-v5/getting-started-1/making-your-first-request)
and [REST/Batch guide](https://docs.similarweb.com/api-v5/guides/rest-api-vs-batch-api)
document the synchronous request shape:

```text
GET https://api.similarweb.com/v5/website-analysis/websites/traffic-and-engagement
    ?domain=example.com&start_date=2026-07&end_date=2026-09
    &granularity=monthly&web_source=total&country=ww
    &metrics=visits&mtd=false&main_domain_only=false&format=json
Header: api-key: <injected at runtime; never archived>
```

This illustrative request was **not executed**; `example.com` is a placeholder,
not a promised covered site. Confirm accepted parameter casing, account coverage,
response row shape, limits and error/no-data cases against `/describe` and a
separately authorized bounded sample. Preserve the API version; never silently
mix v1/v5 or REST/Batch response contracts. Async Batch is deferred.

The [methodology FAQ](https://support.similarweb.com/hc/en-us/articles/5083358615313-Similarweb-Data-Methodology-FAQs)
states that estimates may be fractional, monthly releases occur by the 10th of
the following month, and reporting uses fixed EST without daylight savings.
These are provider conventions, not exact row-level release timestamps or a
customer-specific SLA. Preserve fractional estimates. Domain changes do not
carry old-domain history forward automatically. Capture actual availability
and the selected filters rather than explaining every value change as a revision.

## First delivery and deferred scope

First slice: a small manifest-defined panel, **monthly complete periods and
visits only**, one geography (`ww`, subject to verification), `total` web source,
explicit inclusion of subdomains (`main_domain_only=false`) and `mtd=false`.
Start with at most five user-selected domains, three months and one metric
for a potential live pilot. Use invented `brand-a.example`/`brand-b.example`
domains in fixtures; no production universe is selected yet.

Exclude daily/weekly estimates, partial months, traffic channels, conversions,
mobile-app activity, identity-level browsing, ad spend, revenue inference,
company-wide aggregate traffic, Batch extraction and cloud scheduling from the
first slice. Future device components must never be added to an already total
measure. Worldwide is a distinct scope; do not sum it with country rows.

If a free source is selected later, preserve its native metric and methodology
under its own source/dataset. An authorized export and API result share a series
only after equivalence of filters, units and methodology is proven.

## Proposed manifest and universe

Planned location: `manifests/similarweb-website-traffic.yml`, created only if the
optional provider is selected. This is a **proposed fragment**, not accepted by
today's AAII validator:

```yaml
contract_version: web-traffic-v1
source: similarweb
dataset: similarweb-website-traffic
api_version: v5
format: json
metric: visits
granularity: monthly
country: ww
web_source: total
main_domain_only: false
mtd: false
measurement_type: provider_estimate
domains:
  - brand-a.example
  - brand-b.example
access:
  method: authorized-local-export
  automation: disabled
  rights_review: pending
```

A later API profile references an environment variable name for the key,
never the key itself. Runtime controls include maximum requests, response bytes,
credit budget and allowed bounds; a zero budget blocks paid requests before
I/O. Do not assume discovery is free without checking current provider policy.

Canonicalize domains using an explicit policy: validate host-only input,
IDNA-normalize, lowercase and remove a trailing dot. Reject schemes, paths,
ports, wildcards, malformed names and canonical duplicates. Preserve the user
input and provider-returned domain. Match provider handling of `www` explicitly;
do not strip arbitrary subdomains or assume registrable-domain aggregation.
No DNS lookup or redirect-following may silently rewrite historical identities.

A dated universe registry records additions/removals and selection reasons.
A later domain-to-company mapping must have stable entity IDs, evidence,
effective intervals and first-seen versions. Preserve delisted/acquired domains
when building historical panels. Never relabel all history with today's ticker,
stitch a domain migration automatically or sum overlapping sites as unique
company visitors. Entity aggregation is outside the first delivery.

## Bronze, Silver and availability contracts

Bronze retains original payload bytes, semantic manifest and universe snapshot,
redacted request URL/parameters, nonsecret HTTP metadata, parser/API versions,
run ID, UTC retrieval time, hashes, date/filter selection, provider response
metadata, account capability evidence and review references. Keep raw responses
when parsing or DQ fails. Do not store authorization headers, query tokens,
cookies, signed download credentials or account secrets in archives/logs.
Contractual retention must permit exact payload preservation and replay; if it
does not, this provider cannot satisfy this design without a reviewed revision.

Silver logical key:

```text
(source, dataset, api_contract_version, domain, country, web_source,
 main_domain_only, granularity, period_start, period_end, metric,
 measurement_basis)
```

Keep any additional filtering/segment definition in a versioned contract hash
included in identity. `measurement_basis` distinguishes estimates from any
provider-verified data mode; do not infer it from the value. Parser version is
lineage, not a reason to create a new economic series. A changed provider
methodology is retained as version content with a break flag; introduce a new
series contract where comparability actually changes.

| Field | Contract |
| --- | --- |
| `period_start`, `period_end`, `period_timezone` | Monthly interval with end exclusive; retain the provider date label. Fixed EST/UTC−05:00 for the optional Similarweb contract, not DST-aware New York time. |
| `value`, `unit`, `measurement_type` | Nullable finite nonnegative Decimal visits estimate; fractional counts are valid. Do not round to an integer or divide by 100 without a verified unit contract. |
| `coverage_status`, `provider_status` | Separate observed, insufficient-data, unavailable, suppressed, not-yet-released and verified withdrawal states using actual provider evidence. Never guess the reason from an omitted row. |
| `provider_updated_at`, raw update label | Preserve precision/scope; a month-wide or date-only metadata update is not an exact row publication time. |
| `provider_published_at` | Nullable with evidence; never populate using period end or the expected release day. |
| `retrieved_at`, `first_seen_at` | Actual UTC capture and first capture of this version; historical downloads become available when captured. |
| `version_id`, `content_hash`, `raw_run_id` | Immutable observed version and raw lineage; changes include value and meaningful status/methodology. |

Store request coverage/completeness separately from economic observations.
Only an explicit provider no-data state can create a null-status observation;
an absent row or HTTP failure is not a zero or a deletion. A withdrawal needs
explicit evidence and a versioned state. Unchanged observations add no versions;
A → B → A retains three. Resolve equal capture timestamps deterministically.
Different geography, device, domain/subdomain or measurement modes never revise
each other's rows.

Observed-as-of selects the latest version first seen by the cutoff, and published
by it where verified, **before** deriving features. Closed monthly periods must
also end by the cutoff. Date-only update metadata never backdates availability.
The first historical import is revised history observed today, not a historical
publication-vintage panel. Future remapping/universe versions obey the same
availability rule when used for company research.

## Gold research outputs

Provide `web_traffic_latest`, an observed-as-of view and a coverage/completeness
readout, with native dimensions, estimate/status labels, version lineage and
feature version. Initial features are:

- Monthly visits, with reference period and observed availability visible.
- Month-over-month growth: `current / prior_calendar_month - 1`.
- Year-over-year growth: `current / same_month_prior_year - 1` when enough
  history exists. The three-month pilot correctly returns null for YoY.

Comparisons require exact calendar periods and identical scope, measurement
basis and compatible methodology. A gap does not mean the previous available
row is the previous month. Zero/missing denominator, suppression, incomplete
month, missing comparator or methodology break yields null with a reason.
A real observed zero remains zero and can produce −100% growth against a positive
prior value. No arbitrary rounding or fabricated low-traffic values.

Later peer share is share of a declared observed comparison panel, not market
share. It needs panel membership/version and missing-coverage rules first.
No company-level user counts or revenue proxies are implied by first-slice Gold.

## Extraction, quality, cost and failures

For a selected provider, discover available periods/metrics/countries, estimate
cost, validate the universe and build a bounded request plan before extraction.
Optional Similarweb pilot upper bound: 5 domains × 3 months × 1 geography ×
1 metric = 15 result credits under the documented simple visits model, subject
to current entitlement and validation. This is not a dollar quote or purchase
approval. Retries, reconciliation and duplicate successful requests can consume
additional credits; enforce cumulative run/month budgets including worst-case
attempts. Never log the key while estimating or making requests.

Use injected HTTP/clock, timeouts, byte limits, configurable conservative pacing
and at most three attempts for transient failures with Retry-After/backoff.
Do not retry authentication/permission/schema errors. An ambiguous timeout may
have consumed credits; reserve budget before retry. Verify whether each chosen
endpoint paginates or batches, and archive every required part before marking
an extraction complete. Async report submission requires an idempotency contract
and is deferred.

Blocking DQ: malformed JSON/HTML, unexpected API envelope/status, conflicting
duplicates, invalid domain/period/filter echo, negative/nonfinite values,
truncated response, unrecognized units, overlapping partial/complete periods
or unknown coverage semantics. Provider unsupported/no-data states are explicit
coverage outcomes. Large jumps are warning-level research signals unless a
separate validated rule establishes corruption.

Treat the selected manifest panel/window as one publication unit for the pilot.
A failed domain request must not publish an apparently complete panel or advance
a success checkpoint. Preserve successful raw captures; keep other datasets'
committed snapshots intact. Known no-data responses may complete a request but
must leave the panel flagged incomplete. Warehouse success followed by Parquet
failure is a visible partial publication with recoverable export, following the
existing architecture rather than claiming a distributed transaction.

For monthly updates, propose refetching the most recent three closed months,
with configurable periodic older reconciliation subject to budget. This cannot
guarantee detection of every old revision. Freshness compares expected provider
release/coverage with successful capture and grace, not period age alone.
No daemon or schedule is enabled by this draft; eventual Dagster definitions
start stopped after verified acquisition, storage rights, budget and monitoring.

## Proposed files, style and commands

| Location | Responsibility when implemented |
| --- | --- |
| `src/market_data_pipeline/company_web_traffic/source.py` | Pipeline-owned optional provider transport; no generic scraping engine. |
| `src/market_data_pipeline/company_web_traffic/manifest.py` | Source-specific manifest and universe validation. |
| `src/market_data_pipeline/company_web_traffic/data/` | Immutable records, domain normalization, Decimal parsing, coverage DQ and features. |
| `src/market_data_pipeline/company_web_traffic/` | Pipeline execution, configuration, CLI, replay and Dagster definitions. |
| `src/market_data_pipeline/company_web_traffic/io/` | Source-owned archive, version tables, warehouse adapters and typed snapshots. |
| `tests/fixtures/web_traffic/`, `tests/test_web_traffic_*.py` | Synthetic provider-shaped fixtures, rights/provenance README and transport/end-to-end tests. |
| `docs/deployment/`, `resources/` | Cost/access runbook and stopped Dagster config after provider selection. |

Illustrative pure-core convention, **not implemented**; calling code must first
verify comparable adjacent periods and statuses:

```python
from decimal import Decimal


def visits_growth(current: Decimal, previous: Decimal) -> Decimal | None:
    if not current.is_finite() or not previous.is_finite():
        raise ValueError("visit estimates must be finite")
    if current < 0 or previous < 0:
        raise ValueError("visit estimates must be nonnegative")
    return None if previous == 0 else current / previous - 1
```

Follow the [pipeline package layout](../../docs/development/pipeline_layout.md):
`company_web_traffic/` owns its manifest, CLI, data, persistence and orchestration.
Only provider-independent helpers belong in `shared/`; never import another
pipeline's internals. Preserve existing AAII/root entrypoints when extending
repository dispatch. Use explicit units/dimensions, frozen records,
parameterized SQL and no network inside transforms. Keep a separate root, e.g. `data/web-traffic/`, with its own
source-owned tables/schema and warehouse identity. Do not migrate or test against
the live AAII database. Reuse existing adapters only after compatibility tests.

These CLI examples are **planned; they do not work today** and the fixture
paths do not yet exist. No live command is authorized by the example:

```bash
.venv/bin/python -m market_data_pipeline.company_web_traffic validate \
  --manifest manifests/similarweb-website-traffic.yml
.venv/bin/python -m market_data_pipeline.company_web_traffic run \
  --manifest manifests/similarweb-website-traffic.yml \
  --input tests/fixtures/web_traffic/monthly.json --root data/web-traffic-demo
.venv/bin/python -m market_data_pipeline.company_web_traffic gold --root data/web-traffic-demo \
  --as-of 2026-10-30T20:00:00Z
.venv/bin/python -m market_data_pipeline.company_web_traffic replay --source-root data/web-traffic-demo \
  --root data/web-traffic-replayed
```

Existing implementation verification commands:

```bash
python3 scripts/verify_agent_skills.py
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m build --no-isolation
```

## Build sequence and acceptance criteria

Source feasibility/rights → provider-shaped synthetic fixtures → local
manifest/normalization → Silver/Gold/replay → PostgreSQL/Parquet parity →
explicitly authorized bounded acquisition → stopped Dagster/runbook. A source
cannot pass acquisition readiness on synthetic evidence alone. Keep source-scoped
planning separate from the current AAII `tasks/plan.md` and `tasks/todo.md`.

Offline-contract acceptance:

- [ ] Freeze the selected provider's envelope/field/status contract against
  official docs before parsing. Label synthetic fixtures and preserve their
  shape provenance; never check in restricted real customer data.
- [ ] Manifest/domain/filter validation fails before I/O; API keys are absent
  from manifests, raw metadata, logs, errors and replay outputs.
- [ ] A two-domain, three-month fixture writes exact Bronze, typed Silver,
  versioned Gold, audit, coverage state and a committed Parquet snapshot.
- [ ] Fractional visits, observed zero, no-data, suppressed and missing rows
  remain distinct. Exact-period MoM/YoY handles gaps and null/zero denominators.
- [ ] Identical reruns add no versions; corrections/reversions, filter separation,
  methodology breaks and past as-of exclusion pass deterministic tests.
- [ ] Malformed responses, 401/403, 429 exhaustion, ambiguous timeouts, truncation,
  incomplete multi-request panels and budget exhaustion preserve evidence and
  leave the prior committed panel/checkpoint unchanged.
- [ ] Budget planning and retries cannot exceed the configured credit ceiling;
  the default zero-spend profile makes no paid data requests.
- [ ] Replay in an empty destination preserves capture times, version IDs,
  coverage and as-of features without network/credentials; SQLite/PostgreSQL
  and Parquet preserve decimal/null/status behavior. AAII regressions pass.
- [ ] Injected-transport Dagster materialization uses the same core and exposes
  coverage/cost metadata, with a stopped schedule and no live CI dependency.

Acquisition-readiness acceptance, separately tracked:

- [ ] Either a free visits-estimate source passes the rights/schema/history
  review, or the user explicitly selects the paid provider and spending limit.
  A ranking-only proxy does not tick this box.
- [ ] Actual entitlement permits immutable raw retention, historical warehouse
  versions, backup/replay, intended research and any planned redistribution.
- [ ] The user supplies the initial domain universe; capability discovery and a
  bounded sample verify filters, real no-data behavior, release metadata,
  numeric units, account history and cost against the source review.
- [ ] A tested runbook records permitted use, retention, attribution, cost
  controls, recovery and freshness. Recurring acquisition remains stopped
  pending a separately selected operational environment and schedule.

## Boundaries and remaining decisions

Always retain source/filter/period identity, raw provenance, revisions, coverage
and observed timing, with explicit research limitations. Review first: paid
access, provider changes, a rank/attention proxy, daily granularity, extra metrics,
entity mapping/aggregation, shared migrations, new dependencies or scheduling.
Never bypass access controls, expose keys, interpret no-data as zero, claim
measured competitor analytics or backdate availability to the period label.

Open decisions: suitable free visits source, if any; whether a distinct free
proxy is useful; optional paid provider/budget; initial domains/geography; required
history; and retention/use rights. Until resolved, report **offline contract
ready** and **acquisition not verified** separately. No subscription or deployment
is authorized by this specification.
