"""Build the 7-page PDF (pages 0-6): charts (src/charts.py) -> HTML pages (16:9) -> PDF with headless Edge, empty metadata.
Every number is read from data/processed (findings.json and tables), so the report matches the code.
    python src/build_pdf.py
Output: site/report/bank_ds_case_study.pdf (the HTML draft is written to a temporary folder and deleted).
"""
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import pandas as pd
from pypdf import PdfReader, PdfWriter

import charts
from common import PROC, ROOT, load_findings

REP = ROOT / "site" / "report"
PDF_NAME = "bank_ds_case_study.pdf"
READ_ON = "25 Nov 2026"
FOOTER = "Independent case study based on public data · not affiliated with any bank or recruiter"
AI_NOTE = ("AI-assisted workflow: I used Claude, mainly to write scripts faster. I drove the project: I defined the questions, "
           "chose and validated the data sources, made the analytical decisions and checked every result.")
TITLE = "Forecast, model, explain: three bank questions answered with public data - and documented for the EU AI Act"
N_PAGES = 7


def pct(x, d=0, sign=False):
    return f"{x * 100:{'+' if sign else ''}.{d}f}%"


def bn(m, d=1):
    return f"€{m / 1000:.{d}f} bn"


def page(n, title, subtitle, tags, body, sources):
    t = "".join(f'<div class="tag tag-{x.lower().split()[0]}">{x}</div>' for x in tags)
    return f"""
<section class="page">
  <header><div><h1>{title}</h1><p class="sub">{subtitle}</p></div><div class="tags">{t}</div></header>
  <main>{body}</main>
  <footer><span>{sources}</span><span>{FOOTER}</span><span>{n} / {N_PAGES - 1}</span></footer>
</section>"""


def card(inner, cls="", tag=None):
    tg = f'<span class="ctag ctag-{tag.lower().split()[0]}">{tag}</span>' if tag else ""
    return f'<div class="card {cls}">{tg}{inner}</div>'


def img(src, tag, cap=""):
    return card(f'<figure><img src="{src}"/>{f"<figcaption>{cap}</figcaption>" if cap else ""}</figure>', "fig", tag)


def tile(label, value, text, tag):
    return card(f'<div class="label">{label}</div><div class="big">{value}</div><p>{text}</p>', "tile", tag)


def table(cols, rows, cls="small"):
    return (f'<table class="{cls}"><tr>' + "".join(f"<th>{c}</th>" for c in cols) + "</tr>" +
            "".join("<tr>" + "".join(f"<td>{v}</td>" for v in r) + "</tr>" for r in rows) + "</table>")


