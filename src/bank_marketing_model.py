"""PUBLIC DATA: UCI Bank Marketing (id 222, CC BY 4.0) - phone campaigns of a Portuguese bank, May 2008 - Nov 2010,
41,188 calls. Who to call for a term deposit, without cheating.

- 'duration' (length of the call) is only known AFTER the call: it is excluded from the final model; a second model with
  it shows how much it inflates the score (information leak).
- Age and marital status are sensitive: not model inputs; used only to measure selection rates in aggregates (n >= 5).
- Models: logistic regression and HistGradientBoosting; stratified random 80/20 split (main result) and an out-of-time
  check (the file is in call order: train on the first 80%, test on the last 20%, when the economic context had changed).
- Output: cumulative gain curve, lift vs random targeting, business segments (sql/05).
    python src/bank_marketing_model.py
"""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

from common import PROC, RAW, save_findings
import run_sql

SENSITIVE = ["age", "marital"]
CAT = ["job", "education", "default", "housing", "loan", "contact", "month", "day_of_week", "poutcome"]
NUM = ["campaign", "pdays", "previous", "emp.var.rate", "cons.price.idx", "cons.conf.idx", "euribor3m", "nr.employed"]


def models(num, cat):
    lr = make_pipeline(ColumnTransformer([("n", StandardScaler(), num), ("c", OneHotEncoder(handle_unknown="ignore"), cat)]),
                       LogisticRegression(max_iter=2000))
    gb = make_pipeline(ColumnTransformer([("n", "passthrough", num),
                                          ("c", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1), cat)]),
                       HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, categorical_features=list(range(len(num), len(num) + len(cat))),
                                                      random_state=42))
    return {"Logistic": lr, "Gradient boosting": gb}


def gain_curve(y, s, steps=100):
    order = np.argsort(-s)
    cum = np.cumsum(y[order]) / y.sum()
    k = np.linspace(0, 1, steps + 1)
    return k, np.concatenate([[0], cum[(np.maximum(k[1:] * len(y), 1)).astype(int) - 1]])


def main():
    d = pd.read_parquet(RAW / "bank_marketing.parquet")
    d["target"] = (d.y == "yes").astype(int)
    d["pdays"] = d.pdays.replace(999, -1)           # 999 = never contacted before
    n_test = int(len(d) * 0.2)
    oot = {}
    for name, m in models(NUM, CAT).items():          # out-of-time robustness check
        m.fit(d.iloc[:-n_test][NUM + CAT], d.iloc[:-n_test].target)
        oot[name] = roc_auc_score(d.iloc[-n_test:].target, m.predict_proba(d.iloc[-n_test:][NUM + CAT])[:, 1])
    tr, te = train_test_split(d, test_size=0.2, stratify=d.target, random_state=42)
    res, scores = [], {}
    for feats, label in ((NUM, "without duration"), (NUM + ["duration"], "with duration (leak)")):
        for name, m in models(feats, CAT).items():
            m.fit(tr[feats + CAT], tr.target)
            s = m.predict_proba(te[feats + CAT])[:, 1]
            auc = roc_auc_score(te.target, s)
            res.append({"model": name, "features": label, "auc": auc})
            scores[(name, label)] = s
    res = pd.DataFrame(res)
    res.to_csv(PROC / "bm_model_comparison.csv", index=False)
    print(res.round(3).to_string(index=False))
    final_name = res[res.features == "without duration"].sort_values("auc").iloc[-1].model
    s = scores[(final_name, "without duration")]
    y = te.target.values
    k, g = gain_curve(y, s)
    _, g_leak = gain_curve(y, scores[(final_name, "with duration (leak)")])
    gc = pd.DataFrame({"share_called": k, "share_subscribers_found": g, "with_duration_leak": g_leak})
    gc.to_csv(PROC / "bm_gain.csv", index=False)
    top = lambda q: float(np.interp(q, k, g))
    # selection rate by age band at a 20% call budget (fairness check, aggregates only)
    te = te.assign(score=s, selected=s >= np.quantile(s, 0.8),
                   age_band=pd.cut(te.age, [0, 29, 39, 49, 59, 200], labels=["<30", "30-39", "40-49", "50-59", "60+"]))
    fair = te.groupby("age_band", observed=True).agg(n=("target", "size"), subscription_rate=("target", "mean"),
                                                     selected_rate=("selected", "mean")).reset_index()
    fair = fair[fair.n >= 5]
    fair.to_csv(PROC / "bm_fairness_age.csv", index=False)
    pd.DataFrame({"feature": NUM + CAT}).to_csv(PROC / "bm_final_features.csv", index=False)
    base = y.mean()
    prec20 = te.loc[te.selected, "target"].mean()
    leak = res.set_index(["model", "features"]).auc
    save_findings("marketing", {
        "n_calls": int(len(d)), "n_test": int(n_test), "base_rate_all": float(d.target.mean()), "base_rate_test": float(base),
        "final_model": final_name, "auc_final": float(leak[(final_name, "without duration")]),
        "auc_with_duration": float(leak[(final_name, "with duration (leak)")]),
        "auc_logistic": float(leak[("Logistic", "without duration")]), "auc_gb": float(leak[("Gradient boosting", "without duration")]),
        "gain_top10": top(0.1), "gain_top20": top(0.2), "gain_top30": top(0.3),
        "lift_top20": top(0.2) / 0.2, "precision_top20": float(prec20),
        "auc_oot_logistic": float(oot["Logistic"]), "auc_oot_gb": float(oot["Gradient boosting"]),
        "base_rate_oot": float(d.iloc[-n_test:].target.mean()),
    })
    run_sql.run_all(verbose=False)
    print(f"final {final_name}: top 20% of calls finds {top(0.2):.0%} of subscribers (lift {top(0.2) / 0.2:.1f}x); base rate test {base:.1%}")


if __name__ == "__main__":
    main()
