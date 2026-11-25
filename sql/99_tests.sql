-- requires: data/processed/atm_backtest.parquet
-- Assertions: each query returns (test, failures); run_sql.py stops if any failure count is above 0.
SELECT 'one row per (date, atm_id) in staging' AS test, COUNT(*) AS failures
FROM (SELECT date, atm_id FROM stg_atm_daily GROUP BY 1, 2 HAVING COUNT(*) > 1);
SELECT 'feed-gap zeros are NULL in staging' AS test, COUNT(*) AS failures FROM stg_atm_daily WHERE feed_gap AND withdrawals_eur IS NOT NULL;
SELECT 'no rows after decommissioning' AS test, COUNT(*) AS failures
FROM stg_atm_daily s JOIN atm_master m USING (atm_id) WHERE m.decommissioned IS NOT NULL AND s.date >= CAST(m.decommissioned AS DATE);
SELECT 'no fairness group below 5' AS test, COUNT(*) AS failures FROM credit_fairness WHERE n < 5;
SELECT 'no marketing segment below 5' AS test, COUNT(*) AS failures FROM bm_segments WHERE calls < 5;
SELECT 'no duration in the final marketing model' AS test, COUNT(*) AS failures
FROM read_csv_auto('data/processed/bm_final_features.csv') WHERE lower(feature) LIKE '%duration%';
SELECT 'no sensitive attribute in the credit model' AS test, COUNT(*) AS failures
FROM read_csv_auto('data/processed/credit_final_features.csv') WHERE upper(feature) IN ('SEX', 'AGE', 'MARRIAGE');
SELECT 'Easter Monday 2026 not flagged by DQ' AS test, COUNT(*) AS failures
FROM read_csv_auto('data/processed/dq_report.csv') WHERE "check" LIKE 'network-level%' AND status <> 'PASS';