# ------------------------------------------------------------------ pages
def p0(f, ch):
    fc, mk, cr, at = f["forecast"], f["marketing"], f["credit"], f["atm"]
    qs = ["How many new mortgages and deposits should a Belgian bank expect next year, and how sure can it be?",
          "Who should a term-deposit campaign call first, without cheating on the data?",
          "Who is likely to default on credit, and can the decision be explained and defended?",
          "Can a cash forecast for an ATM network be trusted in production, with the data engineers?",
          "What does the EU AI Act ask for a credit-scoring model, and what is still missing?"]
    body = f"""<div class="grid4 p0">
      {tile("FORECAST (MORTGAGE VOLUMES)", f"MASE {fc['mase_ets']:.2f}", f"ETS, 12 rolling origins, 1-12 months ahead: MAPE {pct(fc['mape_ets'], 1)} vs {pct(fc['mape_snaive'], 1)} for 'same month last year'", "PUBLIC DATA")}
      {tile("TARGETING GAIN", f"{mk['lift_top20']:.1f}x", f"calling the top 20% by score reaches {pct(mk['gain_top20'])} of subscribers, without the leaky call duration", "PUBLIC DATA")}
      {tile("CREDIT MODEL", f"AUC {cr['auc_lr']:.2f}", f"interpretable scorecard (Gini {cr['gini_lr']:.2f}); calibrated within {cr['cal_max_gap'] * 100:.0f} points in every group; Brier {cr['brier_lr']:.3f}", "PUBLIC DATA")}
      {tile("DRIFT DETECTION", f"{at['drift_days_to_detect']} days", f"to flag a -15% fall in mall ATM demand after the model was frozen (CUSUM alert on {pd.Timestamp(at['drift_detect_mall']):%d %b %Y})", "SIMULATED")}
    </div>
    <div class="grid3 p0">
      {card('<h2>Five questions</h2><ol class="qs">' + ''.join(f'<li>{q}</li>' for q in qs) + '</ol>')}
      {card(f'''<h2>Five recommendations for decision-makers</h2><ol class="reco">
        <li><b>Plan mortgage volumes with ranges, not one number.</b> With a stable rate, about {bn(fc['next12_stable_m'])} of new mortgages in the next 12 months (last 12: {bn(fc['last12_actual_m'])}); ±50 bp moves it to {bn(fc['next12_plus50_m'])}-{bn(fc['next12_minus50_m'])}, an effect that is real but poorly measured.</li>
        <li><b>Call fewer people, better.</b> Clients with a past success and mobile numbers first; stop after 3-4 calls. Never use call length to score.</li>
        <li><b>Use the explainable scorecard with a cost-based cut-off</b> ({cr['threshold_best']:.2f} instead of 0.50): expected cost per client {pct(cr['cost_best'] / cr['cost_at_050'] - 1, sign=True)}; a person reviews every decline.</li>
        <li><b>Write a data contract with the data engineers</b> (0 vs missing, duplicates, freshness) and monitor drift on two levels; forecast-driven ATM refills cut visits by {pct(1 - at['refill']['forecast']['visits'] / at['refill']['fixed']['visits'])}.</li>
        <li><b>Treat credit scoring as high-risk under the AI Act</b> (Annex III, point 5(b)): model card, logs, human oversight and a fundamental-rights impact assessment before go-live.</li></ol>''', '', 'PUBLIC DATA + SIMULATED')}
      {card(f'''<h2>Method in three lines</h2>
        <p>1. <b>Public data</b>: 3 ECB series for Belgium ({fc['n_months']} months, {fc['first_month']} to {fc['last_month']}), two UCI datasets (CC BY 4.0, Portugal 2008-2010 and Taiwan 2005, not Belgian clients), the AI Act text, Belgian public holidays.</p>
        <p>2. <b>Simulated data</b>: 60 ATMs of a fictitious "Bank B" in Belgium, 2 years daily, with 8 hidden events (data errors, a closure, a festival, a holiday, a drift).</p>
        <p>3. <b>Tools</b>: Python (statsmodels, scikit-learn), SQL (DuckDB) with tests, one notebook, an interactive dashboard.</p>
        <p class="note">Built for a junior data-scientist role in an international bank in Brussels. Simulated figures show how the methods behave; they are not any bank's numbers. Data read on {READ_ON}.</p>''')}
    </div>"""
    return page(0, TITLE, "A junior data scientist answers three business questions with models that are accurate, explained and documented, on data made reliable with the data engineers.",
                ["OVERVIEW"], body, f"ECB Data Portal, UCI ML Repository, EUR-Lex / Publications Office, Nager.Date · read {READ_ON}")


def p1(f, ch):
    fc = f["forecast"]
    dp = fc["deposits"]
    rows = [("Build statistical and forecasting models", "ETS, SARIMAX with the rate, seasonal naive; logistic scorecard and gradient boosting; backtests", "2, 3, 4"),
            ("Analyse data to answer business teams", "Which clients say yes; what drives default; where ATM demand moves", "3, 4, 5"),
            ("Present clear recommendations to decision-makers", "One-page memo, plain-language answers, cost-based choices", "0, 3, 4"),
            ("Work with data engineers on data reliability", "Data contract, 8 declared checks, SQL staging with tests, issues log", "5"),
            ("Plus: production projects", "Frozen model, drift monitor, runbook, refill policy", "5"),
            ("Plus: EU AI Act", "Credit model treated as high-risk: model card and article-by-article checklist", "6")]
    body = f"""<div class="grid-1-1-1 tall">
      {card('<h2>The four missions and two assets of the role, and where this study shows them</h2>' + table(["Mission", "What the study does", "Page"], rows) +
            '<p class="note">Source: the job posting (junior data scientist, permanent, full remote, based in Brussels; Python or R and SQL; statistics and modelling; ability to explain; bachelor degree or equivalent). The bank is not named in the posting and is not guessed here.</p>')}
      {img(ch['deposits'], 'PUBLIC DATA', f"ECB BSI.M.BE.N.A.L21.A.1.U2.2250.Z01.E, stocks, EUR millions (UNIT_MULT = 6), read {READ_ON}.")}
      {img(ch['rate_volume'], 'PUBLIC DATA', f"ECB MIR.M.BE.B.A2C.A.R.A.2250.EUR.N (rate, %) and MIR.M.BE.B.A2C.A.B.A.2250.EUR.N (new business, EUR millions, UNIT_MULT = 6), read {READ_ON}.")}
    </div>
    <div class="grid3 auto">
      {card(f'''<h2>Deposits: up, then down</h2><p>Household overnight deposits in Belgium grew from {bn(dp['first_value_m'])} (2015-01) to a peak of <b>{bn(dp['peak_value_m'])}</b> in {dp['peak_month']}, then fell to <b>{bn(dp['last_value_m'])}</b> in {dp['last_month']} ({dp['drop_peak_to_last_pct']:.0f}%).</p>''', '', 'PUBLIC DATA')}
      {card(f'''<h2>Mortgage rate: 1.43% to 3.90%</h2><p>The rate on new mortgages went from a low of <b>{fc['rate_min']:.2f}%</b> ({fc['rate_min_month']}) to a high of <b>{fc['rate_max']:.2f}%</b> ({fc['rate_max_month']}); it was {fc['last_rate']:.2f}% in {fc['last_month']}. New volumes: {', '.join(f'€{v / 1000:.2f} bn' for v in fc['vol_last_3'])} in Jul-Sep 2026.</p>''', '', 'PUBLIC DATA')}
      {card('''<h2>What we describe, and what we do not</h2><p>Changes in level are described by date and size only. This study does not claim a cause for the fall in deposits: no official source giving one was used here.</p>''')}
    </div>"""
    return page(1, f"The role asks for forecasts, models and clear advice; the Belgian market moved a lot: deposits {dp['drop_peak_to_last_pct']:.0f}% from their 2022 peak, mortgage rates up from 1.43% to 3.90%",
                "The missions of the job posting, what this study shows for each, and the public Belgian context it starts from.",
                ["PUBLIC DATA"], body, f"Job posting; ECB Data Portal (BSI, MIR) · read {READ_ON}")


