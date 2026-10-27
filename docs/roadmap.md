# Master research roadmap and source backlog

Last updated: 2026-10-26. This is the canonical backlog for source selection;
the [master handoff](handoffs/project_bootstrap.md) records the current pickup
point. AAII has an executable authorized-local-CSV slice; automated provider
retrieval remains unverified. Other sources remain unimplemented. Research uses are hypotheses,
and neither low adoption nor predictive value has been established.

## Main scope: positioning and market structure

Spec 002 implements AAII first with Parquet, SQLite/PostgreSQL, and Dagster.
Spec 001 retains the broader ingestion design, with CFTC positioning,
FINRA short-sale volume and OFR funding measures still planned. SEC settlement
failures are a candidate extension. Build and verify one provider end to end
before extending coverage. Source selection and individual fields remain subject
to provider-contract verification.

## Additional positioning and market-structure sources

The following seven additions remain in the backlog. AAII is promoted to the
first local CSV slice; the other six remain research candidates. They supplement CFTC, FINRA short-sale
volume, OFR STFM, and SEC fails-to-deliver candidates in the
[source catalog](catalog/README.md). FINRA venue transparency is distinct from
short-sale volume; OFR Hedge Fund Monitor is distinct from STFM.

Access descriptions reflect the official documentation reviewed on 2026-10-26,
not a completed live extraction test. Confirm endpoints, availability, terms,
authentication, and free access before implementation.

