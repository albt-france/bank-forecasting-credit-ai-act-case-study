# Model card: credit default scorecard

*Study model on public data. Not for use on real clients. Not legal advice.*

| Item | Content |
|---|---|
| Model | Logistic regression on 6 binned inputs, shown as a points scorecard (PDO 20, 600 points at odds 50:1) |
| Challenger | `HistGradientBoostingClassifier` on all behavioural inputs |
| Version | 1.0, code `src/credit_default_model.py`, seed 42 |
| Owner (in a bank) | Credit risk modelling team; validation by an independent model-risk team |

## Intended use

- Estimate the probability that a credit-card client defaults on next month's payment.
- Support a decision (accept / decline, or limit review) at a cost-based cut-off, **with a person reviewing every decline**.
- **Out of scope**: fully automated decisions; pricing; any use on clients outside the population the model was trained on.

## Data

- **UCI Default of Credit Card Clients** (id 350, CC BY 4.0): 30,000 credit-card clients in **Taiwan, 2005** (April-September statements). Not Belgian clients.
- Target: default payment next month (22.1% of clients).
- Split: 70% training / 30% test, stratified (9,000 test clients).
- **Inputs (6)**: months late in the last 5, repayment status last month, credit limit, utilisation of the limit, share of the bill paid, bill trend over 5 months.
- **Not inputs**: sex, age, marital status (sensitive, used only to measure fairness in aggregates of 5 or more) and education (possible proxy, left out by choice).

## Performance (test set)

| Metric | Scorecard | Challenger (boosting) |
|---|---|---|
| AUC | 0.754 | 0.775 |
| Gini | 0.51 | 0.55 |
| KS | 0.40 | 0.42 |
| Brier score | 0.139 | 0.136 |

Reference: Brier 0.172 if every client gets the average rate. The challenger gains 0.02 AUC; the scorecard is kept because it can be read and explained point by point.

## Calibration

Over 10 groups of 900 clients, predicted and observed default rates differ by **at most 2 points**. The probabilities can be used as such for expected-loss calculations, after recalibration on the bank's own data.

## Decision cut-off

- Assumed costs: a missed default (bad client accepted) = 5, a good client declined = 1.
- Best cut-off on the test set: **0.15** (theory: 1 / (1 + 5) = 0.167). Acceptance 60%.
- Expected cost per client: 0.59 at 0.15, 0.77 at 0.50, 1.11 if everyone is accepted.
- The costs are business assumptions: the cut-off must be re-derived once the bank sets them.

## What drives the score

Permutation importance (AUC lost when one input is shuffled): months late in the last 5 (0.083), repayment status last month (0.041), credit limit (0.016), utilisation (0.007), bill trend (0.003), share of the bill paid (0.001). Partial effect of last month's repayment status (average predicted default when every test client is set to that status): revolving credit used normally 17%, paid in full 22%, 1 month late 20%, **2 months late 44%**, 3 months or more 39% (few clients). Being 2 months late is the clear jump; the effect is not strictly monotonic, which a reviewer should know.

## Fairness (aggregates, test set)

| Group | n | Observed default | Accepted | Good clients declined |
|---|---|---|---|---|
| Women | 5,437 | 21.0% | 61.4% | 30.9% |
| Men | 3,563 | 23.9% | 59.0% | 32.0% |
| Under 30 | 2,882 | 22.4% | 56.0% | 35.5% |
| 30-39 | 3,332 | 19.8% | 64.2% | 28.3% |
| 40-49 | 1,958 | 23.9% | 61.7% | 29.6% |
| 50 and over | 828 | 26.0% | 57.9% | 33.3% |

- Ratio of lowest to highest acceptance by age: 0.87.
- **To review**: good payers under 30 are declined more often (35.5%) than those aged 30-39 (28.3%), while their observed default rates are close (22.4% vs 19.8%). A deployer would analyse this before use (AI Act Art. 10 and 27).
- Smallest group: 828 clients. No group below 5 is ever shown.

## Stability

PSI of the score: **0.04** between the August and September 2005 windows (rebuilt from the dataset's own history: stable), **0.17** under a SIMULATED stress (30% of clients one month later on their last two payments: "watch" zone, 0.10-0.25).

## Limits

- Old, foreign, card-only data: the model shows the method, not Belgian risk levels.
- Behavioural inputs only; no income, no bureau data; no reject inference (only accepted clients are observed).
- Costs are assumptions.

## Monitoring (in production)

Monthly: PSI of the score and of each input (watch > 0.10, act > 0.25); calibration by score band; acceptance and decline rates by sex and age band; override rate of human reviewers. See `monitoring_runbook.md`.
