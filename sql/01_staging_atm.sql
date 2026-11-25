-- requires: data/sim/atm_daily.parquet
-- Staging (SIMULATED): one row per (date, atm_id); zeros recorded during a feed outage become NULL.
CREATE OR REPLACE TABLE atm_master AS SELECT * FROM read_parquet('data/sim/atm_master.parquet');
CREATE OR REPLACE TABLE holidays AS SELECT CAST(date AS DATE) AS date, name, statutory FROM read_csv_auto('data/processed/holidays_be.csv');
CREATE OR REPLACE TABLE local_events AS SELECT * FROM read_parquet('data/sim/local_events.parquet');
CREATE OR REPLACE TABLE stg_atm_daily AS
WITH raw AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY date, atm_id ORDER BY refill_flag DESC) AS rn
    FROM read_parquet('data/sim/atm_daily.parquet')
)
SELECT CAST(date AS DATE) AS date, atm_id,
       CASE WHEN withdrawals_eur = 0 AND n_transactions = 0 AND out_of_service_hours = 0 THEN NULL ELSE withdrawals_eur END AS withdrawals_eur,
       CASE WHEN withdrawals_eur = 0 AND n_transactions = 0 AND out_of_service_hours = 0 THEN NULL ELSE n_transactions END AS n_transactions,
       cassette_capacity_eur, refill_flag, out_of_service_hours,
       (withdrawals_eur = 0 AND n_transactions = 0 AND out_of_service_hours = 0) AS feed_gap
FROM raw WHERE rn = 1;
