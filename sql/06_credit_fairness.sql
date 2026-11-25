-- requires: data/processed/credit_scores.parquet
-- PUBLIC DATA: UCI Default of Credit Card Clients (Taiwan, 2005, CC BY 4.0), test set scored by the credit model.
-- Sex and age band are NOT model inputs; they are used here only to measure fairness, in aggregates of 5 or more.
CREATE OR REPLACE TABLE credit_fairness AS
WITH s AS (SELECT * FROM read_parquet('data/processed/credit_scores.parquet')),
g AS (
    SELECT 'sex' AS attribute, sex AS grp, default_next_month, pd_model, decision FROM s
    UNION ALL SELECT 'age band', age_band, default_next_month, pd_model, decision FROM s
)
SELECT attribute, grp, COUNT(*) AS n,
       AVG(default_next_month) AS observed_default_rate,
       AVG(pd_model) AS mean_predicted_pd,
       AVG(CASE WHEN decision = 'accept' THEN 1.0 ELSE 0 END) AS acceptance_rate,
       SUM(CASE WHEN decision = 'decline' AND default_next_month = 0 THEN 1 ELSE 0 END) * 1.0 / NULLIF(SUM(1 - default_next_month), 0) AS good_declined_rate,
       SUM(CASE WHEN decision = 'accept' AND default_next_month = 1 THEN 1 ELSE 0 END) * 1.0 / NULLIF(SUM(default_next_month), 0) AS bad_accepted_rate
FROM g GROUP BY 1, 2 HAVING COUNT(*) >= 5 ORDER BY 1, 2;
COPY credit_fairness TO 'data/processed/credit_fairness.csv' (HEADER);
