# Data contract: ATM daily feed (SIMULATED "Bank B")

*Agreement between data engineering (producer) and data science (consumer). Checks run by `src/data_quality.py` and `sql/99_tests.sql`.*

## What is delivered

| Table | Grain | Key | Owner |
|---|---|---|---|
| `atm_daily` | one row per ATM per day | (`date`, `atm_id`) | data engineering (ATM switch feed) |
| `atm_master` | one row per ATM | `atm_id` | network team |
| `feed_log` | one row per delivery and source system | (`date`, `source_system`) | data engineering |
| `local_events` | one row per known event | (`date_from`, `region`) | branch network |
| `refill_costs` | assumptions | - | cash logistics |

### `atm_daily` schema

| Column | Type | Rule |
|---|---|---|
| `date` | date | not null |
| `atm_id` | text | not null, exists in `atm_master` |
| `withdrawals_eur` | number | not null; **NULL when the feed failed, never 0** |
| `n_transactions` | integer | not null; 0 only if the ATM was out of service |
| `cassette_capacity_eur` | integer | from `atm_master` |
| `refill_flag` | 0/1 | |
| `out_of_service_hours` | number | 0-24 |

## Service levels

- **Freshness**: the daily file arrives before **08:00 the next day**.
- **Completeness**: rows per day = ATMs active that day in `atm_master`.
- **Uniqueness**: one row per (`date`, `atm_id`); a reload must replace, not append.
- **Decommissioning**: the network team updates `atm_master.decommissioned` **before** the last day; no rows after it.

## Checks (status in `data/processed/dq_report.csv`)

| Check | Rule | Result on the simulated feed | Who fixes |
|---|---|---|---|
| Unique key | no duplicate (`date`, `atm_id`) | FAIL: 9 duplicates on 2026-06-02 (file reloaded) | data engineering: reload guard; data science: dedupe in staging |
| Zero vs missing | 0 EUR and 0 transactions while in service = missing | FAIL: 36 rows on 12-13 Mar 2026 (18 ATMs) | data engineering: send NULL; staging sets NULL |
| Required fields | not null | PASS | - |
| Freshness | before 08:00 next day | WARN: 2 late files (feed outage) | data engineering |
| Volume | rows per day = active ATMs | FAIL: 68 rows vs 59 on 2026-06-02 | data engineering |
| Decommissioned ATMs | no rows after the date | PASS (ATM037, 15 May 2026) | network team |
| Extreme values | > 2.5x the ATM's weekday median | WARN: festival days match `local_events` (kept); isolated spikes sent for review | branch network + data science |
| Network drops | day total < 60% of last week | PASS: all drops are statutory public holidays (incl. Easter Monday 2026-04-06): **no alert** | - |

## Escalation

1. A FAIL blocks model retraining and is reported to the data engineering on-call the same morning.
2. A WARN is logged in `data_issues_log.md` and reviewed weekly.
3. A correction is re-delivered as a full replacement of the affected days; the staging SQL is idempotent.
