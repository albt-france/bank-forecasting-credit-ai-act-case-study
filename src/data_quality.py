"""Declared data-quality checks on the ATM feed (SIMULATED), as agreed with the data engineers (docs/data_contract_atm.md).

Each check returns PASS, WARN or FAIL with the number of affected rows and the owner who fixes it.
    python src/data_quality.py
Output: data/processed/dq_report.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SIM, PROC = ROOT / "data" / "sim", ROOT / "data" / "processed"


def main():
    d = pd.read_parquet(SIM / "atm_daily.parquet")
    m = pd.read_parquet(SIM / "atm_master.parquet")
    fl = pd.read_parquet(SIM / "feed_log.parquet")
    ev = pd.read_parquet(SIM / "local_events.parquet")
    h = pd.read_csv(PROC / "holidays_be.csv")
    hol = set(pd.to_datetime(h[h.statutory].date))
    res = []

    def add(check, status, rows, detail, owner):
        res.append({"check": check, "status": status, "rows_affected": int(rows), "detail": detail, "owner": owner})

    # 1. uniqueness of (date, atm_id)
    dup = d.duplicated(["date", "atm_id"], keep="first")
    days = sorted(d.loc[dup, "date"].dt.date.astype(str).unique())
    add("unique (date, atm_id)", "FAIL" if dup.any() else "PASS", dup.sum(),
        f"duplicate rows on {', '.join(days)}; fix: deduplicate in staging (sql/01), reload guard in the loader", "data engineering")
    # 2. zero versus missing: an ATM in service (0 h out of service) with 0 transactions all day is not a real zero
    z = (d.withdrawals_eur == 0) & (d.n_transactions == 0) & (d.out_of_service_hours == 0)
    zd = sorted(d.loc[z, "date"].dt.date.astype(str).unique())
    add("zero vs missing", "FAIL" if z.any() else "PASS", z.sum(),
        f"{d.loc[z, 'atm_id'].nunique()} ATMs report 0 EUR and 0 transactions while in service on {', '.join(zd)}; set to NULL (sql/01)",
        "data engineering")
    # 3. nulls in required fields
    nn = d[["date", "atm_id", "withdrawals_eur", "n_transactions"]].isna().sum().sum()
    add("required fields not null", "FAIL" if nn else "PASS", nn, "date, atm_id, withdrawals_eur, n_transactions", "data engineering")
    # 4. freshness: the daily file must arrive before 08:00 the next day
    sw = fl[fl.source_system == "atm_switch"].copy()
    sw["delay_h"] = (sw.arrival_ts - sw.date).dt.total_seconds() / 3600 - 24
    late = sw[sw.delay_h > 8]
    add("freshness (< 08:00 next day)", "WARN" if len(late) else "PASS", len(late),
        f"late files: {', '.join(late.date.dt.date.astype(str))} (up to {late.delay_h.max():.0f} h after 00:00 next day)" if len(late) else "all on time",
        "data engineering")
    # 5. volume: rows per day must equal the number of active ATMs in the master table
    active = lambda day: int(((m.opened <= day) & (m.decommissioned.isna() | (m.decommissioned > day))).sum())
    vol = d.groupby("date").size()
    exp = pd.Series({k: active(k) for k in vol.index})
    bad = vol[vol != exp]
    add("rows per day = active ATMs", "FAIL" if len(bad) else "PASS", len(bad),
        "; ".join(f"{k.date()}: {v} rows vs {exp[k]} expected" for k, v in bad.items()) or "row count follows the master table (59 ATMs after 15 May 2026)",
        "data engineering")
    # 6. retired ATMs: no rows after decommissioning
    dd = d.merge(m[["atm_id", "decommissioned"]], on="atm_id")
    after = dd[dd.decommissioned.notna() & (dd.date >= dd.decommissioned)]
    add("no rows after decommissioning", "FAIL" if len(after) else "PASS", len(after),
        "ATM037 decommissioned 2026-05-15; its station neighbour ATM036 takes part of the demand (feature 'neighbour_closed')", "data science")
    # 7. extreme values: > 2.5x the ATM's median for the same weekday; matched to the local events calendar
    c = d.drop_duplicates(["date", "atm_id"]).copy()
    c["dow"] = c.date.dt.dayofweek
    med = c[c.withdrawals_eur > 0].groupby(["atm_id", "dow"]).withdrawals_eur.median().rename("med")
    c = c.join(med, on=["atm_id", "dow"])
    c["ratio"] = c.withdrawals_eur / c.med
    in_ev = np.zeros(len(c), bool)
    for e in ev.itertuples():
        in_ev |= (c.date >= e.date_from).values & (c.date <= e.date_to).values & c.atm_id.isin(e.atm_ids.split(",")).values
    spikes = c[~in_ev & (c.ratio > 2.5)]
    add("extreme values explained", "WARN", in_ev.sum() + len(spikes),
        f"local events calendar: annual festival ({', '.join(f'{a.date()} to {b.date()}' for a, b in zip(ev.date_from, ev.date_to))}), {in_ev.sum()} ATM-days at "
        f"x{c.ratio[in_ev].mean():.1f} the usual level: real demand, kept and modelled with an event feature; "
        f"outside events: {len(spikes)} isolated ATM-days above x2.5, sent to the branch network for review (not removed)",
        "business + data science")
    # 8. network drop: a day-level total below 60% of the same weekday a week before
    tot = c[c.withdrawals_eur > 0].groupby("date").withdrawals_eur.sum()
    ratio = tot / tot.shift(7)
    drops = ratio[ratio < 0.6]
    explained = [k for k in drops.index if k in hol]
    unexplained = [k for k in drops.index if k not in explained]
    add("network-level drop vs last week", "FAIL" if unexplained else "PASS", len(unexplained),
        f"{len(drops)} drops below 60%, all on statutory Belgian public holidays, incl. Easter Monday 2026-04-06 "
        f"({', '.join(str(k.date()) for k in explained[:6])}{'...' if len(explained) > 6 else ''}): no alert" if not unexplained
        else f"unexplained drops: {', '.join(str(k.date()) for k in unexplained)}", "data science")
    out = pd.DataFrame(res)
    out.to_csv(PROC / "dq_report.csv", index=False)
    print(out[["check", "status", "rows_affected"]].to_string(index=False))


if __name__ == "__main__":
    main()
