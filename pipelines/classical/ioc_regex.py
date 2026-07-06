"""Classical IOC regex pass over reports (PLAN 7.3, pass 1).

Runs iocextract over each report body to pull well-formed and defanged
indicators deterministically into silver_iocs_regex. Cheap, auditable, free,
no model call. This is the deterministic half of the regex-vs-agent contrast.
"""

from __future__ import annotations

import iocextract
import pandas as pd

REGEX_COLS = ["report_id", "indicator_value", "indicator_type", "method"]


def extract_from_text(text: str) -> list[tuple[str, str]]:
    """Return (value, type) pairs iocextract finds, refanged to plain form."""
    found: list[tuple[str, str]] = []
    # refang=True turns hxxps://x[.]com back into the plain matchable form.
    for url in iocextract.extract_urls(text, refang=True):
        found.append((url, "url"))
    for ip in iocextract.extract_ips(text, refang=True):
        found.append((ip, "ip"))
    for email in iocextract.extract_emails(text, refang=True):
        found.append((email, "email"))
    # Domains are not a first-class iocextract type; derive from URLs and any
    # bare defanged hostnames the URL extractor missed.
    return found


def build_silver_iocs_regex(reports: pd.DataFrame) -> pd.DataFrame:
    """Extract IOCs from every report body via iocextract.

    reports: frame with report_id and body columns (bronze_reports).
    """
    rows = []
    for _, r in reports.iterrows():
        seen = set()
        for value, itype in extract_from_text(r["body"]):
            key = (value, itype)
            if key in seen:
                continue
            seen.add(key)
            rows.append({
                "report_id": r["report_id"],
                "indicator_value": value,
                "indicator_type": itype,
                "method": "regex",
            })
    return pd.DataFrame(rows, columns=REGEX_COLS)
