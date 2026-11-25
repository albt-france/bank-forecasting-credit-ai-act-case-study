-- requires: data/processed/atm_backtest.parquet
-- MAPE of the rolling-origin backtest (SIMULATED), global model vs seasonal naive, by region, site type and horizon.
CREATE OR REPLACE TABLE atm_backtest AS SELECT * FROM read_parquet('data/processed/atm_backtest.parquet');
CREATE OR REPLACE TABLE acc_by_region AS
SELECT region, COUNT(*) AS n, AVG(ABS(y - pred_model) / y) AS mape_model, AVG(ABS(y - pred_naive) / y) AS mape_naive
FROM atm_backtest WHERE y > 0 GROUP BY 1 ORDER BY 1;
CREATE OR REPLACE TABLE acc_by_site AS
SELECT site_type, COUNT(*) AS n, AVG(ABS(y - pred_model) / y) AS mape_model, AVG(ABS(y - pred_naive) / y) AS mape_naive
FROM atm_backtest WHERE y > 0 GROUP BY 1 ORDER BY 1;
CREATE OR REPLACE TABLE acc_by_horizon AS
SELECT horizon, COUNT(*) AS n, AVG(ABS(y - pred_model) / y) AS mape_model, AVG(ABS(y - pred_naive) / y) AS mape_naive
FROM atm_backtest WHERE y > 0 GROUP BY 1 ORDER BY 1;
COPY (SELECT 'region' AS dim, region AS level, n, mape_model, mape_naive FROM acc_by_region
      UNION ALL SELECT 'site_type', site_type, n, mape_model, mape_naive FROM acc_by_site
      UNION ALL SELECT 'horizon', CAST(horizon AS VARCHAR), n, mape_model, mape_naive FROM acc_by_horizon)
TO 'data/processed/atm_accuracy.csv' (HEADER);
