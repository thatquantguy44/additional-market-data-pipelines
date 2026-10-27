# Research roadmap

## Main scope: positioning and market structure

Spec 001 defines the shared ingestion path, starting with CFTC positioning,
followed by FINRA short-sale volume and OFR funding measures. SEC settlement
failures are a candidate extension. Build and verify one provider end to end
before extending coverage. Source selection and individual fields remain subject
to provider-contract verification.

## Later theme: company disclosures and insider activity

Consider SEC insider filings, holdings disclosures, and filing-event metadata.
Perform a separate source/access review and write a new numbered specification
before implementation. Assess overlap with the sister project's existing SEC
company-financials coverage. Preserve accession identifiers, amendments, filing
and acceptance timestamps, and reporting lags. This theme has no enabled sources
or implementation commitments yet.

## Later theme: broader free alternative data

Explore other publicly accessible data relevant to market research after the
core pipeline is dependable. Candidate themes include physical-market activity,
trade/logistics, and public procurement. These are exploration categories, not
verified free providers. Rank candidates by incremental coverage, history,
stable identifiers, access and usage terms, revision behavior, and maintenance
cost. Specify chosen datasets separately before adding connectors.

## Platform growth

SQLite provides the first local integration target. Evaluate PostgreSQL, then
Databricks/Delta and scheduling against actual workload needs. Keep this project's
catalogs, schemas, secrets, job names, and deployment targets independent of the
FRED project.
