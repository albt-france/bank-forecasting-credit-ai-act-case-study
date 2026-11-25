"""SIMULATED data: daily cash withdrawals of a fictitious network of 60 ATMs of "Bank B" in Belgium,
1 Dec 2024 - 31 Oct 2026, with 8 hidden events (data/_hidden_truth.csv, local only, never published).

Calibration (all assumptions in docs/assumptions.md): real Belgian public holidays (Nager.Date), day-of-week and
start-of-month (salary) effects, December and summer seasonality, slow decline of cash use (-4% a year).
    python src/simulate_atm.py
Outputs: data/sim/atm_daily, atm_master, feed_log, refill_costs, local_events (.parquet)
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT / "data" / "sim"
rng = np.random.default_rng(42)
START, END = pd.Timestamp("2024-12-01"), pd.Timestamp("2026-10-31")

# ---- network: Brussels has many stations (hard to forecast), Flanders many rural and city sites (easy)
MIX = {"Brussels": {"station": 9, "city_centre": 3, "mall": 2, "rural": 1},
       "Flanders": {"station": 3, "city_centre": 8, "mall": 6, "rural": 10},
       "Wallonia": {"station": 3, "city_centre": 5, "mall": 3, "rural": 7}}
LEVEL = {"station": 9000, "city_centre": 7000, "mall": 8000, "rural": 3000}     # EUR / day, mean level
NOISE = {"station": 0.26, "city_centre": 0.12, "mall": 0.13, "rural": 0.10}      # log-normal sigma
REGION_NOISE = {"Brussels": 1.0, "Flanders": 1.12, "Wallonia": 1.05}             # within a site type, Flanders is noisier
DOW = np.array([0.95, 0.90, 0.95, 1.00, 1.25, 1.15, 0.70])                        # Mon..Sun
DOW_STATION = np.array([1.10, 1.05, 1.05, 1.10, 1.20, 0.75, 0.60])
TREND_PER_YEAR = -0.04
AR = 0.6                                                                          # day-to-day autocorrelation of the noise
HOLIDAY_FACTOR = 0.55                                                             # -45% on a public holiday


def master():
    rows = [(r, s) for r, mix in MIX.items() for s, n in mix.items() for _ in range(n)]
    order = rng.permutation(len(rows))
    rows = [rows[i] for i in order]
    # ATM036 and ATM037 sit in the same Brussels station
    idx = [i for i, x in enumerate(rows) if x == ("Brussels", "station") and i not in (35, 36)]
    for target in (35, 36):
        if rows[target] != ("Brussels", "station"):
            src = idx.pop(0)
            rows[target], rows[src] = rows[src], rows[target]
    m = pd.DataFrame(rows, columns=["region", "site_type"])
    m.insert(0, "atm_id", [f"ATM{i:03d}" for i in range(1, 61)])
    m["location_code"] = [f"{r[:2].upper()}-{s[:3].upper()}-{i:02d}" for i, (r, s) in enumerate(rows, 1)]
    m.loc[m.atm_id.isin(["ATM036", "ATM037"]), "location_code"] = "BR-STA-GARE1"
    m["opened"] = pd.Timestamp("2019-01-01")
    m["decommissioned"] = pd.NaT
    m.loc[m.atm_id == "ATM037", "decommissioned"] = pd.Timestamp("2026-05-15")
    m["base_level"] = [LEVEL[s] * rng.lognormal(0, 0.25) for s in m.site_type]
    m["cassette_capacity_eur"] = (np.ceil(m.base_level * 4.5 / 5000) * 5000).astype(int)
    return m


def calendar(hol):
    d = pd.DataFrame({"date": pd.date_range(START, END)})
    d["dow"] = d.date.dt.dayofweek
    d["holiday"] = d.date.isin(hol)
    d["som"] = d.date.dt.day.isin([1, 2, 3]) | ((d.date.dt.day == 4) & (d.dow == 0))
    m, day = d.date.dt.month, d.date.dt.day
    d["season"] = 1.0 + np.where(m == 12, 0.06 + 0.10 * (day >= 15) * (day <= 24), 0) + np.where(m.isin([7, 8]), 0.04, 0)
    d["trend"] = (1 + TREND_PER_YEAR) ** ((d.date - START).dt.days / 365.25)
    return d


def main():
    SIM.mkdir(parents=True, exist_ok=True)
    h = pd.read_csv(ROOT / "data" / "processed" / "holidays_be.csv")
    hol = pd.to_datetime(h[h.statutory].date)
    m, cal = master(), calendar(set(hol))
    out = []
    fest25, fest = pd.date_range("2025-07-17", "2025-07-20"), pd.date_range("2026-07-16", "2026-07-19")   # annual festival
    fest_atms = m[(m.region == "Flanders") & (m.site_type.isin(["city_centre", "station"]))].atm_id.head(4).tolist()
    for a in m.itertuples():
        dow = DOW_STATION if a.site_type == "station" else DOW
        mu = a.base_level * dow[cal.dow] * cal.season * cal.trend * np.where(cal.som, 1.15, 1.0)
        mu = mu * np.where(cal.holiday, HOLIDAY_FACTOR, 1.0)
        if a.site_type == "rural":
            mu = mu * np.where(cal.date.dt.month.isin([7, 8]), 1.06, 1.0)
        if a.site_type == "city_centre":
            mu = mu * np.where(cal.date.dt.month.isin([7, 8]), 0.90, 1.0)
        # event 6: drift, mall demand -15% from Sept 2026 (assumed new payment habit)
        if a.site_type == "mall":
            mu = mu * np.where(cal.date >= "2026-09-01", 0.85, 1.0)
        # event 4: 4-day annual festival, x3 on 4 Flanders ATMs (2025 edition gives the model a precedent)
        if a.atm_id in fest_atms:
            mu = mu * np.where(cal.date.isin(fest) | cal.date.isin(fest25), 3.0, 1.0)
        sig = NOISE[a.site_type] * REGION_NOISE[a.region]
        z = rng.normal(0, 1, len(cal))
        e = np.zeros(len(cal))                      # AR(1) noise: busy days cluster (weather, local life)
        for t in range(len(cal)):
            e[t] = (AR * e[t - 1] if t else 0) + np.sqrt(1 - AR ** 2) * z[t]
        w = mu * np.exp(sig * e - sig ** 2 / 2)
        out.append(pd.DataFrame({"date": cal.date, "atm_id": a.atm_id, "withdrawals_eur": w}))
    df = pd.concat(out, ignore_index=True)
    # event 3: ATM037 removed on 15 May 2026, 60% of its demand moves to ATM036 (same station)
    cut = pd.Timestamp("2026-05-15")
    moved = df[(df.atm_id == "ATM037") & (df.date >= cut)].withdrawals_eur.values * 0.60
    i36 = (df.atm_id == "ATM036") & (df.date >= cut)
    df.loc[i36, "withdrawals_eur"] = df.loc[i36, "withdrawals_eur"].values + moved
    df = df[~((df.atm_id == "ATM037") & (df.date >= cut))]
    df["withdrawals_eur"] = (df.withdrawals_eur / 10).round() * 10           # EUR 10 notes and more
    ticket = rng.normal(95, 6, len(df)).clip(70, 130)
    df["n_transactions"] = np.maximum(1, (df.withdrawals_eur / ticket).round()).astype(int)
    df = df.merge(m[["atm_id", "cassette_capacity_eur"]], on="atm_id")
    # refills: twice a week (Mon, Thu) or when the cassette falls under 20%; stock-outs give out-of-service hours
    df = df.sort_values(["atm_id", "date"]).reset_index(drop=True)
    w, cap, dts = df.withdrawals_eur.to_numpy().copy(), df.cassette_capacity_eur.to_numpy(), df.date.dt.dayofweek.to_numpy()
    refill, oos = np.zeros(len(df), int), np.zeros(len(df))
    for _, idx in df.groupby("atm_id").indices.items():
        bal = None
        for i in idx:
            if bal is None or dts[i] in (0, 3) or bal < 0.2 * cap[i]:
                bal, refill[i] = cap[i], 1
            if w[i] > bal:
                oos[i] = round(24 * (1 - bal / w[i]), 1)
                w[i] = bal
            bal -= w[i]
    df["withdrawals_eur"], df["refill_flag"], df["out_of_service_hours"] = w, refill, oos
    small = rng.random(len(df)) < 0.01                                      # small technical outages
    df.loc[small, "out_of_service_hours"] += rng.integers(1, 4, small.sum())
    # event 1: feed outage 12-13 Mar 2026, 18 ATMs recorded as 0 instead of missing
    out_atms = rng.choice(m.atm_id[m.atm_id != "ATM037"], 18, replace=False)
    i1 = df.date.isin(pd.to_datetime(["2026-03-12", "2026-03-13"])) & df.atm_id.isin(out_atms)
    df.loc[i1, ["withdrawals_eur", "n_transactions", "refill_flag", "out_of_service_hours"]] = 0
    # event 2: file reloaded on 2 Jun 2026, rows of 9 ATMs duplicated
    dup_atms = rng.choice(m.atm_id[m.atm_id != "ATM037"], 9, replace=False)
    dups = df[(df.date == "2026-06-02") & df.atm_id.isin(dup_atms)]
    df = pd.concat([df, dups]).sort_values(["date", "atm_id"]).reset_index(drop=True)
    df["withdrawals_eur"] = df.withdrawals_eur.astype(float)
    df.to_parquet(SIM / "atm_daily.parquet", index=False)
    m.drop(columns="base_level").to_parquet(SIM / "atm_master.parquet", index=False)
    # feed log: one delivery per day and source; arrival next day ~06:00, late on the outage days
    fl = df.groupby("date").size().rename("rows").reset_index()
    fl["source_system"], fl["null_rate"] = "atm_switch", 0.0
    fl["arrival_ts"] = fl.date + pd.Timedelta(days=1) + pd.to_timedelta(rng.integers(330, 400, len(fl)), unit="m")
    late = fl.date.isin(pd.to_datetime(["2026-03-12", "2026-03-13"]))
    fl.loc[late, "arrival_ts"] = fl.loc[late, "date"] + pd.Timedelta(days=2, hours=14)
    rf = df.groupby("date").refill_flag.sum().rename("rows").reset_index()
    rf["source_system"], rf["null_rate"] = "cit_refills", 0.0
    rf["arrival_ts"] = rf.date + pd.Timedelta(days=1, hours=8)
    pd.concat([fl, rf])[["date", "source_system", "rows", "null_rate", "arrival_ts"]].to_parquet(SIM / "feed_log.parquet", index=False)
    pd.DataFrame([{"cost_per_refill_visit_eur": 150.0, "cost_per_stockout_hour_eur": 40.0,
                   "cash_holding_cost_per_year": 0.03, "note": "assumption, see docs/assumptions.md"}]).to_parquet(SIM / "refill_costs.parquet", index=False)
    pd.DataFrame([{"date_from": fr[0], "date_to": fr[-1], "region": "Flanders", "atm_ids": ",".join(fest_atms),
                   "description": "Large 4-day summer festival (fictitious, annual), known in advance by the branch network"} for fr in (fest25, fest)]).to_parquet(SIM / "local_events.parquet", index=False)
    truth = [
        (1, "data", "2026-03-12/13", ",".join(sorted(out_atms)), "feed outage recorded as 0 EUR instead of missing"),
        (2, "data", "2026-06-02", ",".join(sorted(dup_atms)), "file reloaded, rows duplicated"),
        (3, "network", "2026-05-15", "ATM037->ATM036", "ATM037 removed, 60% of its demand moves to ATM036"),
        (4, "business", "2026-07-16..19", ",".join(fest_atms), "festival, demand x3: real, model as event"),
        (5, "false signal", "2026-04-06", "all", "Easter Monday, -45%: public holiday, no alert"),
        (6, "drift", "2026-09-01", "mall sites", "demand -15% from Sept 2026, monitor must detect within 3 weeks"),
        (7, "Simpson", "all", "Brussels vs Flanders", "Flanders better overall, worse within each site type"),
        (8, "validation", "all", "all", "random day split leaks; rolling-origin gives the real error"),
    ]
    pd.DataFrame(truth, columns=["event", "kind", "when", "who", "what"]).to_csv(ROOT / "data" / "_hidden_truth.csv", index=False)
    print("atm_daily", df.shape, "| ATMs", df.atm_id.nunique(), "| zero rows", int((df.withdrawals_eur == 0).sum()),
          "| stock-out days", int((df.out_of_service_hours > 4).sum()), "| festival ATMs", fest_atms)


if __name__ == "__main__":
    main()
