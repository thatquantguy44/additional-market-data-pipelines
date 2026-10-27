# Proposed data dictionary

Status: logical contracts only; tables and DDL do not exist yet. Physical names
and source-specific fields must be finalized against real provider schemas.

| Layer | Proposed record | Key and purpose |
| --- | --- | --- |
| Metadata | Dataset manifest | Provider, dataset/report scope, identifiers, frequency, owner, usage metadata |
| Bronze | Raw response | Run/request/page identity, response bytes/hash, request metadata, UTC retrieval time |
| Silver | CFTC position version | Source + report family/scope + contract code + position date + category + observed version |
| Gold | Latest position | Latest observed version per CFTC logical key |
| Gold | Position features | Net position, matching-open-interest share, prior-report change with dates/gaps and lineage |
| Audit | Run | Start/end timestamps, succeeded/partial/failed status, counts |
| Audit | Dataset run | Source/dataset identity, extraction status, row counts, error details |
| Audit | DQ result | Rule, dataset/run, severity, result, reason |

Common timing fields:

- `position_date`: source observation date; not a publication timestamp.
- `provider_published_at`: verified upstream publication time when available;
  nullable when unknown.
- `retrieved_at`: when the HTTP response was captured, in UTC.
- `first_seen_at`: earliest capture of this particular normalized version.

Content hashes identify observed changes. Codes retain leading zeros. Missing
values stay null. Do not infer historical publication vintages from current
historical files. FINRA and OFR require separate dictionaries before promotion.
