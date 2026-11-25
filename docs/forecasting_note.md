# Forecasting note: Belgian mortgages and deposits

*PUBLIC DATA. Code: `src/forecast_bank_series.py`. Data read on 25 Nov 2026.*

## Data (ECB Data Portal)

| Series | Key | Unit |
|---|---|---|
| Household overnight deposits, Belgium (stocks) | `BSI.M.BE.N.A.L21.A.1.U2.2250.Z01.E` | EUR millions (`UNIT_MULT` = 6) |
| Rate on new mortgages to households, Belgium | `MIR.M.BE.B.A2C.A.R.A.2250.EUR.N` | % per year (`UNIT_MULT` = 0) |
| New mortgage business volume, Belgium | `MIR.M.BE.B.A2C.A.B.A.2250.EUR.N` | EUR millions (`UNIT_MULT` = 6) |

Monthly, 2015-01 to 2026-09 (141 points). The key `...A2C.P.B...` returns 404: `A.B` is the working one.

## Method

- **Models**: seasonal naive (same month last year); ETS on log volume (additive damped trend, additive seasonality); SARIMAX(1,1,1)(0,1,1,12) on log volume with the new-mortgage rate as exogenous variable.
- **Rolling-origin backtest**: 12 origins (2024-10 to 2025-09), each fitted on data up to the origin and forecasting 1-12 months ahead.
- **Metrics**: MAPE; MASE (scaled by the in-sample error of the seasonal naive); share of actual values inside the 80% and 95% intervals.
- In the backtest, SARIMAX uses the rate that actually happened: it measures the model *given* the rate path, which is how it is used with scenarios.

## Results

| Model | MAPE | MASE | Inside 80% | Inside 95% |
|---|---|---|---|---|
| ETS | 8.4% | 0.31 | 97% | 99% |
| SARIMAX + rate | 11.0% | 0.41 | 99% | 99% |
| Seasonal naive | 15.0% | 0.56 | - | - |

- ETS is the most accurate overall; SARIMAX is close at 1-2 months and worse beyond 6 months.
- Intervals are **too wide** (97% inside instead of 80%): safe, but they could be narrowed (e.g. conformal intervals from backtest errors).
- **Rate effect** (SARIMAX on the full sample): -35% volume per +1 percentage point, 95% CI -53% to -8%, p = 0.013. The direction is clear, the size is not.

## Scenarios (next 12 months, 2026-10 to 2027-09)

| Scenario | Rate | Total new mortgages |
|---|---|---|
| Stable | 3.76% | €41.8 bn |
| -50 bp | 3.26% | €51.7 bn |
| +50 bp | 4.26% | €33.8 bn |

Last 12 months actual: €41.7 bn. The scenario spread is driven by the uncertain rate coefficient; use it as a range, not as a prediction.

## Deposits: a dated break

- Household overnight deposits rose from €61.0 bn (2015-01) to a **peak of €136.1 bn in 2022-06**, then fell to **€108.7 bn in 2026-09** (-20%).
- A two-trend least-squares fit puts the turn in **2021-10**: about +10% a year before, -4% a year after (Chow F = 372; the date was searched, so the test is optimistic and only used to describe).
- **No cause is claimed**: this note describes the date and size of the change only.
- Forecasting deposits 1-12 months ahead: "last value" MAPE 2.9%, ETS 3.1%. No model beats the naive rule here.

## Limits

141 monthly points; one rate variable; no house prices, incomes or policy changes; breaks cannot be forecast; scenarios assume the rate jumps at once and stays flat.
