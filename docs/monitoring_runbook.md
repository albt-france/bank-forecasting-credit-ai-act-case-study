# Monitoring runbook

*How the ATM forecast (SIMULATED) and the credit scorecard (PUBLIC DATA) are watched in production.*

## ATM cash forecast

| What | How | Watch | Alert | Action |
|---|---|---|---|---|
| Data quality | `src/data_quality.py` each morning | WARN | FAIL | FAIL: block the run, call data engineering (see `data_contract_atm.md`) |
| Forecast bias by site type | One-sided CUSUM on the daily % error of each segment total, standardised with the backtest mean and SD, slack k = 1 | CUSUM > 5 | CUSUM > 7 (1.25 x the highest value seen Jan-Aug 2026, with no known drift) | Investigate; retrain if the bias persists for 14 days |
| Accuracy | Rolling 7-day MAPE by site type | +5 pts vs backtest | +10 pts | Review features and events calendar |
| Network changes | `atm_master` changes | new or closed ATM | - | Transfer rule for neighbours (50% of the closed ATM's level, fading over 5 weeks) |

**What happened in Sept-Oct 2026 (simulated)**

- Model frozen on 31 Aug 2026.
- **Malls**: alert on **2 Sept 2026** (2 days). Error stayed at -13% after mid-September: a real fall in demand. Action: retrain with the new level.
- **Rural sites**: alert on 6 Sept 2026, back under "watch" by 14 Sept. The model over-forecast the end of summer by about 6%. Action: no retrain; add an end-of-summer feature in the next version.
- City centres and stations: no alert.
- Easter Monday (6 Apr 2026, -45%): no alert, because the model knows public holidays.

## Credit scorecard

| What | Watch | Alert | Action |
|---|---|---|---|
| PSI of the score (monthly) | > 0.10 | > 0.25 | Find which input moved; recalibrate or retrain |
| PSI of each input | > 0.10 | > 0.25 | Check with data engineering first (definition changes) |
| Calibration by score band | gap > 3 pts | gap > 5 pts | Recalibrate the intercept |
| Acceptance by sex and age band | ratio < 0.85 | ratio < 0.80 | Fairness review with compliance |
| Reviewer override rate | +50% vs last quarter | x2 | Review the cut-off and the instructions for use |

## Retraining and rollback

1. A new model is trained on a fixed window, backtested with rolling origins, and compared with the current one on the same period.
2. It goes live only if it is at least as good on every segment and its calibration holds.
3. The previous model and its data snapshot are kept; rollback = switch the model version in the scoring service and re-run the last day.
4. Every change is logged (date, version, reason, approver).
