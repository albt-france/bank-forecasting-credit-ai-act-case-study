"""PUBLIC DATA: UCI Default of Credit Card Clients (id 350, CC BY 4.0) - 30,000 credit-card clients in Taiwan, 2005.
A credit-default model you can explain: an interpretable logistic scorecard and a gradient-boosting challenger.

- Inputs: credit line, repayment status, bills and payments of the last 6 months (+ 4 derived ratios).
  NOT inputs: sex, age, marital status (sensitive, used only to measure fairness, in aggregates of 5 or more) and
  education (possible proxy, left out by choice).
- Metrics: AUC, Gini, KS; calibration (reliability curve, Brier); cost-based cut-off (assumed cost matrix);
  permutation importance and partial effect; fairness by sex and age band (sql/06); score stability (PSI).
    python src/credit_default_model.py
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score, roc_curve
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder

from common import PROC, RAW, save_findings
import run_sql

COST_BAD_ACCEPTED, COST_GOOD_DECLINED = 5.0, 1.0      # assumption: a missed default costs 5x a lost good client
PDO, BASE_SCORE, BASE_ODDS = 20, 600, 50              # scorecard scaling: +20 points doubles the odds good:bad
PAY = ["PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6"]
BILL = [f"BILL_AMT{i}" for i in range(1, 7)]
PAYAMT = [f"PAY_AMT{i}" for i in range(1, 7)]


def features(d, shift=0):
    """Derived inputs; shift=1 rebuilds them one month earlier (Aug 2005 window) from the dataset's own history."""
    pay, bill, pam = PAY[shift:shift + 5], BILL[shift:shift + 5], PAYAMT[shift:shift + 5]
    f = pd.DataFrame(index=d.index)
    f["LIMIT_BAL"] = d.LIMIT_BAL
    f["status_last"] = d[pay[0]]
    f["months_late_5m"] = (d[pay] > 0).sum(axis=1)
    f["max_delay_5m"] = d[pay].max(axis=1)
    f["utilisation"] = (d[bill[0]] / d.LIMIT_BAL).clip(-0.5, 2)
    f["paid_ratio"] = (d[pam[0]] / d[bill[0]].where(d[bill[0]] > 0)).clip(0, 2).fillna(1)
    f["bill_trend"] = ((d[bill[0]] - d[bill[-1]]) / d.LIMIT_BAL).clip(-1, 1)
    f["avg_payment"] = d[pam].mean(axis=1)
    return f


BINS = {"status_last": [-10, -1, 0, 1, 2, 10], "months_late_5m": [-1, 0, 1, 2, 5],
        "utilisation": [-10, 0.1, 0.4, 0.7, 0.9, 10], "paid_ratio": [-1, 0.02, 0.05, 0.2, 10],
        "LIMIT_BAL": [0, 50e3, 100e3, 200e3, 360e3, 1e7], "bill_trend": [-10, -0.1, 0.05, 0.2, 10]}


def binned(f):
    return pd.DataFrame({c: pd.cut(f[c], b).astype(str) for c, b in BINS.items()}, index=f.index)


def ks(y, s):
    fpr, tpr, _ = roc_curve(y, s)
    return float(np.max(tpr - fpr))


def psi(a, b, bins=10):
    edges = np.unique(np.quantile(a, np.linspace(0, 1, bins + 1)))
    edges[0], edges[-1] = -np.inf, np.inf
    pa = np.histogram(a, edges)[0] / len(a)
    pb = np.histogram(b, edges)[0] / len(b)
    pa, pb = np.clip(pa, 1e-6, None), np.clip(pb, 1e-6, None)
    return float(((pb - pa) * np.log(pb / pa)).sum())


