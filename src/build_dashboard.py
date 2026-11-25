"""Self-contained interactive dashboard (Plotly, 5 tabs): site/dashboard/index.html. Data from data/processed.
Every chart title starts with its data label: PUBLIC DATA or SIMULATED.
    python src/build_dashboard.py
"""
import json

import pandas as pd
import plotly.graph_objects as go
from plotly.offline import get_plotlyjs
from plotly.subplots import make_subplots

from common import PROC, ROOT, load_findings

OUT = ROOT / "site" / "dashboard" / "index.html"
BLUE, GREY, RED, ORANGE, GREEN, LIGHT = "#2A78D6", "#A3A19A", "#D03B3B", "#EB6834", "#1BAF7A", "#C9DDF5"
FOOTER = "Independent case study based on public data · not affiliated with any bank or recruiter"


def style(fig, title, tag, h=380):
    fig.update_layout(title=dict(text=f"<span style='font-size:11px;color:{'#1C5CAB' if tag == 'PUBLIC DATA' else '#9A3B12'}'><b>{tag}</b></span><br>{title}",
                                 x=0.01, font=dict(size=15)),
                      template="plotly_white", height=h, margin=dict(l=55, r=20, t=70, b=45),
                      font=dict(family="Segoe UI, Arial", size=12), legend=dict(orientation="h", y=-0.18),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


def div(fig):
    return f'<div class="card">{fig.to_html(full_html=False, include_plotlyjs=False, config={"displayModeBar": False, "responsive": True})}</div>'


def ym(s):
    return pd.PeriodIndex(s, freq="M").to_timestamp()


def table(cols, rows):
    return ("<table><tr>" + "".join(f"<th>{c}</th>" for c in cols) + "</tr>" +
            "".join("<tr>" + "".join(f"<td>{v}</td>" for v in r) + "</tr>" for r in rows) + "</table>")


def tab_forecast(f):
    h, s = pd.read_csv(PROC / "fc_history.csv"), pd.read_csv(PROC / "fc_scenarios.csv")
    bh = pd.read_csv(PROC / "fc_mape_by_h.csv")
    x = ym(h.month)
    a = make_subplots(specs=[[{"secondary_y": True}]])
    a.add_bar(x=x, y=h.volume, name="New mortgage volume (EUR m)", marker_color=LIGHT)
    a.add_scatter(x=x, y=h.rate, name="New mortgage rate (%)", line=dict(color=BLUE, width=2), secondary_y=True)
    style(a, "New mortgages in Belgium: monthly volume and rate (ECB MIR)", "PUBLIC DATA")
    b = go.Figure()
    for c, col in (("Seasonal naive", GREY), ("SARIMAX + rate", ORANGE), ("ETS", BLUE)):
        b.add_scatter(x=bh.h, y=bh[c] * 100, name=c, mode="lines+markers", line=dict(color=col, width=2))
    b.update_xaxes(title="months ahead", dtick=1); b.update_yaxes(title="MAPE, %")
    style(b, "Backtest error by horizon, 12 rolling origins (2024-10 to 2025-09)", "PUBLIC DATA")
    c = go.Figure()
    hh = h.tail(36)
    c.add_scatter(x=ym(hh.month), y=hh.volume, name="Actual", line=dict(color="#0B0B0B"))
    st = s[s.scenario == "Stable rate"]
    xs = ym(st.month)
    c.add_scatter(x=list(xs) + list(xs[::-1]), y=list(st.hi95) + list(st.lo95[::-1]), fill="toself", fillcolor="rgba(42,120,214,0.12)",
                  line=dict(width=0), name="95% interval (stable)", hoverinfo="skip")
    c.add_scatter(x=list(xs) + list(xs[::-1]), y=list(st.hi80) + list(st.lo80[::-1]), fill="toself", fillcolor="rgba(42,120,214,0.25)",
                  line=dict(width=0), name="80% interval (stable)", hoverinfo="skip")
    for name, col in (("-50 bp", GREEN), ("Stable rate", BLUE), ("+50 bp", RED)):
        g = s[s.scenario == name]
        c.add_scatter(x=ym(g.month), y=g.pred, name=name, line=dict(color=col, width=2))
    c.update_yaxes(title="EUR m per month")
    style(c, "Next 12 months under three rate scenarios (SARIMAX with the rate)", "PUBLIC DATA")
    d = go.Figure()
    d.add_scatter(x=x, y=h.deposits, name="Household overnight deposits (EUR m)", line=dict(color=BLUE, width=2))
    d.add_scatter(x=x, y=h.deposits_fitted_break, name="Two-trend fit", line=dict(color=GREY, dash="dash"))
    dp = f["forecast"]["deposits"]
    d.add_vline(x=pd.Period(dp["break_month"]).to_timestamp(), line=dict(color=RED, dash="dot"))
    style(d, f"Deposits: trend turns in {dp['break_month']}, peak {dp['peak_month']} (date and size only, no cause claimed)", "PUBLIC DATA")
    fc = f["forecast"]
    note = (f"<p>ETS: MAPE {fc['mape_ets']:.1%}, MASE {fc['mase_ets']:.2f}; SARIMAX + rate: {fc['mape_sarimax']:.1%}; seasonal naive {fc['mape_snaive']:.1%}. "
            f"Intervals hold {fc['cov80_ets']:.0%} of actuals at the 80% level: too wide. Rate effect {fc['rate_effect_pct_per_100bp']:.0f}% per +1 pp "
            f"(95% CI {fc['rate_effect_ci95_pct'][0]:.0f}% to {fc['rate_effect_ci95_pct'][1]:.0f}%). Series: ECB BSI.M.BE.N.A.L21.A.1.U2.2250.Z01.E, "
            "MIR.M.BE.B.A2C.A.R.A.2250.EUR.N, MIR.M.BE.B.A2C.A.B.A.2250.EUR.N (EUR millions, UNIT_MULT = 6), read 25 Nov 2026.</p>")
    return f'<div class="note card">{note}</div><div class="grid">{div(a)}{div(b)}{div(c)}{div(d)}</div>'


def tab_target(f):
    mk = f["marketing"]
    g = pd.read_csv(PROC / "bm_gain.csv")
    a = go.Figure()
    a.add_scatter(x=g.share_called * 100, y=g.with_duration_leak * 100, name=f"With call duration (leak), AUC {mk['auc_with_duration']:.2f}", line=dict(color=GREY, dash="dash"))
    a.add_scatter(x=g.share_called * 100, y=g.share_subscribers_found * 100, name=f"Final model, AUC {mk['auc_final']:.2f}", line=dict(color=BLUE, width=3))
    a.add_scatter(x=[0, 100], y=[0, 100], name="Random calls", line=dict(color=RED, dash="dot"))
    a.update_xaxes(title="% of clients called (best score first)"); a.update_yaxes(title="% of subscribers reached")
    style(a, "Cumulative gain: who to call first (UCI Bank Marketing, test set)", "PUBLIC DATA", 420)
    b = pd.read_csv(PROC / "bm_segments.csv")
    fig = go.Figure()
    for seg in b.segment.unique():
        x = b[b.segment == seg]
        fig.add_bar(x=x.subscription_rate * 100, y=[f"{seg}: {l}" for l in x.level], orientation="h", name=seg,
                    customdata=x.calls, hovertemplate="%{y}<br>%{x:.1f}% of %{customdata:,} calls<extra></extra>")
    fig.update_xaxes(title="subscription rate, %"); fig.update_layout(showlegend=False)
    style(fig, "Subscription rate by business segment (groups of 5+ calls)", "PUBLIC DATA", 620)
    m = pd.read_csv(PROC / "bm_model_comparison.csv")
    t = table(["Model", "Inputs", "AUC (test)"], [(r.model, r.features, f"{r.auc:.3f}") for r in m.itertuples()])
    fa = pd.read_csv(PROC / "bm_fairness_age.csv")
    t2 = table(["Age band", "Calls", "Subscription rate", "Selected (top 20%)"],
               [(r.age_band, f"{r.n:,}", f"{r.subscription_rate:.1%}", f"{r.selected_rate:.1%}") for r in fa.itertuples()])
    note = (f"<h2>The duration trap <span class='tag pub'>PUBLIC DATA</span></h2><p>Call duration is only known after the call: it lifts the AUC from {mk['auc_final']:.2f} to "
            f"{mk['auc_with_duration']:.2f}. Excluded from the final model (SQL test). Age and marital status are not inputs. Out of time (latest calls), boosting falls to "
            f"{mk['auc_oot_gb']:.2f}, logistic keeps {mk['auc_oot_logistic']:.2f}.</p>{t}<h2>Selection by age band (aggregates)</h2>{t2}"
            "<p>Data: a Portuguese bank, May 2008 - Nov 2010 (UCI id 222, CC BY 4.0). Not Belgian clients.</p>")
    return f'<div class="grid">{div(a)}<div class="card">{note}</div>{div(fig)}</div>'


def tab_credit(f):
    cr = f["credit"]
    c = pd.read_csv(PROC / "credit_calibration.csv")
    a = go.Figure()
    a.add_scatter(x=[0, 0.8], y=[0, 0.8], name="Perfect", line=dict(color=GREY, dash="dot"))
    for m, col in (("Gradient boosting", ORANGE), ("Logistic scorecard", BLUE)):
        g = c[c.model == m]
        a.add_scatter(x=g.predicted, y=g.observed, name=m, mode="lines+markers", line=dict(color=col, width=2))
    a.update_xaxes(title="predicted default probability", tickformat=".0%"); a.update_yaxes(title="observed default rate", tickformat=".0%")
    style(a, "Calibration: 10 groups of 900 test clients", "PUBLIC DATA")
    cc = pd.read_csv(PROC / "credit_cost_curve.csv")
    b = make_subplots(specs=[[{"secondary_y": True}]])
    b.add_scatter(x=cc.threshold, y=cc.cost_per_applicant, name="Expected cost per client", line=dict(color=BLUE, width=2))
    b.add_scatter(x=cc.threshold, y=cc.acceptance_rate * 100, name="Acceptance rate, %", line=dict(color=GREY, dash="dash"), secondary_y=True)
    b.add_vline(x=cr["threshold_best"], line=dict(color=RED, dash="dash"))
    b.update_xaxes(title="cut-off on predicted default probability")
    style(b, f"Cost-based cut-off {cr['threshold_best']:.2f} (assumed: missed default = 5, lost good client = 1)", "PUBLIC DATA")
    im = pd.read_csv(PROC / "credit_importance.csv").iloc[::-1]
    d = go.Figure(go.Bar(x=im.auc_drop, y=im.variable, orientation="h", marker_color=BLUE))
    d.update_xaxes(title="AUC lost when shuffled")
    style(d, "Permutation importance (logistic scorecard)", "PUBLIC DATA")
    fa = pd.read_csv(PROC / "credit_fairness.csv")
    e = go.Figure()
    lab = [f"{a}: {g}" for a, g in zip(fa.attribute, fa.grp)]
    e.add_bar(x=lab, y=fa.acceptance_rate * 100, name="Accepted, %", marker_color=BLUE)
    e.add_bar(x=lab, y=fa.good_declined_rate * 100, name="Good clients declined, %", marker_color=ORANGE)
    e.add_scatter(x=lab, y=fa.observed_default_rate * 100, name="Observed default rate, %", mode="markers", marker=dict(color="#0B0B0B", symbol="diamond", size=9))
    style(e, "Fairness by sex and age band (not model inputs; all groups n >= 828)", "PUBLIC DATA")
    sc = pd.read_csv(PROC / "credit_scorecard.csv")
    t = table(["Variable", "Bin", "Points"], [(r.variable, r.bin, r.points) for r in sc.itertuples()])
    note = (f"<h2>Scorecard (logistic, 6 binned inputs) <span class='tag pub'>PUBLIC DATA</span></h2><p>AUC {cr['auc_lr']:.3f}, Gini {cr['gini_lr']:.2f}, KS {cr['ks_lr']:.2f}, "
            f"Brier {cr['brier_lr']:.3f}; challenger boosting AUC {cr['auc_gb']:.3f}. PSI of the score: {cr['psi_aug_sep']:.2f} (Aug vs Sept 2005), {cr['psi_stress']:.2f} "
            f"under a simulated stress. More points = lower risk. Data: UCI id 350, Taiwan 2005, CC BY 4.0, not Belgian clients.</p>"
            f"<div class='scroll'>{t}</div>")
    return f'<div class="grid">{div(a)}{div(b)}{div(d)}{div(e)}<div class="card">{note}</div></div>'


def tab_atm(f):
    at = f["atm"]
    bt = pd.read_parquet(PROC / "atm_backtest.parquet")
    pr = pd.read_parquet(PROC / "atm_prod.parquet")
    allp = pd.concat([bt[["date", "site_type", "y", "pred_model", "pred_naive"]], pr[["date", "site_type", "y", "pred_model", "pred_naive"]]])
    a = go.Figure()
    sts = ["all"] + sorted(allp.site_type.unique())
    for i, st in enumerate(sts):
        g = (allp if st == "all" else allp[allp.site_type == st]).groupby("date")[["y", "pred_model", "pred_naive"]].sum() / 1000
        vis = i == 0
        a.add_scatter(x=g.index, y=g.y, name="Actual", line=dict(color="#0B0B0B", width=1.5), visible=vis)
        a.add_scatter(x=g.index, y=g.pred_model, name="Model", line=dict(color=BLUE, width=1.5), visible=vis)
        a.add_scatter(x=g.index, y=g.pred_naive, name="Same day last week", line=dict(color=GREY, width=1, dash="dot"), visible=vis)
    btns = [dict(label=st.replace("_", " "), method="update", args=[{"visible": [j // 3 == i for j in range(3 * len(sts))]}]) for i, st in enumerate(sts)]
    a.update_layout(updatemenus=[dict(buttons=btns, x=1, xanchor="right", y=1.18, direction="down")])
    a.add_vline(x=pd.Timestamp("2026-09-01"), line=dict(color=RED, dash="dash"))
    a.update_yaxes(title="EUR k per day")
    style(a, "Daily withdrawals: actual vs 7-day-ahead forecast (backtest Jan-Aug, frozen model Sept-Oct 2026)", "SIMULATED", 420)
    d = pd.read_csv(PROC / "atm_drift.csv", parse_dates=["date"])
    b = go.Figure()
    for st, col in (("mall", RED), ("rural", ORANGE), ("city_centre", GREY), ("station", LIGHT)):
        g = d[d.site_type == st]
        b.add_scatter(x=g.date, y=g.cusum, name=st, line=dict(color=col, width=2))
    b.add_hline(y=at["cusum_h_alert"], line=dict(color=RED, dash="dash"), annotation_text="alert")
    b.add_hline(y=at["cusum_h_watch"], line=dict(color=GREY, dash="dot"), annotation_text="watch")
    style(b, f"Drift monitor (CUSUM on falls in demand): malls alert on {at['drift_detect_mall']}", "SIMULATED", 420)
    v = go.Figure(go.Bar(x=["v1: random days + yesterday", "random days", "rolling origin (real)", "same day last week"],
                         y=[at["mape_v1_random_lag1"] * 100, at["mape_random_split"] * 100, at["mape_model"] * 100, at["mape_naive"] * 100],
                         marker_color=[GREY, GREY, BLUE, ORANGE], text=[f"{x:.1%}" for x in (at["mape_v1_random_lag1"], at["mape_random_split"], at["mape_model"], at["mape_naive"])]))
    v.update_yaxes(title="MAPE, %")
    style(v, "Validation: a shuffled test flatters the model", "SIMULATED")
    dq = pd.read_csv(PROC / "dq_report.csv")
    t = table(["Status", "Check", "Rows", "Detail", "Owner"], [(f"<span class='st {r.status.lower()}'>{r.status}</span>", r.check, r.rows_affected, r.detail, r.owner) for r in dq.itertuples()])
    s = pd.read_csv(PROC / "simpson.csv")
    t2 = table(["Region", "Site type", "ATM-days", "MAPE"], [(r.region, r.site_type, f"{r.n:,}", f"{r.mape:.1%}") for r in s.itertuples()])
    rf = at["refill"]
    t3 = table(["Policy (Sept-Oct, 59 ATMs)", "Visits", "Stock-out hours", "Assumed cost"],
               [(k, f"{v['visits']:.0f}", f"{v['stockout_hours']:.0f}", f"€{v['cost_eur']:,.0f}") for k, v in rf.items()])
    return (f'<div class="card"><h2>Data checks with the data engineers <span class="tag sim">SIMULATED</span></h2><div class="scroll">{t}</div></div>'
            f'<div class="grid">{div(a)}{div(b)}{div(v)}<div class="card"><h2>Simpson\'s paradox <span class="tag sim">SIMULATED</span></h2>{t2}'
            f'<h2>Refill policy</h2>{t3}<p>Easter Monday 2026: actual €{at["easter"]["actual"] / 1000:.0f}k, model €{at["easter"]["model"] / 1000:.0f}k, '
            f'"same day last week" €{at["easter"]["naive"] / 1000:.0f}k: a holiday, not an incident.</p></div></div>')


def overview(f):
    fc, mk, cr, at = f["forecast"], f["marketing"], f["credit"], f["atm"]
    tiles = [("Forecast (mortgage volumes)", f"MASE {fc['mase_ets']:.2f}", f"ETS, MAPE {fc['mape_ets']:.1%} vs {fc['mape_snaive']:.1%} naive, 1-12 months", "pub"),
             ("Targeting gain", f"{mk['lift_top20']:.1f}x", f"top 20% of calls reach {mk['gain_top20']:.0%} of subscribers", "pub"),
             ("Credit model", f"AUC {cr['auc_lr']:.2f}", f"calibrated within {cr['cal_max_gap'] * 100:.0f} pts; cost-based cut-off {cr['threshold_best']:.2f}", "pub"),
             ("Drift detection", f"{at['drift_days_to_detect']} days", "to flag a -15% fall in mall ATM demand", "sim")]
    t = "".join(f'<div class="card"><span class="tag {c}">{"PUBLIC DATA" if c == "pub" else "SIMULATED"}</span><p class="lbl">{a}</p><div class="big">{b}</div><p>{d}</p></div>' for a, b, d, c in tiles)
    return f"""<div class="tiles">{t}</div>
<div class="grid"><div class="card"><h2>Three business questions</h2><ol>
<li><b>Forecast</b>: how many new mortgages and deposits to expect in Belgium (ECB data), with backtests, intervals and rate scenarios.</li>
<li><b>Model</b>: who to target for a term deposit (UCI Bank Marketing) and who may default (UCI credit cards), explained, calibrated and checked for fairness.</li>
<li><b>Production</b>: a simulated ATM network of a fictitious "Bank B": data checks with the data engineers, drift monitoring, refill policy.</li></ol>
<p>Plus an EU AI Act checklist for the credit model (high-risk, Annex III point 5(b)). Not legal advice.</p></div>
<div class="card"><h2>Recommendations</h2><ol>
<li>Plan mortgage volumes as ranges: €{fc['next12_stable_m'] / 1000:.1f} bn next 12 months at a stable rate; €{fc['next12_plus50_m'] / 1000:.1f}-{fc['next12_minus50_m'] / 1000:.1f} bn for ±50 bp.</li>
<li>Score and call the top 20%; past successes and mobile numbers first; never score on call duration.</li>
<li>Explainable scorecard with a cost-based cut-off; a person reviews each decline.</li>
<li>Data contract with the data engineers; two-level drift monitor; forecast-driven refills ({at['refill']['forecast']['visits']:.0f} vs {at['refill']['fixed']['visits']:.0f} visits).</li>
<li>Model card, logs, human oversight and an impact assessment before any credit model goes live.</li></ol></div></div>"""


HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bank data science case study - dashboard</title>
<style>
:root { --bg:#F4F4F2; --card:#FFFFFF; --line:#E1E0D9; --ink:#0B0B0B; --muted:#52514E; --accent:#2A78D6; }
* { box-sizing:border-box; } body { margin:0; font-family:'Segoe UI', Arial, sans-serif; background:var(--bg); color:var(--ink); }
.wrap { max-width:1320px; margin:0 auto; padding:20px 16px 40px; }
h1 { font-size:23px; margin:0 0 4px; } .sub { color:var(--muted); margin:0 0 14px; font-size:14px; }
nav { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:12px; }
nav button { border:1px solid var(--line); background:var(--card); color:var(--ink); padding:8px 13px; border-radius:6px; cursor:pointer; font:inherit; font-size:14px; }
nav button.on { border-color:var(--accent); color:var(--accent); font-weight:600; }
.tab { display:none; } .tab.on { display:block; }
.grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(520px, 1fr)); gap:12px; margin-top:12px; }
.tiles { display:grid; grid-template-columns:repeat(auto-fit, minmax(240px, 1fr)); gap:12px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:12px 14px; min-width:0; overflow:hidden; }
.grid > * { min-width:0; } .plotly-graph-div { width:100% !important; }
.card h2 { font-size:15px; margin:4px 0 6px; } .card p, .card li { font-size:13.5px; color:#2B2A27; line-height:1.45; }
.lbl { font-weight:700; color:var(--muted) !important; font-size:12px !important; text-transform:uppercase; letter-spacing:.04em; margin:6px 0 0; }
.big { font-size:32px; font-weight:700; margin:2px 0; }
.tag { font-size:10.5px; font-weight:700; letter-spacing:.06em; padding:2px 7px; border-radius:4px; }
.pub { background:#E3EEFB; color:#1C5CAB; } .sim { background:#FBE9E0; color:#9A3B12; }
table { border-collapse:collapse; width:100%; font-size:12.5px; margin:6px 0; } th, td { text-align:left; padding:4px 6px; border-bottom:1px solid var(--line); vertical-align:top; }
th { color:var(--muted); font-weight:600; } .scroll { max-height:420px; overflow:auto; }
.st { font-weight:700; font-size:11px; padding:1px 6px; border-radius:3px; } .st.pass { background:#E1F4EC; color:#0E7A52; } .st.warn { background:#FFF1D6; color:#8A5A00; } .st.fail { background:#FBE3E3; color:#A32626; }
.note p { margin:2px 0; } footer { margin-top:18px; font-size:12px; color:var(--muted); }
</style><script>__PLOTLY__</script></head><body><div class="wrap">
<h1>Forecast, model, explain: three bank questions answered with public data</h1>
<p class="sub">Interactive companion to the PDF report. Public data (ECB, UCI, EU AI Act) and a simulated ATM network of a fictitious "Bank B", tagged on every chart.</p>
<nav id="nav"><button data-t="t1" class="on">Overview</button><button data-t="t2">Belgian lending &amp; deposits forecast</button>
<button data-t="t3">Who to target</button><button data-t="t4">Credit risk &amp; fairness</button><button data-t="t5">ATM network &amp; data quality</button></nav>
<section id="t1" class="tab on">__T1__</section><section id="t2" class="tab">__T2__</section><section id="t3" class="tab">__T3__</section>
<section id="t4" class="tab">__T4__</section><section id="t5" class="tab">__T5__</section>
<footer>__FOOTER__ · Sources: ECB Data Portal; UCI Machine Learning Repository (CC BY 4.0); Regulation (EU) 2024/1689; Nager.Date. Data read on 25 Nov 2026.</footer>
</div><script>
document.querySelectorAll('#nav button').forEach(b => b.onclick = () => {
  document.querySelectorAll('#nav button').forEach(x => x.classList.toggle('on', x === b));
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('on', t.id === b.dataset.t));
  document.querySelectorAll('#' + b.dataset.t + ' .js-plotly-plot').forEach(el => Plotly.Plots.resize(el));
});
window.addEventListener('load', () => document.querySelectorAll('.tab.on .js-plotly-plot').forEach(el => Plotly.Plots.resize(el)));
window.addEventListener('resize', () => document.querySelectorAll('.tab.on .js-plotly-plot').forEach(el => Plotly.Plots.resize(el)));
</script></body></html>"""


def main():
    f = load_findings()
    html = (HTML.replace("__PLOTLY__", get_plotlyjs()).replace("__T1__", overview(f)).replace("__T2__", tab_forecast(f))
            .replace("__T3__", tab_target(f)).replace("__T4__", tab_credit(f)).replace("__T5__", tab_atm(f)).replace("__FOOTER__", FOOTER))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print("written", OUT.relative_to(ROOT), f"{OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
