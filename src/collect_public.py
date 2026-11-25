"""Collect the public sources (ECB, UCI, EU AI Act, Belgian public holidays) into data/raw/ (cache, never published)
and write small tidy extracts to data/processed/ plus a source log (URL, date, size, status).

    python src/collect_public.py
"""
import io
import re
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd

from polite import cached

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
ECB = "https://data-api.ecb.europa.eu/service/data/"
SERIES = {  # name: (dataset, key)
    "deposits_hh_overnight": ("BSI", "M.BE.N.A.L21.A.1.U2.2250.Z01.E"),
    "mortgage_rate_new": ("MIR", "M.BE.B.A2C.A.R.A.2250.EUR.N"),
    "mortgage_volume_new": ("MIR", "M.BE.B.A2C.A.B.A.2250.EUR.N"),
}
UCI = {
    "bank_marketing": "https://archive.ics.uci.edu/static/public/222/bank+marketing.zip",
    "credit_default": "https://archive.ics.uci.edu/static/public/350/default+of+credit+card+clients.zip",
}
AI_ACT = "https://publications.europa.eu/resource/celex/32024R1689"
STATUTORY = {"New Year's Day", "Easter Monday", "Labour Day", "Ascension Day", "Whit Monday", "Belgian National Day",
             "Assumption Day", "All Saints' Day", "Armistice Day", "Christmas Day"}
HOLIDAYS = "https://date.nager.at/api/v3/PublicHolidays/{y}/BE"
log = []


def fetch(name, url, path, headers=None):
    p, status, from_cache = cached(url, path, headers)
    log.append({"source": name, "url": url, "status": status, "bytes": p.stat().st_size if p.exists() else 0,
                "retrieved": date.today().isoformat(), "from_cache": from_cache})
    if status != 200:
        raise RuntimeError(f"{name}: HTTP {status}")
    return p


def ecb():
    rows = []
    for name, (ds, key) in SERIES.items():
        url = f"{ECB}{ds}/{key}?format=csvdata&startPeriod=2015-01"
        d = pd.read_csv(fetch(f"ECB {ds}.{key}", url, RAW / f"ecb_{name}.csv"))
        d = d[["TIME_PERIOD", "OBS_VALUE", "UNIT_MULT", "TITLE"]].rename(columns={"TIME_PERIOD": "month", "OBS_VALUE": "value"})
        d["series"], d["key"] = name, f"{ds}.{key}"
        rows.append(d)
    out = pd.concat(rows)
    out.to_csv(PROC / "ecb_series.csv", index=False)
    w = out.pivot(index="month", columns="series", values="value")
    print("ECB", w.shape, "months", w.index.min(), "->", w.index.max())


def uci():
    z = zipfile.ZipFile(fetch("UCI Bank Marketing (id 222)", UCI["bank_marketing"], RAW / "bank_marketing.zip"))
    inner = zipfile.ZipFile(io.BytesIO(z.read("bank-additional.zip")))
    name = next(n for n in inner.namelist() if n.endswith("bank-additional-full.csv"))
    bm = pd.read_csv(io.BytesIO(inner.read(name)), sep=";")
    bm.to_parquet(RAW / "bank_marketing.parquet", index=False)
    z = zipfile.ZipFile(fetch("UCI Default of Credit Card Clients (id 350)", UCI["credit_default"], RAW / "credit_default.zip"))
    xls = next(n for n in z.namelist() if n.endswith(".xls"))
    cd = pd.read_excel(io.BytesIO(z.read(xls)), header=1)   # double header: keep the second row
    cd.to_parquet(RAW / "credit_default.parquet", index=False)
    print("UCI bank marketing", bm.shape, "credit default", cd.shape)


def ai_act():
    p = fetch("EU AI Act, Regulation (EU) 2024/1689", AI_ACT, RAW / "ai_act.html",
              {"Accept": "application/xhtml+xml;q=1, text/html;q=0.9", "Accept-Language": "eng"})
    html = p.read_text(encoding="utf-8", errors="ignore")
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;|&#160;", " ", text)
    text = re.sub(r"\s+", " ", text)
    (RAW / "ai_act.txt").write_text(text, encoding="utf-8")
    cites = []
    for art in [6, 9, 10, 11, 12, 13, 14, 15, 17, 26, 27, 43, 49, 72, 86]:
        m = re.search(rf"Article {art} ([A-Z][^.]{{3,120}}?) (?:1\.|The |Providers|Deployers|Without|High-risk|In)", text)
        cites.append({"ref": f"Article {art}", "title": m.group(1).strip() if m else ""})
    m = re.search(r"\(b\) AI systems intended to be used to evaluate the creditworthiness of natural persons[^;]*;", text)
    cites.append({"ref": "Annex III, point 5(b)", "title": m.group(0).strip(" ;") if m else ""})
    m = re.search(r"AI systems used to evaluate the credit score or creditworthiness of natural persons should be classified as high-risk AI systems[^,]*", text)
    cites.append({"ref": "Recital 58", "title": m.group(0).strip() if m else ""})
    m = re.search(r"It shall apply from 2 August 2026\.", text)
    cites.append({"ref": "Article 113 (application)", "title": m.group(0) if m else ""})
    pd.DataFrame(cites).to_csv(PROC / "ai_act_citations.csv", index=False)
    print("AI Act text", len(text), "chars; citations found", sum(bool(c["title"]) for c in cites), "/", len(cites))


def holidays():
    rows = []
    for y in (2024, 2025, 2026):
        p = fetch(f"Nager.Date Belgian holidays {y}", HOLIDAYS.format(y=y), RAW / f"holidays_be_{y}.json")
        h = pd.read_json(p)
        rows.append(h[["date", "localName", "name", "global"]])
    out = pd.concat(rows)
    out = out[out["global"]].drop(columns="global")
    # Nager.Date also lists Good Friday, the day after Ascension and 26 December for BE; they are not among the
    # 10 statutory public holidays in Belgium, so they are kept with statutory = False (see docs/data_issues_log.md)
    out["statutory"] = out["name"].isin(STATUTORY)
    out.to_csv(PROC / "holidays_be.csv", index=False)
    print("holidays", len(out), "statutory", int(out.statutory.sum()))


if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    PROC.mkdir(parents=True, exist_ok=True)
    for f in (ecb, uci, ai_act, holidays):
        f()
    pd.DataFrame(log).to_csv(ROOT / "data" / "sources_log.csv", index=False)
