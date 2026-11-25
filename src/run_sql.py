"""Run the DuckDB SQL files in order (sql/01..06, then 99_tests). A file is skipped while its input
(first line '-- requires: <path>') does not exist yet; each model script calls run_all() again at its end.
    python src/run_sql.py
Database: data/bank.duckdb (local, rebuilt from the files each run).
"""
import os
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "sql"


def run_all(verbose=True):
    os.chdir(ROOT)
    con = duckdb.connect(str(ROOT / "data" / "bank.duckdb"))
    failed = []
    for f in sorted(SQL.glob("*.sql")):
        text = f.read_text(encoding="utf-8")
        req = text.splitlines()[0].replace("-- requires:", "").strip()
        if not (ROOT / req).exists():
            if verbose:
                print(f"[skip] {f.name}: needs {req}")
            continue
        if f.name.startswith("99"):
            body = "\n".join(l for l in text.splitlines() if not l.strip().startswith("--"))
            for stmt in [s for s in body.split(";") if "SELECT" in s.upper()]:
                test, n = con.execute(stmt).fetchone()
                if n:
                    failed.append(f"{test}: {n}")
                if verbose:
                    print(f"[test] {'PASS' if n == 0 else 'FAIL'} {test}")
        else:
            con.execute(text)
            if verbose:
                print(f"[ok] {f.name}")
    con.close()
    if failed:
        sys.exit("SQL tests failed: " + "; ".join(failed))


if __name__ == "__main__":
    run_all()