def main():
    d = pd.read_parquet(RAW / "credit_default.parquet").rename(columns={"default payment next month": "y"})
    f = features(d)
    tr_i, te_i = train_test_split(d.index, test_size=0.3, stratify=d.y, random_state=42)
    y_tr, y_te = d.y[tr_i].values, d.y[te_i].values
    # 1. logistic scorecard on binned inputs
    lr = make_pipeline(OneHotEncoder(handle_unknown="ignore", drop=None), LogisticRegression(C=0.5, max_iter=3000))
    xb = binned(f)
    lr.fit(xb.loc[tr_i], y_tr)
    p_lr = lr.predict_proba(xb.loc[te_i])[:, 1]
    # 2. challenger: gradient boosting on all behavioural inputs
    xg = pd.concat([f, d[PAY + BILL + PAYAMT]], axis=1)
    gb = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=31, random_state=42)
    gb.fit(xg.loc[tr_i], y_tr)
    p_gb = gb.predict_proba(xg.loc[te_i])[:, 1]
    comp = []
    for name, p in (("Logistic scorecard", p_lr), ("Gradient boosting", p_gb)):
        auc = roc_auc_score(y_te, p)
        comp.append({"model": name, "auc": auc, "gini": 2 * auc - 1, "ks": ks(y_te, p), "brier": brier_score_loss(y_te, p)})
    comp = pd.DataFrame(comp)
    comp.to_csv(PROC / "credit_model_comparison.csv", index=False)
    print(comp.round(3).to_string(index=False))
    # calibration (10 equal-size bins)
    cal = []
    for name, p in (("Logistic scorecard", p_lr), ("Gradient boosting", p_gb)):
        q = pd.qcut(p, 10, labels=False, duplicates="drop")
        g = pd.DataFrame({"p": p, "y": y_te, "bin": q}).groupby("bin").agg(predicted=("p", "mean"), observed=("y", "mean"), n=("y", "size"))
        cal.append(g.reset_index().assign(model=name))
    cal = pd.concat(cal)
    cal.to_csv(PROC / "credit_calibration.csv", index=False)
    # scorecard points
    enc, clf = lr.named_steps["onehotencoder"], lr.named_steps["logisticregression"]
    factor = PDO / np.log(2)
    offset = BASE_SCORE - factor * np.log(BASE_ODDS)
    names = enc.get_feature_names_out(list(BINS))
    n_var = len(BINS)
    sc = pd.DataFrame({"term": names, "coef": clf.coef_[0]})
    sc["variable"] = [next(v for v in BINS if t.startswith(v + "_")) for t in sc.term]
    sc["bin"] = [t[len(v) + 1:] for t, v in zip(sc.term, sc.variable)]
    sc["points"] = (-(sc.coef) * factor + (offset - clf.intercept_[0] * factor) / n_var).round().astype(int)
    sc[["variable", "bin", "points"]].to_csv(PROC / "credit_scorecard.csv", index=False)
    # cost-based cut-off on the final (logistic) model
    th = np.round(np.arange(0.05, 0.71, 0.01), 2)
    cost = [(COST_BAD_ACCEPTED * ((p_lr < t) & (y_te == 1)).sum() + COST_GOOD_DECLINED * ((p_lr >= t) & (y_te == 0)).sum()) / len(y_te) for t in th]
    cc = pd.DataFrame({"threshold": th, "cost_per_applicant": cost,
                       "acceptance_rate": [(p_lr < t).mean() for t in th]})
    cc.to_csv(PROC / "credit_cost_curve.csv", index=False)
    t_best = float(cc.loc[cc.cost_per_applicant.idxmin(), "threshold"])
    t_theory = COST_GOOD_DECLINED / (COST_GOOD_DECLINED + COST_BAD_ACCEPTED)
    cost_at = lambda t: float(cc.loc[(cc.threshold - t).abs().idxmin(), "cost_per_applicant"])
    accept_all = COST_BAD_ACCEPTED * y_te.mean()
    # permutation importance (AUC drop) of the final model, on the binned inputs
    pi = permutation_importance(lr, xb.loc[te_i], y_te, scoring="roc_auc", n_repeats=5, random_state=42)
    imp = pd.DataFrame({"variable": list(BINS), "auc_drop": pi.importances_mean}).sort_values("auc_drop", ascending=False)
    imp.to_csv(PROC / "credit_importance.csv", index=False)
    # partial effect: average predicted PD when every client is set to each repayment-status bin
    pe = []
    for b in sorted(xb.status_last.unique(), key=lambda s: float(s.split(",")[0][1:])):
        x2 = xb.loc[te_i].copy(); x2["status_last"] = b
        pe.append({"status_last_bin": b, "mean_pd": float(lr.predict_proba(x2)[:, 1].mean())})
    pd.DataFrame(pe).to_csv(PROC / "credit_partial_status.csv", index=False)
    # scored test set for fairness (local only, never published: row level)
    te = d.loc[te_i]
    age_band = pd.cut(te.AGE, [0, 29, 39, 49, 200], labels=["<30", "30-39", "40-49", "50+"]).astype(str)
    pd.DataFrame({"sex": te.SEX.map({1: "male", 2: "female"}).values, "age_band": age_band.values,
                  "default_next_month": y_te, "pd_model": p_lr,
                  "decision": np.where(p_lr >= t_best, "decline", "accept")}).to_parquet(PROC / "credit_scores.parquet", index=False)
    pd.DataFrame({"feature": list(BINS)}).to_csv(PROC / "credit_final_features.csv", index=False)
    # stability: PSI of the score between the Aug 2005 window (rebuilt from history) and Sept 2005, plus a SIMULATED stress
    s_sep = lr.predict_proba(binned(features(d)))[:, 1]
    s_aug = lr.predict_proba(binned(features(d, shift=1)))[:, 1]
    rng = np.random.default_rng(42)
    ds = d.copy()
    hit = rng.random(len(ds)) < 0.30                     # SIMULATED stress: 30% of clients late in the last 2 months
    for c in ("PAY_0", "PAY_2"):
        ds.loc[hit, c] = ds.loc[hit, c].clip(lower=0) + 1
    ds["BILL_AMT1"] = ds.BILL_AMT1.astype(float)
    ds.loc[hit, "BILL_AMT1"] = ds.loc[hit, "BILL_AMT1"] * 1.2
    s_stress = lr.predict_proba(binned(features(ds)))[:, 1]
    psis = {"aug_vs_sep_2005": psi(s_aug, s_sep), "simulated_stress": psi(s_sep, s_stress)}
    run_sql.run_all(verbose=False)
    fair = pd.read_csv(PROC / "credit_fairness.csv")
    fs = fair[fair.attribute == "sex"].set_index("grp")
    fa = fair[fair.attribute == "age band"].set_index("grp")
    m = comp.set_index("model")
    cal_lr = cal[cal.model == "Logistic scorecard"]
    save_findings("credit", {
        "n_clients": int(len(d)), "n_test": int(len(te_i)), "default_rate": float(d.y.mean()),
        "auc_lr": m.loc["Logistic scorecard", "auc"], "gini_lr": m.loc["Logistic scorecard", "gini"], "ks_lr": m.loc["Logistic scorecard", "ks"],
        "brier_lr": m.loc["Logistic scorecard", "brier"],
        "auc_gb": m.loc["Gradient boosting", "auc"], "gini_gb": m.loc["Gradient boosting", "gini"], "ks_gb": m.loc["Gradient boosting", "ks"],
        "brier_gb": m.loc["Gradient boosting", "brier"],
        "brier_base": float(brier_score_loss(y_te, np.full(len(y_te), y_tr.mean()))),
        "cal_max_gap": float((cal_lr.predicted - cal_lr.observed).abs().max()),
        "cost_bad": COST_BAD_ACCEPTED, "cost_good": COST_GOOD_DECLINED, "threshold_best": t_best, "threshold_theory": t_theory,
        "cost_best": cost_at(t_best), "cost_at_050": cost_at(0.5), "cost_accept_all": float(accept_all),
        "acceptance_at_best": float(cc.loc[cc.threshold == t_best, "acceptance_rate"].iloc[0]),
        "top_variable": imp.variable.iloc[0], "top_auc_drop": float(imp.auc_drop.iloc[0]),
        "psi_aug_sep": psis["aug_vs_sep_2005"], "psi_stress": psis["simulated_stress"],
        "acc_male": float(fs.loc["male", "acceptance_rate"]), "acc_female": float(fs.loc["female", "acceptance_rate"]),
        "def_male": float(fs.loc["male", "observed_default_rate"]), "def_female": float(fs.loc["female", "observed_default_rate"]),
        "gd_male": float(fs.loc["male", "good_declined_rate"]), "gd_female": float(fs.loc["female", "good_declined_rate"]),
        "acc_by_age": {k: float(v) for k, v in fa.acceptance_rate.items()},
        "gd_by_age": {k: float(v) for k, v in fa.good_declined_rate.items()},
        "def_by_age": {k: float(v) for k, v in fa.observed_default_rate.items()},
        "min_group_n": int(fair.n.min()),
        "scorecard_points_range": [int(sc.groupby("variable").points.min().sum()), int(sc.groupby("variable").points.max().sum())],
    })
    print(f"cut-off {t_best} (theory {t_theory:.3f}); cost/applicant {cost_at(t_best):.3f} vs 0.5 cut-off {cost_at(0.5):.3f} vs accept all {accept_all:.3f}")
    print("PSI", {k: round(v, 3) for k, v in psis.items()}, "| top variable", imp.variable.iloc[0])
    print(fair.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