def p2(f, ch):
    fc = f["forecast"]
    dp = fc["deposits"]
    m = pd.read_csv(PROC / "fc_metrics.csv").set_index("model")
    rows = [(k, pct(m.loc[k, "mape"], 1), f"{m.loc[k, 'mase']:.2f}", "-" if pd.isna(m.loc[k, "cov80"]) else pct(m.loc[k, "cov80"]),
             "-" if pd.isna(m.loc[k, "cov95"]) else pct(m.loc[k, "cov95"])) for k in ("ETS", "SARIMAX + rate", "Seasonal naive")]
    lo, hi = fc["rate_effect_ci95_pct"]
    body = f"""<div class="grid-1-1-1">
      {img(ch['mape_by_h'], 'PUBLIC DATA', f"Rolling origins {fc['origins']} (12), each forecasting 1-12 months ahead; error on the actual ECB values.")}
      {img(ch['scenarios'], 'PUBLIC DATA', "SARIMAX(1,1,1)(0,1,1,12) on log volume with the new-mortgage rate as exogenous input, fitted on 2015-01 to 2026-09; rate held flat at the scenario level.")}
      {card(f'''<h2>Backtest (new mortgage volumes)</h2>''' + table(["Model", "MAPE", "MASE", "80% int.", "95% int."], rows) + f'''
        <p class="note">MASE &lt; 1: better than the in-sample error of "same month last year". Interval columns: share of actual values inside the interval (target 80% and 95%).</p>
        <ul class="facts"><li><b>ETS wins</b> ({pct(fc['mape_ets'], 1)}); adding the rate (SARIMAX) helps at 1-2 months but not beyond. Both beat the naive rule.</li>
        <li><b>Intervals are too wide</b>: they hold {pct(fc['cov80_ets'])} of actuals instead of 80%. Safe for planning, but they can be narrowed.</li>
        <li><b>Rate effect</b>: about {fc['rate_effect_pct_per_100bp']:.0f}% volume for +1 point of rate, 95% CI {lo:.0f}% to {hi:.0f}%: the sign is clear, the size is not.</li></ul>''', '', 'PUBLIC DATA')}
    </div>
    <div class="grid3 auto">
      {card(f'''<h2>Three rate scenarios, next 12 months</h2><p>Stable at {fc['last_rate']:.2f}%: <b>{bn(fc['next12_stable_m'])}</b> · -50 bp: <b>{bn(fc['next12_minus50_m'])}</b> · +50 bp: <b>{bn(fc['next12_plus50_m'])}</b>. Last 12 months actual: {bn(fc['last12_actual_m'])}.</p>''', '', 'PUBLIC DATA')}
      {card(f'''<h2>A dated break in deposits</h2><p>A two-trend fit places the turn in <b>{dp['break_month']}</b>: about {dp['growth_before_pct_yr']:+.0f}% a year before, {dp['growth_after_pct_yr']:+.0f}% after (Chow F = {dp['chow_F']:.0f}; the date was searched, so this describes, it does not prove). Level peak: {dp['peak_month']}.</p>''', '', 'PUBLIC DATA')}
      {card(f'''<h2>What we cannot forecast</h2><p>Breaks like this one: on deposits, the simple "last value" rule (MAPE {pct(fc['dep_mape_naive'], 1)}) is as good as ETS ({pct(fc['dep_mape_ets'], 1)}). Rate decisions are scenarios, not forecasts. Monthly data gives few points (141).</p>''')}
    </div>"""
    return page(2, f"ETS forecasts Belgian mortgage volumes with {pct(fc['mape_ets'], 1)} error up to a year ahead; the rate matters, but the size of its effect is uncertain",
                "Three models compared on 12 rolling origins; 80% and 95% intervals; three rate scenarios; a dated break in deposits.",
                ["PUBLIC DATA"], body, f"ECB Data Portal: BSI and MIR series for Belgium, monthly, read {READ_ON} · code: src/forecast_bank_series.py")


