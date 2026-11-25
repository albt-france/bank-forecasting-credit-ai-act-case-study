-- requires: data/raw/bank_marketing.parquet
-- PUBLIC DATA: UCI Bank Marketing (Portuguese bank, phone campaigns May 2008 - Nov 2010, CC BY 4.0).
-- Subscription rate to a term deposit by business segment. Age and marital status are not used here
-- (sensitive attributes are only used to measure fairness, in aggregates). Groups below 5 calls are dropped.
CREATE OR REPLACE TABLE bm AS SELECT * FROM read_parquet('data/raw/bank_marketing.parquet');
CREATE OR REPLACE TABLE bm_segments AS
WITH s AS (
    SELECT 'month' AS segment, month AS level, y FROM bm
    UNION ALL SELECT 'contact channel', contact, y FROM bm
    UNION ALL SELECT 'previous campaign outcome', poutcome, y FROM bm
    UNION ALL SELECT 'calls in this campaign', CASE WHEN campaign >= 5 THEN '5+' ELSE CAST(campaign AS VARCHAR) END, y FROM bm
    UNION ALL SELECT 'Euribor 3m at call', CASE WHEN euribor3m < 1.5 THEN 'a. < 1.5%' WHEN euribor3m < 4.5 THEN 'b. 1.5-4.5%' ELSE 'c. >= 4.5%' END, y FROM bm
    UNION ALL SELECT 'day of week', day_of_week, y FROM bm
)
SELECT segment, level, COUNT(*) AS calls, AVG(CASE WHEN y = 'yes' THEN 1.0 ELSE 0 END) AS subscription_rate
FROM s GROUP BY 1, 2 HAVING COUNT(*) >= 5 ORDER BY 1, 2;
COPY bm_segments TO 'data/processed/bm_segments.csv' (HEADER);
