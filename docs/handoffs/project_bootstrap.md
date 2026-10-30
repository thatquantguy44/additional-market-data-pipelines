# MarketMedallion — master handoff and current pickup point

Last updated: 2026-10-30.

The current repository name is `market-medallion` (MarketMedallion), at
`https://github.com/thatquantguy44/market-medallion`. The local checkout is
`pipelines/market-medallion`; the previous checkout path is a compatibility
symlink for archived absolute paths and existing workspace references. Package
distribution metadata and the request identifier use the new name. The import
path remains `market_data_pipeline`, and both CLI names are supported.
Existing PostgreSQL, roles, Docker projects/volumes and data are preserved.

**Current stopping point:** the first AAII slice, configured PostgreSQL live run,
and pinned local workflow snapshot are complete. Read
[AAII checkpoint and next scoped work](aaii_checkpoint.md) before implementation.
The recommended next task is offline end-to-end coverage of the existing bounded
live Dagster path. It does not add a source or enable a schedule.
The checkpoint commits were pushed to `origin/main`. Hosted CI could not start
because GitHub reported an account billing/Actions spending-limit block; 54 tests
passed locally. See the focused checkpoint for the run link and recovery step.

The workflow library is now a complete local snapshot at `agents/agent-skills/`,
pinned by `agents/agent-skills.lock.json` to revision
`f63ec56a3cc936408d792956ae583c3c96a825bd`. It replaces the old submodule;
normal use and checksum verification require no network refresh.

The user requested a sister repository named
`additional-market-data-pipelines`, beside `fred-bronze-to-gold-pipeline`.
They selected positioning and market structure as the main spec, requested the
same general repository format, and retained disclosures/insider activity and a
broader alternative-data mix for later.

Completed: independent repository scaffold and original design, plus the first
AAII slice under Spec 002. The implementation has a strict local CSV manifest,
immutable Bronze, observed Silver revisions, Gold/as-of features, audit,
SQLite/PostgreSQL persistence, typed Parquet snapshots, replay, CLI, and Dagster
asset/job/stopped schedule. A Databricks publisher and notebook are implemented
but not live-tested in a workspace. A bounded official AAII XLS load is now
verified in persistent local PostgreSQL; no recurring download or cloud deployment is active.

The user also requested that every additional source discussed be retained in
the handoff and roadmap. The [master roadmap](../roadmap.md) is the canonical
source backlog, with official references, proposed access methods, research
uses, limitations, and stable backlog IDs for all 14 additions.

## Retained source inventory

Current sequence: AAII first at the user's request, then the remaining Spec 001
sources (CFTC positioning → FINRA short-sale volume → OFR Short-term Funding
Monitor) remain planned. SEC fails-to-deliver remains a candidate extension.
See the [source catalog](../catalog/README.md) for those original four sources.

Additional positioning and market-structure candidates:

- `nyfed-primary-dealers`: NY Fed Primary Dealer Statistics.
- `ofr-hedge-fund-monitor`: OFR Hedge Fund Monitor, distinct from STFM.
- `finra-otc-transparency`: FINRA ATS/non-ATS activity, distinct from short-sale
  volume.
- `sec-nmfp`: SEC money-market-fund portfolio holdings.
- `dtcc-public-swaps`: DTCC public swap/security-based-swap dissemination.
- `sec-midas`: SEC Market Structure Analytics / MIDAS published datasets.
- `aaii-investor-sentiment`: first implemented local CSV slice for weekly bullish,
  neutral, and bearish shares. The current official XLS layout and bounded live
  load are verified; recurring entitlement, membership requirements, and reuse
  still require review. Fixtures are synthetic; no official
  public API or free full-history entitlement has been verified.

Later company/holdings candidates:

- `sec-nport`: SEC fund portfolio holdings, derivatives, and securities lending.
- `fdic-bankfind`: FDIC bank financials, deposits, branches, and history.

Later alternative-data candidates:

- `usda-mymarketnews`: USDA agricultural reports and prices.
- `stb-rail-service`: Surface Transportation Board rail performance.
- `epa-clean-air-markets`: EPA plant emissions and operating data.
- `usace-corps-locks`: USACE vessel movements, lockage times, and delays.
- `usaspending`: Federal awards, recipients, and award transactions.

Company insider filings and filing-event metadata also remain future themes.
The other additions are a research backlog; connector access and functionality
have not been validated by live extraction. All 14 IDs remain in the roadmap.

## Next work

Current contract: Spec 002, with plan/tasks under `tasks/`. Run the README demo
and use `docs/deployment/aaii_runbook.md` for PostgreSQL, Dagster, Parquet, replay,
and Delta publishing. Local tests cover validation, revisions/reversion, as-of
changes, raw retention, replay, CLI, and Dagster. PostgreSQL has a real opt-in
test; use a dedicated empty test database. `origin/main` is configured for this
repository; the user requested a commit/push series at closeout. No cloud
deployment or recurring download is active.

Completed follow-up: strict runtime YAML now controls host/port/database/login,
role/schema, SSL and timeout, with environment-only passwords. The official XLS
was downloaded and inspected; four reported dates in October 2026 are persisted
in database additional_market_data, schema aaii, via role aaii_writer, localhost
port 55438. The persistent Compose project is additional-market-data-live.
Settings are in ignored config/config.yaml and .env; raw and Parquet evidence is
in data/aaii-live/verification.json. Reimport added zero versions.

The next bounded engineering task and acceptance criteria are in the checkpoint.
After that, provider work is to verify recurring acquisition entitlement and reuse terms
before configuring scheduled downloads. Keep Reported Date labels unshifted. Next
platform work: live-test Delta in a selected workspace; configure durable worker
storage, secret injection, backups, freshness monitoring, and alerts before
production scheduling. Mage/Airflow wrappers remain optional.

After the initial pipeline slice, the recommended order for the new additions
is NY Fed Primary Dealer Statistics → SEC N-MFP → FINRA ATS/non-ATS → OFR Hedge
Fund Monitor. Keep DTCC and MIDAS queued for later evaluation. This ordering does
not replace the current AAII-first implementation priority.

Use the roadmap's promotion checklist before implementing each candidate:
verify access/terms, coverage and schema, publication/revision semantics, then
capture fixtures and specify acceptance criteria. Preserve provider-specific
grains and original availability timestamps. Update this handoff and the
roadmap when status or priorities change so the same inventory stays visible.