def p3(f, ch):
    mk = f["marketing"]
    body = f"""<div class="grid-1-1-1">
      {img(ch['gain'], 'PUBLIC DATA', f"UCI Bank Marketing, stratified 80/20 split, {mk['n_test']:,} test calls; final model: {mk['final_model'].lower()}, no call duration, no age or marital status.")}
      {img(ch['segments'], 'PUBLIC DATA', "Share of calls ending in a term-deposit subscription; sql/05_bank_marketing_business.sql (groups of 5 calls or more).")}
      {card(f'''<h2>The call-duration trap</h2>
        <p>The length of the call is only known <b>after</b> the call. Adding it lifts the AUC from <b>{mk['auc_final']:.2f}</b> to <b>{mk['auc_with_duration']:.2f}</b>: a model that "knows" the answer. It is excluded from the final model, and a SQL test checks it.</p>
        <h2>Robust beats clever when the world changes</h2>
        <p>On a random split, boosting edges the logistic model (AUC {mk['auc_gb']:.2f} vs {mk['auc_logistic']:.2f}). Trained on the earlier calls and tested on the latest ones, when the economy had changed (subscription rate {pct(mk['base_rate_oot'])} vs {pct(mk['base_rate_all'])} overall), boosting drops to {mk['auc_oot_gb']:.2f} and the logistic model keeps {mk['auc_oot_logistic']:.2f}.</p>
        <p class="note">Data: a Portuguese bank's phone campaigns, May 2008 - Nov 2010 (UCI id 222, CC BY 4.0). Not Belgian clients; the method transfers, the rates do not.</p>''', '', 'PUBLIC DATA')}
    </div>
    <div class="grid3 auto">
      {card(f'''<h2>Campaign recommendation 1</h2><p><b>Score, then call the top 20%</b>: {pct(mk['gain_top20'])} of subscribers for a fifth of the calls ({mk['lift_top20']:.1f}x random; {pct(mk['precision_top20'])} of those calls end in a yes).</p>''', '', 'PUBLIC DATA')}
      {card('''<h2>Campaign recommendation 2</h2><p><b>Start with past successes and mobile numbers</b>; cap at 3-4 calls per client: the 5th call converts about half as often as the 1st.</p>''', '', 'PUBLIC DATA')}
      {card(f'''<h2>Campaign recommendation 3</h2><p><b>Prefer the logistic model and retrain before each campaign</b>: it is easier to explain and held up better when conditions changed. Selection rates by age band are checked in aggregate (notebook).</p>''', '', 'PUBLIC DATA')}
    </div>"""
    return page(3, f"Calling the top 20% of clients by score reaches {pct(mk['gain_top20'])} of subscribers - without using the call duration, which is only known after the call",
                "A targeting model for a term-deposit campaign: gain over random calls, the leak to avoid, and what the data says about who says yes.",
                ["PUBLIC DATA"], body, "UCI Machine Learning Repository, Bank Marketing (id 222), CC BY 4.0 · code: src/bank_marketing_model.py, sql/05")


