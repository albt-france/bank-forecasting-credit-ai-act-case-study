"""SIMULATED: 7-day-ahead cash demand forecast for the 60 ATMs of the fictitious "Bank B", from staged data (sql/01-02).

- Global model: HistGradientBoosting on log demand with calendar, Belgian public holidays, local events, lags >= 7 days,
  ATM, region and site type. Reference: seasonal naive per ATM (same weekday last week).
- Validation: rolling origin, weekly origins Jan-Aug 2026, horizons 1-7 days. A first version with a random day split
  is kept to show why it is wrong (it mixes future and past).
- Decommissioned ATM037: its station neighbour ATM036 gets a transfer adjustment until the lags catch up.
- Production (Sept-Oct 2026): model frozen on 31 Aug; error monitored by segment (rolling 7-day MAPE, CUSUM).
- Refill policy: fixed (Mon + Thu) vs forecast-driven, with the assumed costs of data/sim/refill_costs.
    python src/atm_forecast.py
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from common import PROC, SIM, save_findings
import run_sql

FEATS = ["atm", "reg", "site", "dow", "dom", "month", "start_of_month", "holiday", "pre_christmas", "local_event",
         "neighbour_closed", "lag7", "lag14", "mean_7_13", "mean_7_34"]
CAT_IDX = [0, 1, 2]
CLOSE, PROD_START, BT_START = pd.Timestamp("2026-05-15"), pd.Timestamp("2026-09-01"), pd.Timestamp("2026-01-05")
TRANSFER_SHARE = 0.5          # assumption given to the network team: half of a closed ATM's demand moves next door


def load():
    f = pd.read_parquet(PROC / "atm_features.parquet")
    f["date"] = pd.to_datetime(f.date)
    for c, n in (("atm_id", "atm"), ("region", "reg"), ("site_type", "site")):
        f[n] = f[c].astype("category").cat.codes
    f["lag1"] = f.groupby("atm_id").y.shift(1)        # only used by the flawed first version (not known 7 days ahead)
    return f


def model():
    return HistGradientBoostingRegressor(max_iter=250, learning_rate=0.06, max_leaf_nodes=31, min_samples_leaf=10,
                                         categorical_features=CAT_IDX, random_state=42)


def fit(tr):
    tr = tr[tr.y.notna() & (tr.y > 0) & tr.lag7.notna()]
    return model().fit(tr[FEATS], np.log(tr.y))


def transfer_adjustment(f, pred):
    """Add part of ATM037's last known level to ATM036 forecasts, fading out as the lags absorb the move."""
    lvl37 = f[(f.atm_id == "ATM037") & (f.date < CLOSE)].tail(28).y.mean()
    days = (pred.date - CLOSE).dt.days
    w = np.where(days < 7, 1.0, np.clip((35 - days) / 28, 0, 1))
    m = (pred.atm_id == "ATM036") & (days >= 0)
    return np.where(m, w * TRANSFER_SHARE * lvl37, 0.0)


def rolling_backtest(f, origins, frozen=None):
    out = []
    for o in origins:
        te = f[(f.date >= o) & (f.date < o + pd.Timedelta(days=7))].copy()
        m = frozen or fit(f[f.date < o])
        te["pred_model_raw"] = np.exp(m.predict(te[FEATS]))
        te["origin"], te["horizon"] = o, (te.date - o).dt.days + 1
        out.append(te)
    bt = pd.concat(out, ignore_index=True)
    bt["transfer_adj"] = transfer_adjustment(f, bt)
    bt["pred_model"] = bt.pred_model_raw + bt.transfer_adj
    bt["pred_naive"] = bt.lag7
    return bt


def cusum_lower(e, mu, sd, k=1.0, h=5.0):
    """One-sided CUSUM for a fall in demand: e = (actual - forecast) / forecast, standardised with backtest mean/sd."""
    s, out = 0.0, []
    for x in (e - mu) / sd:
        s = max(0.0, s - x - k)
        out.append(s)
    return np.array(out), h


def refill_policy(df, cap, visit_cost, oos_cost, hold_cost_yr, mode, q95=1.3):
    """Simulate one ATM on actual demand. mode: 'fixed' (Mon/Thu + emergency below 20%) or 'forecast'."""
    bal, visits, oos_h, hold = cap, 0, 0.0, 0.0
    dem, pred, dow = df.y.fillna(df.pred_model).values, df.pred_model.values, df.date.dt.dayofweek.values
    for i in range(len(df)):
        if mode == "fixed":
            need = dow[i] in (0, 3) or bal < 0.2 * cap
        else:
            need = bal < q95 * pred[i]                       # not enough cash for today at the 95% level
        if need:
            bal, visits = cap, visits + 1
        if dem[i] > bal:
            oos_h += 24 * (1 - bal / dem[i])
            bal = 0.0
        else:
            bal -= dem[i]
        hold += bal * hold_cost_yr / 365
    return visits, oos_h, visits * visit_cost + oos_h * oos_cost + hold