| Backlog ID | Source and official reference | Data and potential use | Proposed access | Implementation considerations |
| --- | --- | --- | --- | --- |
| `nyfed-primary-dealers` | [NY Fed Primary Dealer Statistics](https://www.newyorkfed.org/markets/counterparties/primary-dealers-statistics) | Positions, transactions, financing, and settlement fails; dealer inventory and financing-pressure research | [Markets REST API](https://markets.newyorkfed.org/static/docs/markets-api.html), CSV/JSON exports | Preserve historical reporting-definition eras, revisions, publication timing, and suppression rules. |
| `ofr-hedge-fund-monitor` | [OFR Hedge Fund Monitor](https://www.financialresearch.gov/hedge-fund-monitor/) | Aggregate leverage, liquidity, counterparty concentration, financing surveys, and sponsored repo; broader risk context for COT | [JSON API without registration](https://www.financialresearch.gov/hedge-fund-monitor/api/) | Refresh cadence varies; assess overlap with direct CFTC coverage and review underlying-provider terms. |
| `finra-otc-transparency` | [FINRA ATS/non-ATS transparency](https://developer.finra.org/catalog) | Aggregate trading activity by ATS or reporting firm and block summaries; venue concentration and activity shifts | Download files and documented API datasets | Verify current production access, entitlements, publication lags, corrections, and matching coverage/denominators. |
| `sec-nmfp` | [SEC Form N-MFP](https://www.sec.gov/data-research/sec-markets-data/dera-form-n-mfp-data-sets) | Money-market-fund portfolios; funding exposures and portfolio shifts | Monthly ZIP datasets of flattened filings | Preserve observation, filing, and public availability dates; handle form/schema changes and amendments. |
| `dtcc-public-swaps` | [DTCC public swap dissemination](https://pddata.dtcc.com/ppd/info-center) | Public swap and security-based-swap transaction data; derivatives-activity research | Public dashboard and reporting downloads | Higher expected engineering effort: verify current download routes, trade lifecycle handling, corrections/cancellations, and reporting conventions before aggregation. |
| `sec-midas` | [SEC Market Structure Analytics / MIDAS](https://www.sec.gov/featured-topics/market-structure-analytics) | Published market metrics and research datasets; market-quality analysis | Published dataset downloads | Verify each dataset's history and freshness; published extracts do not provide unrestricted access to underlying MIDAS feeds. |
| `aaii-investor-sentiment` | [AAII Investor Sentiment Survey](https://www.aaii.com/sentiment-survey) | Weekly bullish, neutral, and bearish shares for individual investors; sentiment spread, changes, and historical-percentile research | Official survey results and [historical results/download page](https://www.aaii.com/sentimentsurvey/sent_results); access review required | Verify historical-data membership requirements, cost, permitted automation, and reuse terms; no official public API verified. Preserve survey period and actual publication time; opinion measures are not holdings or trade flows. |

AAII is first at the user's request. Recommended order for the remaining additions:
**NY Fed Primary Dealer Statistics → SEC
N-MFP → FINRA ATS/non-ATS → OFR Hedge Fund Monitor**. This is a prioritization
proposal for the backlog; Spec 002 governs the current AAII-first build order.
Retain DTCC and MIDAS for later evaluation; do not silently drop them because
they are outside the first implementation slice.

## Later theme: company disclosures and insider activity

Consider SEC insider filings, holdings disclosures, and filing-event metadata.
Perform a separate source/access review and write a new numbered specification
before implementation. Assess overlap with the sister project's existing SEC
company-financials coverage. Preserve accession identifiers, amendments, filing
and acceptance timestamps, and reporting lags. This theme has no enabled sources
or implementation commitments yet.

| Backlog ID | Source and official reference | Data and potential use | Proposed access | Implementation considerations |
| --- | --- | --- | --- | --- |
| `sec-nport` | [SEC Form N-PORT](https://www.sec.gov/data-research/sec-markets-data/form-n-port-data-sets) | Public fund holdings, with derivatives and securities-lending tables; overlap, ownership concentration, and exposure research | Quarterly ZIP datasets | Respect public reporting lags, amendments, portfolio dates, and fund/security identifiers; avoid look-ahead in ownership features. |
| `fdic-bankfind` | [FDIC BankFind](https://api.fdic.gov/banks/docs) | Bank financials, branches, deposits, failures, and institutional history; funding and balance-sheet research | JSON/CSV API; reviewed docs say a key is currently not required | Recheck authentication policy; maintain a historical crosswalk from banks/subsidiaries to listed corporate parents. |

SEC insider filings and filing-event metadata remain additional future discovery
themes; no specific new access contract is assumed for those themes here.

## Later theme: broader free alternative data

Explore physical-market activity, trade/logistics, and public procurement after
the core pipeline is dependable. Retain these five concrete source candidates:

| Backlog ID | Source and official reference | Data and potential use | Proposed access | Implementation considerations |
| --- | --- | --- | --- | --- |
| `usda-mymarketnews` | [USDA MyMarketNews](https://mymarketnews.ams.usda.gov/mymarketnews-api) | Agricultural market reports and prices; regional price dispersion and input-cost research | API and report downloads; registration provides an API key | Normalize commodity grades, locations, units, and report IDs; track corrected reports and publication times. |
| `stb-rail-service` | [Surface Transportation Board rail data](https://www.stb.gov/reports-data/rail-service-data/) | Weekly train speeds, dwell, cars held, grain loading, and other service measures; freight congestion research | Public spreadsheets and reports | Handle carrier methodology differences, historical file formats, reorganizations, and reporting changes. |
| `epa-clean-air-markets` | [EPA Clean Air Markets](https://www.epa.gov/power-sector/cam-api-portal) | Power-plant emissions, operating data, facilities, and allowances; plant-activity and power-sector research | REST APIs with an API key and bulk files | Observation granularity is not publication latency; reconcile units, facility ownership, revisions, and apportioned versus raw reported data. |
| `usace-corps-locks` | [USACE Corps Locks](https://www.iwr.usace.army.mil/About/Technical-Centers/NDC-Navigation-and-Civil-Works-Decision-Support/NDC-Locks/) | Vessel movements, lockage times, and delays; inland-waterway congestion research | Public tables and reports | Verify export routes, automation terms, historical retention, coverage, and gaps before selecting a scraper. |
| `usaspending` | [USAspending](https://api.usaspending.gov/) | Federal awards, recipients, agencies, and transactions; government-demand exposure research | Public API and bulk downloads | Separate ceilings, obligations, and outlays; resolve recipients to corporate parents and retain award modifications and reporting dates. |

Rank candidates by incremental coverage, history, stable identifiers, usage
terms, revision behavior, and maintenance cost. Check overlap with the sister
FRED project's existing datasets. Specify chosen datasets separately before
adding connectors.

## Backlog status and promotion rules

All **14 additional source IDs** are retained. AAII has a validated manifest,
authorized-local-CSV importer, Parquet output, warehouse adapters, and a stopped
Dagster schedule definition. A bounded official XLS download, current workbook parsing, and a four-row live
PostgreSQL load are verified. Routine download entitlement remains unverified;
offline fixtures are synthetic. The other **13 additions**
remain research candidates without implemented connectors. Retain these IDs
across future specs and handoffs.

For each candidate, progress through these stages and record the evidence:

1. Verify official provider documentation, endpoints, cost, automation/reuse
   terms, authentication, attribution, and rate limits.
2. Confirm incremental value, coverage, grain, identifiers, units, publication
   timing, revisions, and overlap with existing sources.
3. Capture a bounded sample and offline fixture; document schema and failure
   behavior. Prefer APIs, then bulk files, then HTML scraping where appropriate.
4. Define or extend a numbered specification with source-specific contracts and
   acceptance criteria before implementation.
5. Verify Bronze retention, Silver idempotency and revisions, Gold semantics,
   audit/DQ, availability-aware queries, and replay before enabling a source.

Persist original payloads, observation dates, verified publication dates when
known, retrieval timestamps, first-seen versions, and corrections. Free viewing
or downloading does not establish redistribution permission.

## Platform growth

SQLite and Parquet provide the local integration targets. PostgreSQL persistence
is implemented through the same contract. Dagster is the initial orchestrator;
Airflow and Mage wrappers are deferred. A Databricks/Delta publisher is implemented
but awaits live workspace verification. No production deployment is active.
Keep this project's
catalogs, schemas, secrets, job names, and deployment targets independent of the
FRED project.
