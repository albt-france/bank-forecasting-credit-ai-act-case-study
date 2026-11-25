-- requires: data/processed/atm_backtest.parquet
-- Simpson's paradox (SIMULATED): compare forecast error (MAPE) of Brussels and Flanders overall and within each site type.
-- Brussels has many stations, which are hard to forecast.
CREATE OR REPLACE TABLE simpson AS
WITH t AS (
    SELECT region, site_type, COUNT(*) AS n, AVG(ABS(y - pred_model) / y) AS mape
    FROM read_parquet('data/processed/atm_backtest.parquet')
    WHERE y > 0 AND region IN ('Brussels', 'Flanders') GROUP BY 1, 2
)
SELECT region, site_type, n, mape, n * 1.0 / SUM(n) OVER (PARTITION BY region) AS share_of_region FROM t
UNION ALL
SELECT region, 'ALL', SUM(n), SUM(n * mape) / SUM(n), 1.0 FROM t GROUP BY region
ORDER BY site_type, region;
COPY simpson TO 'data/processed/simpson.csv' (HEADER);