def p4(f, ch):
    cr = f["credit"]
    ab = cr["acc_by_age"]
    body = f"""<div class="grid4 fill">
      {img(ch['calibration'], 'PUBLIC DATA')}
      {img(ch['cost_curve'], 'PUBLIC DATA')}
      {img(ch['importance'], 'PUBLIC DATA')}
      {img(ch['fairness'], 'PUBLIC DATA')}
    </div>
    <div class="grid4 auto">
      {card(f'''<h2>Accurate enough, and explainable</h2><p>Scorecard on 6 binned inputs: AUC <b>{cr['auc_lr']:.2f}</b>, Gini {cr['gini_lr']:.2f}, KS {cr['ks_lr']:.2f}. The boosting challenger gains only {cr['auc_gb'] - cr['auc_lr']:.2f} AUC (KS {cr['ks_gb']:.2f}): not worth losing a points table a credit officer can read ({cr['scorecard_points_range'][0]}-{cr['scorecard_points_range'][1]} points).</p>''', '', 'PUBLIC DATA')}
      {card(f'''<h2>Calibrated: a 20% is a 20%</h2><p>Predicted and observed default rates differ by at most <b>{cr['cal_max_gap'] * 100:.0f} points</b> in each of 10 groups. Brier {cr['brier_lr']:.3f} vs {cr['brier_base']:.3f} for "everyone gets the average".</p>''', '', 'PUBLIC DATA')}
      {card(f'''<h2>A cut-off set by cost, not by habit</h2><p>Assumed cost: a missed default = 5, a good client declined = 1. Best cut-off <b>{cr['threshold_best']:.2f}</b> (theory 1/6 = {cr['threshold_theory']:.2f}): cost {cr['cost_best']:.2f} per client vs {cr['cost_at_050']:.2f} at 0.50 and {cr['cost_accept_all']:.2f} accepting all. It accepts {pct(cr['acceptance_at_best'])}.</p>''', '', 'PUBLIC DATA')}
      {card(f'''<h2>Fairness, measured not assumed</h2><p>Sex and age are <b>not inputs</b>. Acceptance: women {pct(cr['acc_female'])}, men {pct(cr['acc_male'])}; by age {pct(ab['<30'])} (&lt;30) to {pct(ab['30-39'])} (30-39), ratio {min(ab.values()) / max(ab.values()):.2f}. Younger clients' good payers are declined more often ({pct(cr['gd_by_age']['<30'])} vs {pct(cr['gd_by_age']['30-39'])}): to review. Smallest group: {cr['min_group_n']:,}.</p>''', '', 'PUBLIC DATA')}
    </div>"""
    return page(4, f"An explainable credit scorecard (AUC {cr['auc_lr']:.2f}) that is calibrated, uses a cost-based cut-off and is checked for fairness by sex and age",
                f"UCI Default of Credit Card Clients: {cr['n_clients']:,} card holders in Taiwan, 2005 (CC BY 4.0, not Belgian clients); 70/30 stratified split, {cr['n_test']:,} test clients; default rate {pct(cr['default_rate'], 1)}.",
                ["PUBLIC DATA"], body, f"UCI ML Repository, Default of Credit Card Clients (id 350), CC BY 4.0 · score stability: PSI {cr['psi_aug_sep']:.2f} Aug vs Sept 2005, {cr['psi_stress']:.2f} under a simulated stress · code: src/credit_default_model.py, sql/06")


