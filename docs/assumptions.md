# Assumptions

## Simulated ATM network (`src/simulate_atm.py`, seed 42)

"Bank B" is **fictitious**. Nothing here describes a real bank.

| Topic | Assumption |
|---|---|
| Network | 60 ATMs: Brussels 15 (9 stations), Flanders 27, Wallonia 18; site types city centre, station, mall, rural |
| Period | 1 Dec 2024 - 31 Oct 2026, daily |
| Level | Mean withdrawals per day: station €9,000, mall €8,000, city centre €7,000, rural €3,000, times an ATM factor (log-normal, sd 0.25) |
| Weekly pattern | Friday and Saturday high, Sunday low; stations busier on weekdays |
| Start of month | +15% on days 1-3 (salaries) |
| Season | December +6%, 15-24 December +16%; July-August +4% (rural +6% more, city centres -10%) |
| Public holidays | -45% on the 10 statutory Belgian public holidays (Nager.Date) |
| Cash-use trend | -4% a year (assumption: slow decline of cash use) |
| Noise | Log-normal; sd by site type (station 0.26, mall 0.13, city 0.12, rural 0.10); Flanders x1.12, Wallonia x1.05; day-to-day autocorrelation 0.6 |
| Cassettes | Capacity about 4.5 days of mean demand; refills Monday and Thursday or below 20% |
| Average withdrawal | €95 (sd €6) |
| Refill costs | €150 per visit; €40 per stock-out hour; cash holding cost 3% a year |
| Closure transfer | 60% of ATM037's demand moves to ATM036 (truth); the model's rule assumes 50% |

### Hidden events (truth file kept local, never published)

1. Feed outage recorded as 0 (12-13 Mar 2026, 18 ATMs).
2. Duplicate rows after a reload (2 Jun 2026, 9 ATMs).
3. ATM037 closed on 15 May 2026, demand moves to ATM036.
4. Annual 4-day festival (July 2025 and July 2026), x3 on 4 Flanders ATMs.
5. Easter Monday 6 Apr 2026: -45%, a holiday, not an incident.
6. Mall demand -15% from 1 Sept 2026 (assumed new payment habit).
7. Simpson's paradox between Brussels and Flanders.
8. A random day split flatters the model; rolling origin gives the real error.

## Models

| Topic | Assumption |
|---|---|
| Credit cost matrix | Missed default = 5, good client declined = 1 |
| Credit stress (PSI) | SIMULATED: 30% of clients one month later on their last two payments, bill +20% |
| ATM forecast horizon | 7 days (weekly cash planning); lags of 7 days or more |
| Drift thresholds | CUSUM slack k = 1 SD; watch 5; alert = 1.25 x the highest CUSUM in Jan-Aug 2026 |
| Refill rule | Refill when the cassette holds less than the forecast for the day x the 95th percentile of actual / forecast |
