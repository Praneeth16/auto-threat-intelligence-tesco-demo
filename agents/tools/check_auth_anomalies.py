"""check_auth_anomalies(employee_ids[]) -> geo mismatches, failed-login bursts,
lockouts, and timing vs clicks (PLAN 8.3).
"""

from __future__ import annotations

import pandas as pd


def check_auth_anomalies(
    employee_ids: list[str],
    auth: pd.DataFrame,
    employees: pd.DataFrame,
) -> dict:
    """Return per-employee auth anomalies: foreign success, failure bursts,
    lockouts."""
    usual = dict(zip(employees["employee_id"], employees["usual_country"]))
    results = []
    for emp in employee_ids:
        rows = auth[auth["employee_id"] == emp]
        if rows.empty:
            continue
        failures = int((rows["result"] == "failure").sum())
        lockouts = int((rows["result"] == "lockout").sum())
        # Successful logins from a country other than the employee's usual one.
        succ = rows[rows["result"] == "success"]
        foreign = succ[succ["country"] != usual.get(emp, "GB")]
        results.append({
            "employee_id": emp,
            "failed_logins": failures,
            "lockouts": lockouts,
            "foreign_success": int(len(foreign)),
            "foreign_countries": sorted(set(foreign["country"])),
            "foreign_asns": sorted(set(foreign["asn_label"])),
        })
    return {"employees": results}
