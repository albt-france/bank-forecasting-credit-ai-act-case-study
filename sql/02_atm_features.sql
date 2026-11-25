-- requires: data/sim/atm_daily.parquet
-- Features for the 7-day-ahead ATM forecast (SIMULATED). Every lag is at least 7 days old, so a forecast made on
-- day t for t+1..t+7 only uses data known on day t.
CREATE OR REPLACE TABLE atm_features AS
WITH base AS (
    SELECT s.*, m.region, m.site_type, m.location_code
    FROM stg_atm_daily s JOIN atm_master m USING (atm_id)
), ev AS (
    SELECT b.date, b.atm_id,
           MAX(CASE WHEN b.date BETWEEN CAST(e.date_from AS DATE) AND CAST(e.date_to AS DATE)
                     AND list_contains(string_split(e.atm_ids, ','), b.atm_id) THEN 1 ELSE 0 END) AS local_event
    FROM base b CROSS JOIN local_events e GROUP BY 1, 2
), nb AS (   -- a neighbour at the same location was decommissioned before this date
    SELECT b.date, b.atm_id,
           MAX(CASE WHEN m2.decommissioned IS NOT NULL AND b.date >= CAST(m2.decommissioned AS DATE) THEN 1 ELSE 0 END) AS neighbour_closed
    FROM base b LEFT JOIN atm_master m2 ON m2.location_code = b.location_code AND m2.atm_id <> b.atm_id GROUP BY 1, 2
)
SELECT b.date, b.atm_id, b.region, b.site_type, b.withdrawals_eur AS y, b.feed_gap,
       dayofweek(b.date) AS dow, day(b.date) AS dom, month(b.date) AS month,
       CASE WHEN day(b.date) <= 3 OR (day(b.date) = 4 AND dayofweek(b.date) = 1) THEN 1 ELSE 0 END AS start_of_month,
       CASE WHEN h.date IS NOT NULL AND h.statutory THEN 1 ELSE 0 END AS holiday,
       CASE WHEN month(b.date) = 12 AND day(b.date) BETWEEN 15 AND 24 THEN 1 ELSE 0 END AS pre_christmas,
       ev.local_event, nb.neighbour_closed,
       LAG(b.withdrawals_eur, 7)  OVER w AS lag7,
       LAG(b.withdrawals_eur, 14) OVER w AS lag14,
       AVG(b.withdrawals_eur) OVER (w ROWS BETWEEN 13 PRECEDING AND 7 PRECEDING) AS mean_7_13,
       AVG(b.withdrawals_eur) OVER (w ROWS BETWEEN 34 PRECEDING AND 7 PRECEDING) AS mean_7_34
FROM base b
LEFT JOIN holidays h ON h.date = b.date
JOIN ev ON ev.date = b.date AND ev.atm_id = b.atm_id
JOIN nb ON nb.date = b.date AND nb.atm_id = b.atm_id
WINDOW w AS (PARTITION BY b.atm_id ORDER BY b.date);
COPY (SELECT * FROM atm_features ORDER BY date, atm_id) TO 'data/processed/atm_features.parquet' (FORMAT parquet);