def mape(a, p):
    m = (a > 0) & np.isfinite(p)
    return float(np.mean(np.abs(a[m] - p[m]) / a[m]))


def main():
    f = load()
    origins = pd.date_range(BT_START, PROD_START - pd.Timedelta(days=7), freq="7D")
    bt = rolling_backtest(f, origins)
    ok = bt.y.notna() & (bt.y > 0)
    bt.loc[:, ["date", "atm_id", "region", "site_type", "origin", "horizon", "y", "pred_model", "pred_model_raw", "pred_naive",
               "holiday", "local_event"]].to_parquet(PROC / "atm_backtest.parquet", index=False)
    m_model, m_naive = mape(bt.y[ok].values, bt.pred_model[ok].values), mape(bt.y[ok].values, bt.pred_naive[ok].values)
    # event 8: first version, random split of days (leaks the future)
    pool = f[(f.date < PROD_START) & f.y.notna() & (f.y > 0) & f.lag7.notna()]
    days = pool.date.unique()
    rng = np.random.default_rng(42)
    test_days = rng.choice(days, int(len(days) * 0.2), replace=False)
    rtr, rte = pool[~pool.date.isin(test_days)], pool[pool.date.isin(test_days)]
    m_random = mape(rte.y.values, np.exp(model().fit(rtr[FEATS], np.log(rtr.y)).predict(rte[FEATS])))
    v1 = FEATS + ["lag1"]
    m_v1 = mape(rte.y.values, np.exp(HistGradientBoostingRegressor(max_iter=250, learning_rate=0.06, max_leaf_nodes=31, min_samples_leaf=10,
                categorical_features=CAT_IDX, random_state=42).fit(rtr[v1], np.log(rtr.y)).predict(rte[v1])))
    m_temporal_same_period = mape(bt.y[ok & bt.date.isin(test_days)].values, bt.pred_model[ok & bt.date.isin(test_days)].values)
    # event 5: Easter Monday 2026 at network level
    em = bt[bt.date == "2026-04-06"]
    easter = {"actual": float(em.y.sum()), "model": float(em.pred_model.sum()), "naive": float(em.pred_naive.sum())}
    # event 3: ATM036 in the 3 weeks after the closure
    w36 = bt[(bt.atm_id == "ATM036") & (bt.date >= CLOSE) & (bt.date < CLOSE + pd.Timedelta(days=21))]
    a36 = {"mape_with_transfer": mape(w36.y.values, w36.pred_model.values), "mape_without": mape(w36.y.values, w36.pred_model_raw.values),
           "under_forecast_without_eur": float((w36.y - w36.pred_model_raw).sum()),
           "cash_planned_for_atm037_eur": float(f[(f.atm_id == "ATM037") & (f.date < CLOSE)].tail(28).y.mean() * 21)}
    # event 4: festival days
    fe = bt[bt.local_event == 1]
    fest = {"mape_model": mape(fe.y.values, fe.pred_model.values), "mape_naive": mape(fe.y.values, fe.pred_naive.values), "n": int(len(fe))}
    # production: frozen model on Sept-Oct 2026, weekly origins
    frozen = fit(f[f.date < PROD_START])
    prod = rolling_backtest(f, pd.date_range(PROD_START, "2026-10-31", freq="7D"), frozen=frozen)
    prod = prod[prod.date <= "2026-10-31"]
    prod[["date", "atm_id", "region", "site_type", "horizon", "y", "pred_model", "pred_naive"]].to_parquet(PROC / "atm_prod.parquet", index=False)
    # drift monitoring by site type: daily percentage error of the segment total
    allp = pd.concat([bt.assign(phase="backtest"), prod.assign(phase="production")])
    allp = allp[allp.y.notna()]
    seg = allp.groupby(["phase", "date", "site_type"]).agg(y=("y", "sum"), p=("pred_model", "sum")).reset_index()
    seg["pe"] = (seg.y - seg.p) / seg.p
    rows, detect = [], {}
    for st, g in seg.groupby("site_type"):
        g = g.sort_values("date").copy()
        ref = g[g.phase == "backtest"].pe
        g["cusum"], _ = cusum_lower(g.pe.values, ref.mean(), ref.std())
        g["mape7"] = g.pe.abs().rolling(7, min_periods=7).mean()
        rows.append(g)
    drift = pd.concat(rows)
    # two levels: WATCH at 5 (look, no action), ALERT above 1.25x the highest CUSUM seen Jan-Aug 2026 (no known drift)
    h_watch = 5.0
    h_alert = float(np.ceil(1.25 * max(h_watch, drift[drift.date < PROD_START].cusum.max())))
    drift["cusum_watch"], drift["cusum_alert"] = h_watch, h_alert
    for st, g in drift.groupby("site_type"):
        al = g[(g.date >= PROD_START) & (g.cusum > h_alert)]
        wa = g[(g.date >= PROD_START) & (g.cusum > h_watch)]
        detect[st] = str(al.date.iloc[0].date()) if len(al) else None
        detect[st + "_watch_days_sep_oct"] = int(len(wa))
        detect[st + "_watch_days_jan_aug"] = int(((g.date < PROD_START) & (g.cusum > h_watch)).sum())
        detect[st + "_bias_sep1_14"] = float(g[(g.date >= PROD_START) & (g.date < "2026-09-15")].pe.mean())
        detect[st + "_bias_sep15_oct31"] = float(g[g.date >= "2026-09-15"].pe.mean())
        back = g[(g.date > (pd.Timestamp(detect[st]) if detect[st] else PROD_START)) & (g.cusum < h_watch)]
        detect[st + "_back_below_watch"] = str(back.date.iloc[0].date()) if detect[st] and len(back) else None
    drift[drift.date >= "2026-06-01"][["date", "site_type", "pe", "mape7", "cusum", "cusum_watch", "cusum_alert"]].to_csv(PROC / "atm_drift.csv", index=False)
    mall_days = (pd.Timestamp(detect["mall"]) - PROD_START).days + 1 if detect["mall"] else None
    prod_ok = prod.y.notna() & (prod.y > 0)
    prod_mape = prod[prod_ok].assign(ape=lambda x: (x.y - x.pred_model).abs() / x.y).groupby("site_type").ape.mean()
    # refill policy on Sept-Oct, with the frozen forecasts
    rc = pd.read_parquet(SIM / "refill_costs.parquet").iloc[0]
    master = pd.read_parquet(SIM / "atm_master.parquet").set_index("atm_id")
    q = bt[ok].assign(r=lambda x: x.y / x.pred_model).r.quantile(0.95)
    pol = []
    for a, g in prod.sort_values("date").groupby("atm_id"):
        cap = master.loc[a, "cassette_capacity_eur"]
        for mode in ("fixed", "forecast"):
            v, o, c = refill_policy(g, cap, rc.cost_per_refill_visit_eur, rc.cost_per_stockout_hour_eur, rc.cash_holding_cost_per_year, mode, q95=q)
            pol.append({"atm_id": a, "site_type": master.loc[a, "site_type"], "policy": mode, "visits": v, "stockout_hours": o, "cost_eur": c})
    pol = pd.DataFrame(pol)
    pol.to_csv(PROC / "atm_refill.csv", index=False)
    ps = pol.groupby("policy")[["visits", "stockout_hours", "cost_eur"]].sum()
    run_sql.run_all(verbose=False)
    simp = pd.read_csv(PROC / "simpson.csv")
    sp = simp.pivot(index="site_type", columns="region", values="mape")
    simpson_holds = bool(sp.loc["ALL", "Flanders"] < sp.loc["ALL", "Brussels"] and
                         all(sp.drop("ALL").Flanders > sp.drop("ALL").Brussels))
    save_findings("atm", {
        "n_atms": int(f.atm_id.nunique()), "n_origins": int(len(origins)), "bt_from": str(origins[0].date()), "bt_to": str((origins[-1] + pd.Timedelta(days=6)).date()),
        "mape_model": m_model, "mape_naive": m_naive, "mape_random_split": m_random, "mape_v1_random_lag1": m_v1, "mape_temporal_same_days": m_temporal_same_period,
        "easter": easter, "atm036": a36, "festival": fest,
        "drift_detect_mall": detect["mall"], "cusum_h_watch": h_watch, "cusum_h_alert": h_alert, "drift_days_to_detect": mall_days, "drift_detect_all": detect,
        "prod_mape_by_site": {k: float(v) for k, v in prod_mape.items()},
        "refill": {p: {k: float(v) for k, v in ps.loc[p].items()} for p in ps.index}, "refill_q95_ratio": float(q),
        "simpson": {f"{r}|{s}": float(sp.loc[s, r]) for s in sp.index for r in sp.columns}, "simpson_holds": simpson_holds,
    })
    print(f"backtest MAPE model {m_model:.3f} vs naive {m_naive:.3f} | v1 random+lag1 {m_v1:.3f} | random split {m_random:.3f} vs temporal (same days) {m_temporal_same_period:.3f}")
    print("Easter Monday", {k: round(v) for k, v in easter.items()}, "| ATM036", {k: round(v, 3) for k, v in a36.items()})
    print("festival", fest, "| drift detection", detect, "->", mall_days, "days")
    print("prod MAPE by site", prod_mape.round(3).to_dict())
    print(ps.round(0).to_string())
    print(sp.round(3).to_string(), "| Simpson holds:", simpson_holds)


if __name__ == "__main__":
    main()
