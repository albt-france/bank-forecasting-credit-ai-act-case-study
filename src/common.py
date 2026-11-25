"""Shared paths and the findings store (data/processed/findings.json): every number in the report and the
dashboard is read from there, so the documents match the code."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC, SIM = ROOT / "data" / "raw", ROOT / "data" / "processed", ROOT / "data" / "sim"
FINDINGS = PROC / "findings.json"


def save_findings(section: str, values: dict):
    f = json.loads(FINDINGS.read_text(encoding="utf-8")) if FINDINGS.exists() else {}
    f[section] = values
    FINDINGS.write_text(json.dumps(f, indent=1, default=float), encoding="utf-8")


def load_findings() -> dict:
    return json.loads(FINDINGS.read_text(encoding="utf-8"))