def p5(f, ch):
    at = f["atm"]
    dq = pd.read_csv(PROC / "dq_report.csv")
    short = {"unique (date, atm_id)": "Duplicates after a file reload (2 Jun)", "zero vs missing": "0 EUR recorded during a feed outage (12-13 Mar)",
             "required fields not null": "Required fields present", "freshness (< 08:00 next day)": "Late files (feed outage)",
             "rows per day = active ATMs": "Rows per day = active ATMs", "no rows after decommissioning": "No rows after ATM037 closed (15 May)",
             "extreme values explained": "Festival days kept as events, 9 spikes reviewed", "network-level drop vs last week": "Holiday drops (Easter Monday): no alert"}
    rows = [(f'<span class="st st-{r.status.lower()}">{r.status}</span>', short.get(r.check, r.check), f"{r.rows_affected}") for r in dq.itertuples()]
    s = at["simpson"]
    a36, ref = at["atm036"], at["refill"]
    body = f"""<div class="grid4 fill">
      {card('<h2>Data checks agreed with the data engineers</h2>' + table(["Status", "Check", "Rows"], rows) + '<p class="note">src/data_quality.py → dq_report.csv; fixes in sql/01 (dedupe, 0 → NULL); 8 SQL tests pass.</p>', '', 'SIMULATED')}
      {img(ch['easter'], 'SIMULATED')}
      {img(ch['drift'], 'SIMULATED')}
      {img(ch['validation'], 'SIMULATED')}
    </div>
    <div class="grid4 auto">
      {card(f'''<h2>The model, honestly measured</h2><p>Global gradient boosting, 7 days ahead, {at['n_origins']} weekly rolling origins: MAPE <b>{pct(at['mape_model'], 1)}</b> vs {pct(at['mape_naive'], 1)} for "same day last week". A first version that shuffled days and used yesterday's value showed {pct(at['mape_v1_random_lag1'], 1)}: too good to be true.</p>''', '', 'SIMULATED')}
      {card(f'''<h2>Simpson's paradox</h2><p>Overall, Flanders looks better than Brussels (MAPE {pct(s['Flanders|ALL'], 1)} vs {pct(s['Brussels|ALL'], 1)}), yet it is <b>worse for every site type</b> (stations {pct(s['Flanders|station'], 1)} vs {pct(s['Brussels|station'], 1)}): Brussels simply has more stations, the hardest sites.</p>''', '', 'SIMULATED')}
      {card(f'''<h2>A closure, a festival, a drift</h2><p>ATM037 closed: without a transfer rule its neighbour ATM036 is under-forecast (MAPE {pct(a36['mape_without'])} → {pct(a36['mape_with_transfer'])} with it). Festival days: {pct(at['festival']['mape_model'])} error with an event feature vs {pct(at['festival']['mape_naive'])} naive. Rural sites raised a short end-of-summer alert that cleared by {pd.Timestamp(at['drift_detect_all']['rural_back_below_watch']):%d %b}; malls stayed {pct(at['drift_detect_all']['mall_bias_sep15_oct31'])}: retrain.</p>''', '', 'SIMULATED')}
      {card(f'''<h2>Refill on forecast, not on calendar</h2><p>Sept-Oct, 59 ATMs: forecast-driven refills need <b>{ref['forecast']['visits']:.0f}</b> visits vs {ref['fixed']['visits']:.0f} (Mon + Thu), for {ref['forecast']['stockout_hours']:.0f} stock-out hours in total; assumed cost €{ref['forecast']['cost_eur'] / 1000:.0f}k vs €{ref['fixed']['cost_eur'] / 1000:.0f}k.</p>''', '', 'SIMULATED')}
    </div>"""
    return page(5, f"From model to production: the data checks catch the real errors, ignore Easter Monday, and the monitor flags a mall drift in {at['drift_days_to_detect']} days",
                "SIMULATED network of 60 ATMs of a fictitious \"Bank B\" in Belgium (Dec 2024 - Oct 2026) with 8 hidden events; real Belgian public holidays.",
                ["SIMULATED"], body, "Simulated data (src/simulate_atm.py, seed 42) · Belgian public holidays: Nager.Date · code: src/data_quality.py, src/atm_forecast.py, sql/01-04, 99_tests")


