# Decision memo: three questions, three answers

*One page for decision-makers. Public data (ECB, UCI) and a simulated ATM network of a fictitious "Bank B". Data read on 25 Nov 2026.*

## 1. How many new mortgages should we plan for next year?

**Answer.** If the mortgage rate stays at 3.76%, about **€41.8 bn** of new mortgages in Belgium over the next 12 months, the same as the last 12 months (€41.7 bn). If rates fall by half a point, about €51.7 bn; if they rise by half a point, about €33.8 bn.

**How sure are we?** Tested on 12 past starting points, the forecast was off by **8.4%** on average, up to a year ahead, against 15.0% for "same month last year". Rates clearly move volumes, but by how much is uncertain: plan with ranges, not one number.

**What we don't know.** Sudden changes, like the turn in household deposits around 2021-10 (peak €136.1 bn in 2022-06, €108.7 bn in 2026-09), cannot be forecast. Rate decisions are scenarios, not forecasts.

## 2. Who should our next term-deposit campaign call?

**Answer.** Score the clients and call the **top 20%** first: they hold **66%** of the clients who say yes (3.3 times better than random calls). Start with clients who said yes to a past campaign and with mobile numbers; stop after 3-4 calls.

**How sure are we?** Tested on 8,237 calls the model had never seen. We did not use the length of the call: it is only known after the call, and using it would make the model look far better than it can be.

**What we don't know.** The data comes from a Portuguese bank (2008-2010). The method transfers; the rates must be re-measured on our own campaigns, and the model retrained before each one.

## 3. Who is likely to default, and can we defend the decision?

**Answer.** A simple points-based scorecard ranks clients well (AUC 0.75) and its probabilities are honest: when it says 20%, about 20% default. With our assumed costs (a missed default costs 5 times a lost good client), the best cut-off is **15%**, not the usual 50%: expected cost per client falls by 23%.

**How sure are we?** Tested on 9,000 clients. Men and women are accepted at similar rates (59% and 61%); younger clients are accepted less often (56% under 30 vs 64% for 30-39), which needs a review. Sex and age are not used by the model.

**What we don't know.** The data is from Taiwan (2005). Under the EU AI Act, credit scoring is **high-risk**: before any real use we need logs, a person reviewing declines, an impact assessment and a legal review. *Not legal advice.*

## What we ask you to decide

1. Plan mortgage volumes on the three rate scenarios.
2. Pilot score-based calling on one campaign, with a control group.
3. Agree the cost of a missed default and of a lost client, so the cut-off reflects the bank's real trade-off.
4. Name an owner for the data contract with the data engineers and for model monitoring.

---

## Presenter script (3 minutes, pages 0 and 4 of the report)

- **(0:00) The ask.** "Three questions: how much will we lend, who do we call, who may default. For each: an answer, how sure we are, what we don't know."
- **(0:30) Credit, the result.** "A points table a credit officer can read. It ranks clients well: AUC 0.75. A fancier model gains only 0.02."
- **(1:00) Calibration.** "When it says 20%, about 20% default. That matters more than ranking when we price or provision."
- **(1:30) The cut-off.** "50% is a habit, not a decision. If a missed default costs five times a lost client, the best cut-off is 15%. Cost per client: minus 23%. You set the costs; the cut-off follows."
- **(2:00) Fairness.** "Sex and age are not inputs, but we measure the outcome: men and women are treated alike; good payers under 30 are declined more often than those aged 30-39, for close default rates. We flag it, we don't hide it."
- **(2:30) AI Act.** "Credit scoring is high-risk under Annex III. The model card and the checklist list what we have and what is missing: logs, human review of declines, an impact assessment. Not legal advice."
- **(2:50) Close.** "Decide the costs, name the owner, and we can pilot."
