"""Matplotlib charts for the PDF (site/report/img/*.png). Every number is read from data/processed.
Each image carries its data label (PUBLIC DATA or SIMULATED) in the top-right corner.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

from common import PROC, ROOT, load_findings

IMG = ROOT / "site" / "report" / "img"
BLUE, GREY, RED, INK, MUTED, GRID, ORANGE, GREEN, LIGHT = "#2A78D6", "#A3A19A", "#D03B3B", "#0B0B0B", "#52514E", "#E1E0D9", "#EB6834", "#1BAF7A", "#C9DDF5"
plt.rcParams.update({
    "font.family": "Segoe UI", "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "figure.facecolor": "white", "axes.facecolor": "white", "legend.frameon": False,
    "axes.titlesize": 11, "axes.titleweight": "semibold", "axes.titlecolor": INK, "axes.titlelocation": "left",
})


def save(fig, name, label):
    IMG.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.text(0.995, 0.995, label, ha="right", va="top", fontsize=7.5, fontweight="bold",
             color="#1C5CAB" if label == "PUBLIC DATA" else "#9A3B12")
    fig.savefig(IMG / f"{name}.png", dpi=200)
    plt.close(fig)
    return f"img/{name}.png"


def ym(s):
    return pd.PeriodIndex(s, freq="M").to_timestamp()


# ---------------------------------------------------------------- page 1-2: ECB (PUBLIC DATA)
def deposits():
    h, f = pd.read_csv(PROC / "fc_history.csv"), load_findings()["forecast"]["deposits"]
    x = ym(h.month)
    fig, ax = plt.subplots(figsize=(5.0, 5.0))
    ax.plot(x, h.deposits / 1000, color=BLUE, lw=2, label="Overnight deposits, households")
    ax.plot(x, h.deposits_fitted_break / 1000, color=GREY, lw=1.2, ls="--", label="Two-trend fit (least squares)")
    b = pd.Period(f["break_month"]).to_timestamp()
    ax.axvline(b, color=RED, ls=":", lw=1)
    ax.text(b, 70, f" trend turns\n {f['break_month']}", color=RED, fontsize=8.5)
    pk = pd.Period(f["peak_month"]).to_timestamp()
    ax.annotate(f"peak {f['peak_value_m'] / 1000:.1f} bn\n{f['peak_month']}", (pk, f["peak_value_m"] / 1000), (pk + pd.Timedelta(days=500), 135),
                fontsize=8.5, color=INK, arrowprops=dict(arrowstyle="-", color=MUTED))
    ax.set_ylabel("EUR bn"); ax.legend(loc="lower right", fontsize=8.5)
    ax.set_title("Belgian household overnight deposits, 2015-01 to 2026-09")
    return save(fig, "deposits", "PUBLIC DATA")


def rate_volume():
    h = pd.read_csv(PROC / "fc_history.csv")
    x = ym(h.month)
    fig, ax = plt.subplots(figsize=(5.0, 5.0))
    ax.bar(x, h.volume / 1000, width=25, color=LIGHT, label="New mortgage volume (EUR bn, left)")
    ax.set_ylabel("EUR bn per month")
    ax2 = ax.twinx()
    ax2.plot(x, h.rate, color=BLUE, lw=2, label="New mortgage rate (% , right)")
    ax2.spines["right"].set_visible(True); ax2.grid(False); ax2.set_ylabel("%")
    ax.legend(loc="upper left", fontsize=8.5); ax2.legend(loc="upper right", fontsize=8.5)
    ax.set_title("New mortgages in Belgium: volume and rate")
    return save(fig, "rate_volume", "PUBLIC DATA")


def mape_by_h():
    d = pd.read_csv(PROC / "fc_mape_by_h.csv").set_index("h")
    fig, ax = plt.subplots(figsize=(5.0, 5.0))
    for c, col in (("Seasonal naive", GREY), ("SARIMAX + rate", ORANGE), ("ETS", BLUE)):
        ax.plot(d.index, d[c] * 100, marker="o", ms=3.5, color=col, lw=2, label=c)
    ax.set_xlabel("Horizon (months ahead)"); ax.set_ylabel("MAPE, %")
    ax.set_xticks(range(1, 13)); ax.legend(fontsize=8.5)
    ax.set_title("Backtest error by horizon (12 rolling origins)")
    return save(fig, "mape_by_h", "PUBLIC DATA")


def scenarios():
    h, s = pd.read_csv(PROC / "fc_history.csv"), pd.read_csv(PROC / "fc_scenarios.csv")
    fig, ax = plt.subplots(figsize=(5.0, 5.0))
    hh = h.tail(36)
    ax.plot(ym(hh.month), hh.volume / 1000, color=INK, lw=1.6, label="Actual")
    st = s[s.scenario == "Stable rate"]
    x = ym(st.month)
    ax.fill_between(x, st.lo95 / 1000, st.hi95 / 1000, color=LIGHT, alpha=0.5, lw=0, label="95% interval (stable)")
    ax.fill_between(x, st.lo80 / 1000, st.hi80 / 1000, color=LIGHT, lw=0, label="80% interval (stable)")
    for name, col in (("-50 bp", GREEN), ("Stable rate", BLUE), ("+50 bp", RED)):
        g = s[s.scenario == name]
        ax.plot(ym(g.month), g.pred / 1000, color=col, lw=2, label=name)
    ax.xaxis.set_major_locator(matplotlib.dates.MonthLocator(bymonth=[1, 7]))
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b %y")); ax.tick_params(axis="x", labelsize=8, rotation=30)
    ax.set_ylabel("EUR bn per month"); ax.legend(fontsize=7.5, ncol=2, loc="upper left")
    ax.set_title("Next 12 months under three rate scenarios (SARIMAX)")
    return save(fig, "scenarios", "PUBLIC DATA")


# ---------------------------------------------------------------- page 3: targeting (PUBLIC DATA)
def gain():
    g = pd.read_csv(PROC / "bm_gain.csv")
    f = load_findings()["marketing"]
    fig, ax = plt.subplots(figsize=(5.0, 5.0))
    ax.plot(g.share_called * 100, g.with_duration_leak * 100, color=GREY, ls="--", lw=1.5, label=f"With call duration (leak), AUC {f['auc_with_duration']:.2f}")
    ax.plot(g.share_called * 100, g.share_subscribers_found * 100, color=BLUE, lw=2.2, label=f"Final model, AUC {f['auc_final']:.2f}")
    ax.plot([0, 100], [0, 100], color=RED, lw=1, ls=":", label="Random calls")
    ax.scatter([20], [f["gain_top20"] * 100], color=BLUE, zorder=5)
    ax.annotate(f"top 20% of calls\n= {f['gain_top20']:.0%} of subscribers", (20, f["gain_top20"] * 100), (32, 45), fontsize=8.5,
                arrowprops=dict(arrowstyle="-", color=MUTED))
    ax.set_xlabel("Share of clients called (highest score first), %"); ax.set_ylabel("Share of subscribers reached, %")
    ax.legend(fontsize=8, loc="lower right"); ax.set_title("Cumulative gain on the test set")
    return save(fig, "gain", "PUBLIC DATA")


def segments():
    b = pd.read_csv(PROC / "bm_segments.csv")
    keep = [("previous campaign outcome", "success"), ("previous campaign outcome", "failure"), ("previous campaign outcome", "nonexistent"),
            ("contact channel", "cellular"), ("contact channel", "telephone"),
            ("calls in this campaign", "1"), ("calls in this campaign", "5+"),
            ("Euribor 3m at call", "a. < 1.5%"), ("Euribor 3m at call", "c. >= 4.5%")]
    lab = {"success": "Previous campaign: success", "failure": "Previous campaign: failure", "nonexistent": "Never contacted before",
           "cellular": "Mobile phone", "telephone": "Landline", "1": "1st call this campaign", "5+": "5th call or more",
           "a. < 1.5%": "Euribor 3m < 1.5%", "c. >= 4.5%": "Euribor 3m >= 4.5%"}
    rows = [b[(b.segment == s) & (b.level == l)].iloc[0] for s, l in keep]
    fig, ax = plt.subplots(figsize=(5.0, 5.0))
    y = np.arange(len(rows))[::-1]
    v = [r.subscription_rate * 100 for r in rows]
    ax.barh(y, v, color=[BLUE if x > 11.3 else GREY for x in v], height=0.65)
    for yi, vi, r in zip(y, v, rows):
        ax.text(vi + 1, yi, f"{vi:.0f}%  (n={r.calls:,})", va="center", fontsize=8)
    ax.set_yticks(y); ax.set_yticklabels([lab[r.level] for r in rows], fontsize=8.5)
    ax.axvline(11.3, color=RED, ls=":", lw=1); ax.text(12, -0.9, "average 11.3%", color=RED, fontsize=8)
    ax.set_xlim(0, 85); ax.set_xlabel("Subscription rate, %"); ax.set_title("Who says yes: subscription rate by segment")
    return save(fig, "segments", "PUBLIC DATA")


# ---------------------------------------------------------------- page 4: credit (PUBLIC DATA)
def calibration():
    c = pd.read_csv(PROC / "credit_calibration.csv")
    fig, ax = plt.subplots(figsize=(4.2, 4.6))
    ax.plot([0, 0.8], [0, 0.8], color=GREY, ls=":", lw=1, label="Perfect calibration")
    for m, col in (("Gradient boosting", ORANGE), ("Logistic scorecard", BLUE)):
        g = c[c.model == m]
        ax.plot(g.predicted, g.observed, marker="o", ms=4, color=col, lw=2, label=m)
    ax.set_xlabel("Predicted default probability"); ax.set_ylabel("Observed default rate")
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(1.0)); ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.legend(fontsize=8); ax.set_title("Calibration (10 groups of 900 clients)")
    return save(fig, "calibration", "PUBLIC DATA")


def cost_curve():
    c, f = pd.read_csv(PROC / "credit_cost_curve.csv"), load_findings()["credit"]
    fig, ax = plt.subplots(figsize=(4.2, 4.6))
    ax.plot(c.threshold, c.cost_per_applicant, color=BLUE, lw=2)
    ax.axvline(f["threshold_best"], color=RED, ls="--", lw=1)
    ax.text(f["threshold_best"] + 0.01, c.cost_per_applicant.max() * 0.95, f"cut-off {f['threshold_best']:.2f}\naccept {f['acceptance_at_best']:.0%}", color=RED, fontsize=8.5, va="top")
    ax.axvline(0.5, color=GREY, ls=":", lw=1); ax.text(0.51, f["cost_at_050"] + 0.02, "usual 0.50", color=MUTED, fontsize=8)
    ax.set_xlabel("Cut-off on predicted default probability"); ax.set_ylabel("Expected cost per client (units)")
    ax.set_title("Cost-based cut-off (missed default = 5x lost client)")
    return save(fig, "cost_curve", "PUBLIC DATA")


def importance():
    d = pd.read_csv(PROC / "credit_importance.csv").iloc[::-1]
    lab = {"months_late_5m": "Months late (last 5)", "status_last": "Repayment status, last month", "LIMIT_BAL": "Credit limit",
           "utilisation": "Utilisation of the limit", "bill_trend": "Bill trend (5 months)", "paid_ratio": "Share of bill paid"}
    fig, ax = plt.subplots(figsize=(4.2, 4.6))
    ax.barh([lab[v] for v in d.variable], d.auc_drop, color=BLUE, height=0.6)
    ax.set_xlabel("AUC lost when the variable is shuffled"); ax.set_title("What drives the score")
    return save(fig, "importance", "PUBLIC DATA")


def fairness():
    d = pd.read_csv(PROC / "credit_fairness.csv")
    d = pd.concat([d[d.attribute == "sex"].sort_values("grp", ascending=False),
                   d[d.attribute == "age band"].set_index("grp").loc[["<30", "30-39", "40-49", "50+"]].reset_index()])
    fig, ax = plt.subplots(figsize=(4.2, 4.6))
    x = np.arange(len(d))
    ax.bar(x - 0.2, d.acceptance_rate * 100, 0.38, color=BLUE, label="Accepted")
    ax.bar(x + 0.2, d.good_declined_rate * 100, 0.38, color=ORANGE, label="Good clients declined")
    ax.plot(x, d.observed_default_rate * 100, "D", color=INK, ms=4, label="Observed default rate")
    ax.set_xticks(x); ax.set_xticklabels([f"{g}\nn={n:,}" for g, n in zip(d.grp, d.n)], fontsize=7.5)
    ax.axvline(1.5, color=GRID, lw=1)
    ax.set_ylabel("%"); ax.legend(fontsize=7.5, loc="upper right", ncol=1); ax.set_ylim(0, 85)
    ax.set_title("Fairness check by sex and age (not model inputs)")
    return save(fig, "fairness", "PUBLIC DATA")


# ---------------------------------------------------------------- page 5: ATM (SIMULATED)
def easter():
    b = pd.read_parquet(PROC / "atm_backtest.parquet")
    b = b[(b.date >= "2026-03-23") & (b.date <= "2026-04-19")]
    g = b.groupby("date")[["y", "pred_model", "pred_naive"]].sum() / 1000
    fig, ax = plt.subplots(figsize=(4.2, 4.6))
    ax.plot(g.index, g.y, color=INK, lw=2, label="Actual")
    ax.plot(g.index, g.pred_model, color=BLUE, lw=1.6, label="Model (knows holidays)")
    ax.plot(g.index, g.pred_naive, color=GREY, lw=1.2, ls="--", label="Same day last week")
    em = pd.Timestamp("2026-04-06")
    ax.annotate("Easter Monday\n(public holiday):\nno alert", (em, g.loc[em, "y"]), (em + pd.Timedelta(days=3), g.y.min() * 0.95), fontsize=8.5,
                arrowprops=dict(arrowstyle="-", color=MUTED))
    ax.set_ylabel("EUR k per day, network"); ax.legend(fontsize=8, loc="upper left")
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d %b"))
    ax.set_title("A -45% day that is not an incident")
    return save(fig, "easter", "SIMULATED")


def drift():
    d, f = pd.read_csv(PROC / "atm_drift.csv", parse_dates=["date"]), load_findings()["atm"]
    d = d[d.date >= "2026-07-15"]
    fig, ax = plt.subplots(figsize=(4.2, 4.6))
    for st, col, lw in (("mall", RED, 2.2), ("rural", ORANGE, 1.4), ("city_centre", GREY, 1.2), ("station", LIGHT, 1.2)):
        g = d[d.site_type == st]
        ax.plot(g.date, g.cusum, color=col, lw=lw, label=st.replace("_", " "))
    ax.axhline(f["cusum_h_alert"], color=RED, ls="--", lw=1); ax.text(d.date.min(), f["cusum_h_alert"] + 1, f"alert {f['cusum_h_alert']:.0f}", color=RED, fontsize=8)
    ax.axhline(f["cusum_h_watch"], color=MUTED, ls=":", lw=1); ax.text(d.date.min(), f["cusum_h_watch"] - 3, "watch 5", color=MUTED, fontsize=8)
    ax.axvline(pd.Timestamp("2026-09-01"), color=INK, lw=0.8); ax.text(pd.Timestamp("2026-09-02"), d.cusum.max() * 0.9, "model frozen\n1 Sept", fontsize=8)
    ax.set_ylabel("CUSUM (falls in demand)"); ax.legend(fontsize=8, loc="center left")
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d %b"))
    ax.set_title(f"Mall demand drift caught on {pd.Timestamp(f['drift_detect_mall']):%d %b}")
    return save(fig, "drift", "SIMULATED")


def validation():
    f = load_findings()["atm"]
    v = [("v1: random days\n+ yesterday's value", f["mape_v1_random_lag1"], GREY), ("random days,\nsame features", f["mape_random_split"], GREY),
         ("rolling origin\n(the real error)", f["mape_model"], BLUE), ("same weekday\nlast week", f["mape_naive"], ORANGE)]
    fig, ax = plt.subplots(figsize=(4.2, 4.6))
    ax.bar(range(4), [x[1] * 100 for x in v], color=[x[2] for x in v], width=0.6)
    for i, x in enumerate(v):
        ax.text(i, x[1] * 100 + 0.4, f"{x[1]:.1%}", ha="center", fontsize=9)
    ax.set_xticks(range(4)); ax.set_xticklabels([x[0] for x in v], fontsize=7.8)
    ax.set_ylabel("MAPE, % (ATM-days)"); ax.set_title("Validation: a shuffled test flatters the model")
    return save(fig, "validation", "SIMULATED")


def build_all():
    return {f.__name__: f() for f in (deposits, rate_volume, mape_by_h, scenarios, gain, segments, calibration, cost_curve,
                                      importance, fairness, easter, drift, validation)}


if __name__ == "__main__":
    print(build_all())