def p6(f, ch):
    c = pd.read_csv(PROC / "ai_act_citations.csv").set_index("ref")
    t = lambda a: c.loc[a, "title"]
    rows = [("Art. 6(2) + Annex III 5(b)", "High-risk: creditworthiness / credit score", "Use case documented in the model card", "Legal confirmation that the scorecard is an 'AI system' (Art. 3(1)) in scope"),
            ("Art. 9", t("Article 9"), "Risks listed: drift, unfair outcomes, misuse of the cut-off", "Formal risk register, owner, review cycle"),
            ("Art. 10", t("Article 10"), "Data source, licence, split, bias check by sex and age", "Real applicant data, representativeness for Belgium"),
            ("Art. 11", t("Article 11"), "Model card, code, backtest, scorecard table", "Annex IV technical file, version control of data"),
            ("Art. 12", t("Article 12"), "Not covered (study)", "Automatic logs of inputs, score, decision, overrides"),
            ("Art. 13", t("Article 13"), "Plain-language memo, limits, intended use", "Instructions for use for the deployer"),
            ("Art. 14", t("Article 14"), "Every decline reviewed by a person (design choice)", "Override process, training, four-eyes rule"),
            ("Art. 15", t("Article 15"), "AUC, calibration, PSI stress test", "Accuracy levels declared, robustness and security tests"),
            ("Art. 26-27", "Deployer duties; fundamental rights impact assessment", "Fairness metrics as an input", "FRIA by the bank before first use (Art. 27(1) names 5(b))"),
            ("Art. 72 / 86", "Post-market monitoring; right to explanation", "PSI and drift monitor; points per variable", "Monitoring plan; explanation letter to the client")]
    body = f"""<div class="grid-2-1">
      {card(f'''<h2>AI Act checklist for the credit model (Regulation (EU) 2024/1689)</h2>''' + table(["Ref.", "Obligation (title in the text)", "This study", "Missing for a real launch"], rows, "ai") +
            f'''<p class="note">Recital 58: "{c.loc['Recital 58', 'title']}". Annex III 5(b) excludes systems used to detect financial fraud. Art. 113: "{c.loc['Article 113 (application)', 'title']}" (with listed exceptions). Text read on {READ_ON} from the Publications Office (CELEX 32024R1689); later amendments not checked. <b>Not legal advice.</b></p>''', '', 'PUBLIC DATA')}
      <div class="stack">
      {card(f'''<h2>Sources and licences</h2><ul class="small">
        <li>ECB Data Portal: BSI.M.BE.N.A.L21.A.1.U2.2250.Z01.E; MIR.M.BE.B.A2C.A.R.A.2250.EUR.N; MIR.M.BE.B.A2C.A.B.A.2250.EUR.N (EUR millions, UNIT_MULT = 6; rate in %), 2015-01 to 2026-09.</li>
        <li>UCI Bank Marketing (id 222) and Default of Credit Card Clients (id 350), CC BY 4.0: Portugal 2008-2010 and Taiwan 2005, not Belgian clients.</li>
        <li>Regulation (EU) 2024/1689; Belgian public holidays (Nager.Date, 10 statutory days kept).</li>
        <li>Simulated: "Bank B" ATM network, seed 42; assumptions in docs/assumptions.md.</li></ul>''')}
      {card('''<h2>Limits</h2><ul class="small">
        <li>Public datasets are old and foreign; models show the method, not Belgian risk levels.</li>
        <li>141 monthly points: rate effect measured with a wide interval; breaks cannot be forecast.</li>
        <li>Cost matrices, transfer share and refill costs are assumptions to be set with the business.</li>
        <li>Simulated ATM data has the patterns we put in it; real data will be messier.</li></ul>''')}
      {card(f'''<h2>AI note</h2><p class="small">{AI_NOTE}</p>''')}
      </div>
    </div>"""
    return page(6, "AI Act, methods and limits: the credit model is high-risk under Annex III; the study covers documentation, accuracy, fairness and monitoring, and lists what a launch still needs",
                "Article-by-article checklist (titles quoted from the Regulation), sources and licences, limits of the study.",
                ["PUBLIC DATA"], body, "Regulation (EU) 2024/1689 (publications.europa.eu, CELEX 32024R1689) · docs/ai_act_checklist.md, docs/model_card_credit_default.md")


