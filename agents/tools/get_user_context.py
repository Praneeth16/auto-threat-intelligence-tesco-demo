"""get_user_context(employee_ids[]) -> department, is_privileged, is_vip, groups
(PLAN 8.3). The business context that routes AP1 to tier-2 (Priya privileged).
"""

from __future__ import annotations

import pandas as pd


def get_user_context(employee_ids: list[str], employees: pd.DataFrame) -> dict:
    ctx = employees[employees["employee_id"].isin(employee_ids)]
    rows = []
    for _, e in ctx.iterrows():
        rows.append({
            "employee_id": e["employee_id"],
            "full_name": e["full_name"],
            "department": e["department"],
            "is_privileged": bool(e["is_privileged"]),
            "is_vip": bool(e["is_vip"]),
            "ad_groups": list(e["ad_groups"]),
        })
    return {"users": rows, "any_privileged": any(r["is_privileged"] for r in rows)}
