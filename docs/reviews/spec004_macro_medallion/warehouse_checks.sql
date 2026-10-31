-- Read-only review. Requires an already-authorized MacroMedallion connection.
-- Outputs aggregate evidence only; no provider payloads or credentials.
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout = '20s';
SELECT json_build_object(
  'section', 'snapshot', 'captured_at_utc', current_timestamp,
  'transaction_read_only', current_setting('transaction_read_only'),
  'isolation', current_setting('transaction_isolation'),
  'total_ecb_fx_series', (SELECT count(DISTINCT series_id)
    FROM silver.fred_observation WHERE source='ecb' AND series_id LIKE 'ECB:EXR:D.%')
);
WITH scoped AS (
  SELECT * FROM silver.fred_observation WHERE source='ecb'
  AND series_id ~ '^ECB:EXR:D\.(USD|GBP|JPY|CHF|CAD|AUD|NZD|NOK|SEK)\.EUR\.SP00\.A$'
), profile AS (
  SELECT series_id, count(*) AS stored_rows, count(DISTINCT observation_date) AS dates,
    min(observation_date) AS first_date, max(observation_date) AS last_date,
    count(*) FILTER (WHERE COALESCE(realtime_start,'')='') AS blank_vintage_rows,
    count(*) FILTER (WHERE value IS NULL) AS null_value_rows,
    count(*) FILTER (WHERE raw_value IS NULL) AS missing_raw_text_rows,
    min(ingested_at) AS first_retained_capture, max(ingested_at) AS last_retained_capture
  FROM scoped GROUP BY series_id ORDER BY series_id
)
SELECT json_build_object('section', 'silver_profile', 'rows', json_agg(profile)) FROM profile;
WITH scoped AS (
  SELECT * FROM silver.fred_observation WHERE source='ecb'
  AND series_id ~ '^ECB:EXR:D\.(USD|GBP|JPY|CHF|CAD|AUD|NZD|NOK|SEK)\.EUR\.SP00\.A$'
), per_date AS (
  SELECT series_id, observation_date, count(*) AS n,
    count(DISTINCT COALESCE(raw_value, '<null>')) AS distinct_raw,
    bool_or(COALESCE(realtime_start,'')='') AS has_blank,
    bool_or(COALESCE(realtime_start,'')<>'') AS has_dated
  FROM scoped GROUP BY series_id, observation_date
), duplicates AS (
  SELECT series_id, count(*) FILTER (WHERE n>1) AS multi_key_dates,
    count(*) FILTER (WHERE n>1 AND distinct_raw>1) AS differing_raw_dates,
    count(*) FILTER (WHERE has_blank AND has_dated) AS mixed_vintage_dates
  FROM per_date GROUP BY series_id ORDER BY series_id
)
SELECT json_build_object('section', 'vintage_overlap', 'rows', json_agg(duplicates)) FROM duplicates;
SELECT json_build_object('section', 'capture_cutoff', 'series', 'ECB:EXR:D.USD.EUR.SP00.A',
  'cutoff', '2026-08-01T23:59:59+00:00',
  'provider_date_eligible_rows', count(*),
  'captured_by_cutoff_rows', count(*) FILTER (WHERE ingested_at <= '2026-08-01T23:59:59+00:00'))
FROM silver.fred_observation
WHERE series_id='ECB:EXR:D.USD.EUR.SP00.A' AND value IS NOT NULL
  AND COALESCE(realtime_start,'') <= '2026-08-01'
  AND (COALESCE(realtime_end,'')='' OR realtime_end>'2026-08-01');
WITH features AS (
  SELECT feature_name, count(*) AS rows FROM gold.fred_cross_series_feature
  GROUP BY feature_name ORDER BY feature_name
)
SELECT json_build_object('section', 'derived_feature_inventory', 'rows', json_agg(features)) FROM features;
WITH columns AS (
  SELECT table_schema, table_name, column_name, data_type FROM information_schema.columns
  WHERE (table_schema='silver' AND table_name='fred_observation')
     OR (table_schema='gold' AND table_name IN ('fred_point_in_time', 'fred_cross_series_feature'))
  ORDER BY table_schema, table_name, ordinal_position
)
SELECT json_build_object('section', 'schema', 'rows', json_agg(columns)) FROM columns;
WITH profile AS (
  SELECT series_id, count(*) AS latest_dates,
    count(*) FILTER (WHERE value IS NULL) AS null_latest_dates,
    count(*) FILTER (WHERE value <= 0) AS nonpositive_latest_dates,
    min(observation_date) AS first_date, max(observation_date) AS last_date
  FROM gold.fred_latest_observation
  WHERE series_id ~ '^ECB:EXR:D\.(USD|GBP|JPY|CHF|CAD|AUD|NZD|NOK|SEK)\.EUR\.SP00\.A$'
  GROUP BY series_id ORDER BY series_id
)
SELECT json_build_object('section', 'gold_latest_profile', 'rows', json_agg(profile)) FROM profile;
COMMIT;
