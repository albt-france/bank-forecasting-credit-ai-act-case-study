# EU AI Act checklist for the credit default model

**This is not legal advice.** It is a data scientist's working checklist, built from the text of **Regulation (EU) 2024/1689** (the AI Act), read on 25 Nov 2026 from the EU Publications Office (`https://publications.europa.eu/resource/celex/32024R1689`). Article titles below are quoted from that text. Later amendments to the Regulation were not checked.

## Why the credit model is high-risk

- **Recital 58**: "AI systems used to evaluate the credit score or creditworthiness of natural persons should be classified as high-risk AI systems".
- **Annex III, point 5(b)**: "AI systems intended to be used to evaluate the creditworthiness of natural persons or establish their credit score, with the exception of AI systems used for the purpose of detecting financial fraud".
- **Article 6(2)**: systems listed in Annex III are high-risk (with the derogations of Article 6(3), which this study does not rely on).
- **Article 113**: "It shall apply from 2 August 2026", with the exceptions listed in that article.
- Open question for legal: whether a simple logistic scorecard meets the definition of an "AI system" (Article 3(1)). This study takes the prudent view and treats it as in scope.

## Obligations, what the study covers, what is missing

| Article | Title in the text | What this study covers | What is missing for a real launch |
|---|---|---|---|
| Art. 9 | Risk management system | Risks listed in the model card: drift, unfair outcomes, misuse of the cut-off, use outside the training population | A formal risk register with owners, mitigations and a review cycle over the whole life of the system |
| Art. 10 | Data and data governance | Source, licence and split documented; sensitive attributes excluded from inputs; outcome checked by sex and age in aggregates | Bank's own applicant data; representativeness for the Belgian population; bias examination and data-quality criteria agreed with data owners |
| Art. 11 | Technical documentation | Model card, code, backtest, scorecard table, this checklist | The full technical documentation of Annex IV, kept up to date; data and model versioning |
| Art. 12 | Record-keeping | Not covered (study) | Automatic logs of each scoring event: inputs, score, decision, reviewer, override |
| Art. 13 | Transparency and provision of information to deployers | Plain-language decision memo, intended use, limits, performance | Instructions for use for the deploying team (accuracy, known limits, human-oversight measures) |
| Art. 14 | Human oversight | Design choice: a person reviews every decline; the cut-off is set by business costs, not by the model | Override process, reviewer training, monitoring of override rates, ability to stop the system |
| Art. 15 | Accuracy, robustness and cybersecurity | AUC, Gini, KS, calibration, PSI under a simulated stress | Declared accuracy levels; robustness tests on real data; security review of the scoring service |
| Art. 17 | Quality management system | Code, tests and reproducible runs | Provider's quality management system (procedures, responsibilities, change control) |
| Art. 26 | Obligations of deployers of high-risk AI systems | Monitoring runbook (drift, calibration, fairness) | Use according to instructions, input-data relevance, log retention, informing affected persons |
| Art. 27 | Fundamental rights impact assessment for high-risk AI systems | Fairness metrics usable as an input | An impact assessment by the deployer before first use (Art. 27(1) names Annex III point 5(b)) |
| Art. 43 / 49 | Conformity assessment; Registration | Not covered | Conformity assessment and registration steps as they apply to the provider |
| Art. 72 | Post-market monitoring by providers and post-market monitoring plan for high-risk AI systems | PSI and drift monitor, thresholds, retraining rules | A written post-market monitoring plan |
| Art. 86 | Right to explanation of individual decision-making | Points per variable make each score explainable | A process and template to give clients a clear explanation of the role of the system in the decision |

## Next steps (in order)

1. Legal and compliance confirm scope and role (provider and/or deployer).
2. Rebuild the model on the bank's own data with the data engineers (data contract, lineage).
3. Write the Annex IV technical documentation and the instructions for use.
4. Put logging and human review in the scoring service.
5. Run the fundamental-rights impact assessment; review the under-30 decline gap.
6. Approve the post-market monitoring plan and the retraining rules.
