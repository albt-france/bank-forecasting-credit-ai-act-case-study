# Data issues log

| # | Date found | Source | Issue | Impact | Fix | Status |
|---|---|---|---|---|---|---|
| 1 | 25 Nov 2026 | ECB MIR | Key `MIR.M.BE.B.A2C.P.B...` returns 404 | Volume series not found | Use `MIR.M.BE.B.A2C.A.B.A.2250.EUR.N` | Closed |
| 2 | 25 Nov 2026 | ECB BSI, MIR | Values in EUR millions (`UNIT_MULT` = 6), rate in % (`UNIT_MULT` = 0) | Wrong scale if ignored | Units stated on every chart and table | Closed |
| 3 | 25 Nov 2026 | UCI Bank Marketing | Nested archive (`bank.zip`, `bank-additional.zip`) | Wrong file read | Read `bank-additional-full.csv` (`;` separator) inside the inner zip | Closed |
| 4 | 25 Nov 2026 | UCI Bank Marketing | `duration` known only after the call | Leak: AUC 0.82 → 0.95 | Excluded from the final model; SQL test | Closed |
| 5 | 25 Nov 2026 | UCI Bank Marketing | `pdays = 999` means "never contacted" | Treated as a huge number | Recoded to -1 | Closed |
| 6 | 25 Nov 2026 | UCI Bank Marketing | File is in call order; the last 20% have a 31% subscription rate vs 11% overall | A time split mixes model quality with a change of context | Main result on a stratified split; time split reported as a robustness check | Closed |
| 7 | 25 Nov 2026 | UCI Credit Default | `.xls` with a double header row | Wrong column names | Read with `header=1` | Closed |
| 8 | 25 Nov 2026 | EUR-Lex | May answer 202 (bot check); `.ENG.xhtml` URL may 404 | Text not retrieved | Publications Office URL with `Accept` and `Accept-Language` headers | Closed |
| 9 | 25 Nov 2026 | Nager.Date (BE) | Lists Good Friday, the day after Ascension and 26 December as Belgian holidays; they are not among the 10 statutory public holidays | Wrong holiday effects | Column `statutory`; only the 10 statutory days are used | Closed |
| 10 | Simulated | ATM feed | Feed outage 12-13 Mar 2026: 0 EUR recorded instead of missing (18 ATMs, 36 rows) | Model learns "empty days" | Staging sets NULL; contract: send NULL | Closed |
| 11 | Simulated | ATM feed | File reloaded on 2 Jun 2026: 9 duplicate rows | Double counting | Dedupe on (`date`, `atm_id`); reload guard | Closed |
| 12 | Simulated | ATM master | ATM037 closed on 15 May 2026; demand moves to ATM036 (same station) | ATM036 under-forecast (MAPE 33%) | Transfer rule (MAPE 15%); feature `neighbour_closed` | Closed |
| 13 | Simulated | ATM feed | Festival in July (x2.6 on 4 ATMs) | Extreme values | Kept; `local_event` feature from the events calendar | Closed |
| 14 | Simulated | ATM feed | 9 isolated spikes > 2.5x the weekday median | Unknown | Sent to the branch network for review; not removed | Open |
| 15 | Simulated | Monitoring | Rural over-forecast of about 6% in early September | Short alert | Add an end-of-summer feature | Open |