CSS = """
@page { size: 1600px 900px; margin: 0; }
* { box-sizing: border-box; }
body { margin: 0; font-family: 'Segoe UI', Arial, sans-serif; color: #0B0B0B; background: #F4F4F2; }
.page { width: 1600px; height: 900px; padding: 28px 44px 20px; display: flex; flex-direction: column; page-break-after: always; overflow: hidden; background: #F4F4F2; }
header { display: flex; justify-content: space-between; align-items: flex-start; gap: 30px; }
h1 { font-size: 25px; margin: 0 0 5px; font-weight: 700; line-height: 1.15; max-width: 1340px; }
.sub { margin: 0; color: #52514E; font-size: 14.5px; max-width: 1340px; }
.tags { display: flex; gap: 6px; }
.tag, .ctag { font-size: 12px; font-weight: 700; letter-spacing: .08em; padding: 5px 10px; border-radius: 4px; white-space: nowrap; color: #52514E; }
.ctag { position: absolute; top: 8px; right: 10px; font-size: 9.5px; padding: 2px 6px; }
.tag-public, .ctag-public { background: #E3EEFB; color: #1C5CAB; } .tag-simulated, .ctag-simulated { background: #FBE9E0; color: #9A3B12; } .tag-overview { color: #52514E; background: #E8E7E2; }
main { flex: 1; display: flex; flex-direction: column; gap: 12px; margin-top: 12px; min-height: 0; }
footer { display: flex; justify-content: space-between; gap: 20px; font-size: 11px; color: #898781; margin-top: 8px; }
.card { position: relative; background: #FFFFFF; border: 1px solid #E1E0D9; border-radius: 8px; padding: 11px 15px; min-height: 0; overflow: hidden; }
.card h2 { font-size: 15.5px; margin: 0 0 5px; padding-right: 90px; }
.card p, .card li { font-size: 13px; line-height: 1.38; margin: 3px 0; color: #2B2A27; }
.card ul, .card ol { padding-left: 18px; margin: 4px 0; }
.fig { padding: 8px 10px 6px; }
.grid3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; flex: 1; min-height: 0; }
.grid4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.grid4.fill { flex: 1; min-height: 0; }
.grid-2-1 { display: grid; grid-template-columns: 1.75fr 1fr; gap: 12px; flex: 1; min-height: 0; }
.grid-1-1-1 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; flex: 1; min-height: 0; }
.stack { display: flex; flex-direction: column; gap: 12px; min-height: 0; }
figure { margin: 0; height: 100%; display: flex; flex-direction: column; }
figure img { width: 100%; flex: 1; min-height: 0; object-fit: contain; }
figcaption { font-size: 11px; color: #52514E; margin-top: 3px; }
.tile .label { font-size: 12px; font-weight: 700; color: #52514E; letter-spacing: .04em; }
.tile .big { font-size: 38px; font-weight: 700; margin: 2px 0; color: #0B0B0B; }
.tile p { font-size: 13px; color: #52514E; }
.auto { flex: 0 0 auto !important; } .tall { flex: 1.25 !important; }
.qs li { font-size: 14.5px !important; margin: 8px 0; } .reco li { font-size: 13.3px !important; margin: 5px 0; }
table { border-collapse: collapse; width: 100%; font-size: 12.5px; }
th { text-align: left; color: #52514E; font-weight: 600; border-bottom: 1px solid #E1E0D9; padding: 4px 6px; }
td { border-bottom: 1px solid #EFEEE9; padding: 4px 6px; vertical-align: top; }
table.small, .small, .small li { font-size: 12px !important; }
.note { font-size: 11px !important; color: #6B6A65 !important; }
.facts li { font-size: 13px !important; margin: 5px 0; }
.p0 .card p, .p0 .card li { font-size: 15px !important; line-height: 1.45; } .p0 .qs li { font-size: 16.5px !important; margin: 12px 0; }
.p0 .card h2 { font-size: 18px; } .p0 .tile p { font-size: 14px !important; } .p0 .note { font-size: 12.5px !important; }
table.ai { font-size: 14px; } table.ai td, table.ai th { padding: 7px 7px; }
.stack .card li, .stack .card p { font-size: 13.5px !important; }
.st { font-size: 10.5px; font-weight: 700; padding: 2px 6px; border-radius: 3px; }
.st-pass { background: #E1F4EC; color: #0E7A52; } .st-warn { background: #FFF1D6; color: #8A5A00; } .st-fail { background: #FBE3E3; color: #A32626; }
"""


def build_html(tmp: Path) -> Path:
    ch = charts.build_all()
    f = load_findings()
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Bank data science case study</title><style>{CSS}</style></head><body>
{''.join(p(f, ch) for p in [p0, p1, p2, p3, p4, p5, p6])}
</body></html>"""
    shutil.copytree(REP / "img", tmp / "img", dirs_exist_ok=True)
    out = tmp / "report.html"
    out.write_text(html, encoding="utf-8")
    return out


def find_browser() -> str:
    for c in [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              shutil.which("msedge") or "", r"C:\Program Files\Google\Chrome\Application\chrome.exe", shutil.which("google-chrome") or "",
              shutil.which("chromium") or ""]:
        if c and Path(c).exists():
            return c
    raise FileNotFoundError("Edge or Chrome is needed to print the PDF")


def print_pdf(html: Path, tmp: Path) -> Path:
    pdf, raw = REP / PDF_NAME, tmp / "_print.pdf"
    profile = tempfile.mkdtemp()
    subprocess.run([find_browser(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--user-data-dir={profile}",
                    "--run-all-compositor-stages-before-draw", "--virtual-time-budget=5000",
                    f"--print-to-pdf={raw}", html.as_uri()], check=True, timeout=180)
    last = -1
    for _ in range(120):
        time.sleep(1)
        size = raw.stat().st_size if raw.exists() else -1
        if size > 0 and size == last:
            break
        last = size
    shutil.rmtree(profile, ignore_errors=True)
    reader, writer = PdfReader(str(raw)), PdfWriter()
    for pg in reader.pages:
        writer.add_page(pg)
    writer.add_metadata({"/Title": "Bank data science case study - forecast, model, explain", "/Author": "", "/Creator": "", "/Producer": "",
                         "/Subject": "", "/Keywords": ""})
    with open(pdf, "wb") as fh:
        writer.write(fh)
    return pdf


def main():
    REP.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    try:
        pdf = print_pdf(build_html(tmp), tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("written", pdf.relative_to(ROOT), len(PdfReader(str(pdf)).pages), "pages")


if __name__ == "__main__":
    main()
