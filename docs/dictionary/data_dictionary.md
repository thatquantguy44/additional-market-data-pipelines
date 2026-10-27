# Data dictionary

The following AAII records are implemented. CFTC, FINRA, OFR, and other provider
schemas remain proposed in Spec 001 and the source backlog.

| Layer | Physical record | Grain and purpose |
| --- | --- | --- |
| Manifest | `manifests/aaii-investor-sentiment.yml` | One dataset; explicit CSV mapping, dates, units, access provenance |
| Bronze | `payload.csv`/`payload.xls`, `metadata.json` | One capture/run; exact bytes, digest, URI, manifest, parser version, capture time, HTTP and selection provenance |
| Bronze | `promotion.json` | Warehouse-promotion receipt, separate from immutable capture metadata |
| Silver | `aaii_silver_versions`, `silver.parquet` | One observed revision of dataset + survey date; unique `version_id` |
| Gold | `aaii_gold_latest`, `gold.parquet` | Latest captured version per dataset + survey date, with prior-survey features |
| Audit | `pipeline_runs`, `audit.parquet` | One capture/run; status, DQ reason, counts, raw path, completion time |
| Control | `pipeline_identity`, `.warehouse.json` | One warehouse identity; prevents accidental root/backend mixing |
| Control | `pipeline_dataset_contract` | Dataset + date basis; prevents mixing reported dates and survey-week labels |

Silver fields:

| Field | Meaning |
| --- | --- |
| `version_id` | SHA-256 of capture identity, survey date, normalized content hash |
| `source`, `dataset` | `aaii`, `aaii-investor-sentiment` |
| `survey_date` | Compatibility field holding the original provider date label; XLS uses Reported Date, without a day shift |
| `bullish`, `neutral`, `bearish` | Finite fractions in [0,1], stored as doubles; no zero imputation |
| `provider_published_at` | Nullable; unknown in both CSV and XLS boundaries |
| `retrieved_at` | UTC timestamp when this input was captured by the pipeline |
| `first_seen_at` | UTC capture time when this consecutive observed state first appeared |
| `content_hash` | SHA-256 of normalized date, shares, and publication field |
| `raw_run_id`, `raw_sha256` | Pointer to original Bronze capture and byte digest |
| `parser_version` | Archived normalization contract (`aaii-csv-v1` or `aaii-xls-v1`) |

A → B → A creates three versions, even though the first and third content hashes
match. Repeating the currently observed state creates no new version. A later
export containing fewer dates does not delete previously observed dates.

Gold adds `bull_bear_spread_pp = 100 * (bullish - bearish)`,
`previous_survey_date`, `gap_days`, `spread_change_pp`, and
`previous_version_id`. First-observation comparison fields are null. Changes
use the preceding available survey, even across gaps; no missing weeks are
fabricated. As-of queries select eligible versions before recomputing features.

Warehouse dates/times are canonical ISO strings for consistent SQLite/PostgreSQL
behavior. Parquet uses `date32`, UTC microsecond timestamps (including all-null
publication columns), `float64` shares/features, and `int64` counts/gaps.

Audit status is `running`, `succeeded`, `failed`, or `partial`. `captured_at` is
the capture timestamp and `completed_at` records the final status update.
`row_count` counts accepted input observations; `inserted_versions` counts new
Silver revisions. Failed validation records a row/rule diagnostic in
`dq_message`; credentials and complete payloads are not logged. There are no
separate DQ outcome or watermark tables in this slice.
