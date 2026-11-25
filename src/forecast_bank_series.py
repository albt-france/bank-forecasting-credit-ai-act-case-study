"""PUBLIC DATA (ECB): forecast new mortgage volumes in Belgium with the mortgage rate as explanatory variable,
and describe the break in household overnight deposits.

Models: seasonal naive, ETS (log, damped trend, additive seasonality), SARIMAX(1,1,1)(0,1,1,12) on log volume with the
new-mortgage rate as exogenous variable. Rolling-origin backtest: 12 origins (2024-10 .. 2025-09), horizons 1-12 months;
MAPE, MASE, 80% and 95% interval coverage. Three rate scenarios for the next 12 months (stable, -50 bp, +50 bp).
Deposits: single break in trend located by least squares, Chow F-test at that date; date and size only, no cause.
    python src/forecast_bank_series.py
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.exponential_smoothing.ets import ETSModel
from statsmodels.tsa.statespace.sarimax import SARIMAX

from common import PROC, save_findings

warnings.filterwarnings("ignore")
ORIGINS = pd.period_range("2024-10", "2025-09", freq="M")
H = 12


def load():
    e = pd.read_csv(PROC / "ecb_series.csv")
    w = e.pivot(index="month", columns="series", values="value")
    w.index = pd.PeriodIndex(w.index, freq="M")
    return w


def fit_sarimax(y, x):
    return SARIMAX(np.log(y), exog=x, order=(1, 1, 1), seasonal_order=(0, 1, 1, 12)).fit(disp=False)


def fit_ets(y):
    return ETSModel(np.log(y), error="add", trend="add", damped_trend=True, seasonal="add", seasonal_periods=12).fit(disp=False)


def predict(model, name, n, x_future=None):
    """Return a frame (pred, lo80, hi80, lo95, hi95) on the original scale."""
    out = {}
    if name == "SARIMAX":
        fc = model.get_forecast(n, exog=x_future)
        out["pred"] = np.exp(fc.predicted_mean.values)
        for a, k in ((0.2, "80"), (0.05, "95")):
            ci = fc.conf_int(alpha=a).values
            out[f"lo{k}"], out[f"hi{k}"] = np.exp(ci[:, 0]), np.exp(ci[:, 1])
    else:
        fc = model.get_prediction(start=model.nobs, end=model.nobs + n - 1)
        out["pred"] = np.exp(fc.predicted_mean.values)
        for a, k in ((0.2, "80"), (0.05, "95")):
            sf = fc.summary_frame(alpha=a)
            out[f"lo{k}"], out[f"hi{k}"] = np.exp(sf["pi_lower"].values), np.exp(sf["pi_upper"].values)
    return pd.DataFrame(out)


def backtest(w):
    y, x = w["mortgage_volume_new"], w[["mortgage_rate_new"]]
    rows = []
    for o in ORIGINS:
        tr = y[:o]
        fut = pd.period_range(o + 1, periods=H, freq="M")
        scale = np.mean(np.abs(tr.values[12:] - tr.values[:-12]))       # in-sample seasonal naive MAE (MASE scale)
        sn = pd.DataFrame({"pred": [y[m - 12] for m in fut]})
        for name, df in (("Seasonal naive", sn),
                         ("ETS", predict(fit_ets(tr), "ETS", H)),
                         ("SARIMAX + rate", predict(fit_sarimax(tr, x[:o]), "SARIMAX", H, x.loc[fut]))):
            df = df.assign(model=name, origin=str(o), month=[str(m) for m in fut], h=range(1, H + 1),
                           actual=y.loc[fut].values, scale=scale)
            rows.append(df)
    bt = pd.concat(rows, ignore_index=True)
    bt["ape"] = (bt.actual - bt.pred).abs() / bt.actual
    bt["ase"] = (bt.actual - bt.pred).abs() / bt.scale
    bt["in80"] = (bt.actual >= bt.lo80) & (bt.actual <= bt.hi80)
    bt["in95"] = (bt.actual >= bt.lo95) & (bt.actual <= bt.hi95)
    return bt


def deposits_break(w):
    d = np.log(w["deposits_hh_overnight"])
    t = np.arange(len(d))
    best = None
    for k in range(24, len(d) - 24):                           # at least 2 years on each side
        X = np.column_stack([np.ones_like(t), t, np.maximum(t - k, 0)])
        beta, ssr, *_ = np.linalg.lstsq(X, d.values, rcond=None)
        ssr = float(((d.values - X @ beta) ** 2).sum())
        if best is None or ssr < best[1]:
            best = (k, ssr, beta)
    k, ssr_u, beta = best
    X0 = np.column_stack([np.ones_like(t), t])
    b0 = np.linalg.lstsq(X0, d.values, rcond=None)[0]
    ssr_r = float(((d.values - X0 @ b0) ** 2).sum())
    F = (ssr_r - ssr_u) / 1 / (ssr_u / (len(d) - 3))
    # Chow test at the located date (two separate linear trends), reported with its p-value; the date was searched,
    # so the p-value is optimistic (sup-F): we only use it to describe, not to prove.
    pre, post = d.iloc[:k + 1], d.iloc[k + 1:]
    def ssr_lin(s):
        tt = np.arange(len(s)); X = np.column_stack([np.ones_like(tt), tt])
        b = np.linalg.lstsq(X, s.values, rcond=None)[0]; return float(((s.values - X @ b) ** 2).sum())
    ssr_c = ssr_lin(pre) + ssr_lin(post)
    chow = ((ssr_r - ssr_c) / 2) / (ssr_c / (len(d) - 4))
    p = 1 - stats.f.cdf(chow, 2, len(d) - 4)
    dep = w["deposits_hh_overnight"]
    g_pre = (np.exp(beta[1] * 12) - 1)
    g_post = (np.exp((beta[1] + beta[2]) * 12) - 1)
    return {"break_month": str(d.index[k]), "growth_before_pct_yr": g_pre * 100, "growth_after_pct_yr": g_post * 100,
            "chow_F": chow, "chow_p": p, "slope_F": F,
            "peak_month": str(dep.idxmax()), "peak_value_m": float(dep.max()),
            "first_value_m": float(dep.iloc[0]), "last_value_m": float(dep.iloc[-1]), "last_month": str(dep.index[-1]),
            "drop_peak_to_last_pct": (dep.iloc[-1] / dep.max() - 1) * 100,
            "fitted": [float(v) for v in np.exp(np.column_stack([np.ones_like(t), t, np.maximum(t - k, 0)]) @ beta)]}


def deposits_backtest(w):
    y = w["deposits_hh_overnight"]
    rows = []
    for o in ORIGINS:
        tr = y[:o]
        fut = pd.period_range(o + 1, periods=H, freq="M")
        scale = np.mean(np.abs(np.diff(tr.values)))
        m = ETSModel(np.log(tr), error="add", trend="add", damped_trend=True).fit(disp=False)
        p_ets = np.exp(m.forecast(H).values)
        for name, p in (("Naive (last value)", np.repeat(tr.iloc[-1], H)), ("ETS", p_ets)):
            rows.append(pd.DataFrame({"model": name, "origin": str(o), "h": range(1, H + 1), "actual": y.loc[fut].values,
                                      "pred": p, "scale": scale}))
    bt = pd.concat(rows, ignore_index=True)
    bt["ape"] = (bt.actual - bt.pred).abs() / bt.actual
    bt["ase"] = (bt.actual - bt.pred).abs() / bt.scale
    return bt


def main():
    w = load()
    bt = backtest(w)
    bt.to_parquet(PROC / "fc_backtest.parquet", index=False)
    met = bt.groupby("model").agg(mape=("ape", "mean"), mase=("ase", "mean"), cov80=("in80", "mean"), cov95=("in95", "mean")).reset_index()
    met.loc[met.model == "Seasonal naive", ["cov80", "cov95"]] = np.nan
    byh = bt.groupby(["model", "h"]).ape.mean().unstack(0)
    byh.to_csv(PROC / "fc_mape_by_h.csv")
    met.to_csv(PROC / "fc_metrics.csv", index=False)
    print(met.round(3).to_string(index=False))
    # final SARIMAX on all data, 12-month rate scenarios
    y, x = w["mortgage_volume_new"], w[["mortgage_rate_new"]]
    final = fit_sarimax(y, x)
    beta = float(final.params["mortgage_rate_new"])
    fut = pd.period_range(y.index[-1] + 1, periods=H, freq="M")
    last_rate = float(x.iloc[-1, 0])
    sc = []
    for name, shift in (("Stable rate", 0.0), ("-50 bp", -0.5), ("+50 bp", 0.5)):
        xf = pd.DataFrame({"mortgage_rate_new": last_rate + shift}, index=fut)
        p = predict(final, "SARIMAX", H, xf).assign(scenario=name, month=[str(m) for m in fut], rate=last_rate + shift)
        sc.append(p)
    sc = pd.concat(sc, ignore_index=True)
    sc.to_csv(PROC / "fc_scenarios.csv", index=False)
    tot = sc.groupby("scenario").pred.sum()
    hist = pd.DataFrame({"month": [str(m) for m in w.index], "volume": y.values, "rate": x.iloc[:, 0].values,
                         "deposits": w["deposits_hh_overnight"].values})
    db = deposits_break(w)
    hist["deposits_fitted_break"] = db.pop("fitted")
    hist.to_csv(PROC / "fc_history.csv", index=False)
    dbt = deposits_backtest(w)
    dmet = dbt.groupby("model").agg(mape=("ape", "mean"), mase=("ase", "mean")).reset_index()
    dmet.to_csv(PROC / "dep_metrics.csv", index=False)
    sar, ets, sn = (met.set_index("model").loc[k] for k in ("SARIMAX + rate", "ETS", "Seasonal naive"))
    save_findings("forecast", {
        "n_months": int(len(w)), "first_month": str(w.index[0]), "last_month": str(w.index[-1]),
        "n_origins": len(ORIGINS), "origins": f"{ORIGINS[0]} to {ORIGINS[-1]}",
        "mape_sarimax": sar.mape, "mase_sarimax": sar.mase, "cov80_sarimax": sar.cov80, "cov95_sarimax": sar.cov95,
        "mape_ets": ets.mape, "mase_ets": ets.mase, "cov80_ets": ets.cov80, "cov95_ets": ets.cov95,
        "mape_snaive": sn.mape, "mase_snaive": sn.mase,
        "rate_coef_log": beta, "rate_effect_pct_per_100bp": (np.exp(beta) - 1) * 100,
        "rate_coef_p": float(final.pvalues["mortgage_rate_new"]),
        "rate_effect_ci95_pct": [float((np.exp(v) - 1) * 100) for v in final.conf_int().loc["mortgage_rate_new"]],
        "last_rate": last_rate, "rate_min": float(x.iloc[:, 0].min()), "rate_min_month": str(x.iloc[:, 0].idxmin()),
        "rate_max": float(x.iloc[:, 0].max()), "rate_max_month": str(x.iloc[:, 0].idxmax()),
        "vol_last": float(y.iloc[-1]), "vol_last_3": [float(v) for v in y.iloc[-3:]],
        "next12_stable_m": float(tot["Stable rate"]), "next12_minus50_m": float(tot["-50 bp"]), "next12_plus50_m": float(tot["+50 bp"]),
        "last12_actual_m": float(y.iloc[-12:].sum()),
        "deposits": db,
        "dep_mape_ets": float(dmet.set_index("model").loc["ETS", "mape"]), "dep_mape_naive": float(dmet.set_index("model").loc["Naive (last value)", "mape"]),
        "dep_mase_ets": float(dmet.set_index("model").loc["ETS", "mase"]), "dep_mase_naive": float(dmet.set_index("model").loc["Naive (last value)", "mase"]),
    })
    print(f"rate effect {(np.exp(beta) - 1) * 100:.1f}% per +1 pp (p={final.pvalues['mortgage_rate_new']:.3f}); next 12 m:",
          {k: round(v) for k, v in tot.items()}, "| last 12 m actual", round(y.iloc[-12:].sum()))
    print("deposits break", db["break_month"], f"growth {db['growth_before_pct_yr']:.1f}% -> {db['growth_after_pct_yr']:.1f}%/yr, Chow F={db['chow_F']:.0f}")
    print(dmet.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
