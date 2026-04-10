"""Smoke test for Google Apps Script logging endpoint.

Checks:
1. Endpoint reachability (GET)
2. POST payload acceptance
3. Redirect diagnostics

Note: Row-count verification requires Google Sheets API credentials and access.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Dict

import requests


APP_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwwYdWSiwyouO2etOI9xftWl-_js4lNQtRwYGjMb0-WE5Qc2vQW3o0Wqu2fjxBu2Cr_9A/exec"


@dataclass
class SmokeResult:
    check: str
    passed: bool
    detail: str


def build_test_payload() -> Dict[str, Any]:
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "participantID": "SMOKE_TEST_FREQ_ISI",
        "participantName": "SmokeTest",
        "schemaVersion": "stage2_freq_isi_v1",
        "totalBlocks": 1,
        "blockData": [
            {
                "blockNumber": 1,
                "frequency": 250,
                "isi": 200,
                "replication": 1,
                "threshold": 2.0,
                "thresholdUnit": "dB",
                "totalTrials": 30,
                "totalReversals": 6,
                "discardedReversals": 2,
                "usableReversals": 4,
                "trialHistory": [{"trialNumber": 1, "deltaI": 5.0, "correct": True}],
            }
        ],
    }


def check_get() -> SmokeResult:
    try:
        r = requests.get(APP_SCRIPT_URL, timeout=20)
        ok = r.status_code == 200 and "Psychoacoustic" in r.text
        return SmokeResult(
            check="GET reachability",
            passed=ok,
            detail=f"status={r.status_code}, body_preview={r.text[:80]!r}",
        )
    except Exception as exc:
        return SmokeResult("GET reachability", False, f"exception={exc}")


def check_post() -> SmokeResult:
    payload = build_test_payload()
    try:
        r = requests.post(
            APP_SCRIPT_URL,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=30,
            allow_redirects=True,
        )

        is_json = "application/json" in r.headers.get("Content-Type", "")
        detail = f"status={r.status_code}, final_url={r.url}, content_type={r.headers.get('Content-Type')}"

        if is_json:
            detail += f", response={r.text[:200]}"
        else:
            detail += f", body_preview={r.text[:120]!r}"

        # We consider this pass only when JSON success is returned.
        passed = is_json and "success" in r.text.lower()
        return SmokeResult("POST logging", passed, detail)
    except Exception as exc:
        return SmokeResult("POST logging", False, f"exception={exc}")


def main() -> None:
    results = [check_get(), check_post()]

    print("=" * 72)
    print("GOOGLE SHEETS PIPELINE SMOKE TEST")
    print("=" * 72)
    for res in results:
        status = "PASS" if res.passed else "FAIL"
        print(f"[{status}] {res.check}: {res.detail}")

    print("\nDIAGNOSTIC NOTES")
    print("- A GET pass only confirms endpoint visibility.")
    print("- POST must return JSON success to confirm write path.")
    print("- If POST fails or returns HTML, verify Apps Script deployment:")
    print("  1) Deploy as Web App")
    print("  2) Execute as: Me (owner)")
    print("  3) Who has access: Anyone")
    print("  4) Spreadsheet ID and sheet name are valid")
    print("  5) Re-deploy and update URL in experiment.js")


if __name__ == "__main__":
    main()
