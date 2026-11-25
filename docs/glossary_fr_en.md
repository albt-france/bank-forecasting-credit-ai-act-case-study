# Glossary (English - French)

| English | Français | In one line |
|---|---|---|
| Forecast | Prévision | An estimate of a future value, with its uncertainty |
| Backtest (rolling origin) | Backtest (origine glissante) | Re-running the forecast at past dates, using only data known then, and comparing with what happened |
| Horizon | Horizon | How far ahead the forecast goes (1 to 12 months) |
| MAPE | MAPE (erreur absolue moyenne en %) | Average error as a percentage of the actual value |
| MASE | MASE | Error divided by the error of a simple naive rule; below 1 means better than the rule |
| Prediction interval | Intervalle de prévision | Range that should contain the actual value 80% or 95% of the time |
| Seasonal naive | Prévision naïve saisonnière | "Same as the same month last year" |
| Exogenous variable | Variable exogène | An outside input to the model, here the mortgage rate |
| Structural break | Rupture (cassure) | A date after which a series behaves differently |
| Scenario | Scénario | A "what if" input path, not a forecast |
| Information leak | Fuite d'information | Using data that would not be known at decision time |
| Cumulative gain | Gain cumulé | Share of positives reached when calling the best-scored clients first |
| Lift | Lift (gain par rapport au hasard) | How many times better than random calls |
| AUC / Gini | AUC / Gini | Ranking quality; Gini = 2 x AUC - 1 |
| KS | KS (Kolmogorov-Smirnov) | Largest gap between the score distributions of good and bad clients |
| Calibration | Calibration | Predicted probabilities match observed rates |
| Brier score | Score de Brier | Average squared error of predicted probabilities |
| Cut-off | Seuil de décision | Probability above which a client is declined |
| Cost matrix | Matrice de coûts | Cost of each type of error, used to choose the cut-off |
| Scorecard | Grille de score | Points per variable band; the total gives the risk |
| Permutation importance | Importance par permutation | Accuracy lost when one input is shuffled |
| PSI | PSI (indice de stabilité de population) | How much a distribution moved between two periods |
| Fairness | Équité | Comparing outcomes between groups (sex, age) |
| Drift | Dérive | The relation between inputs and outcome changes over time |
| CUSUM | CUSUM (somme cumulée) | Running sum of errors that flags a persistent shift |
| Data contract | Contrat de données | Written agreement on schema, keys, freshness and who fixes what |
| Staging | Zone de préparation (staging) | Cleaned, deduplicated copy of raw data |
| Simpson's paradox | Paradoxe de Simpson | A trend that reverses when groups are combined |
| High-risk AI system | Système d'IA à haut risque | AI Act category that includes credit scoring (Annex III 5(b)) |
| Human oversight | Contrôle humain | A person can understand, check and override the system |
| Model card | Fiche de modèle | One document: use, data, performance, limits, owner |
| Fundamental rights impact assessment | Analyse d'impact sur les droits fondamentaux | Assessment required from some deployers before use (Art. 27) |
