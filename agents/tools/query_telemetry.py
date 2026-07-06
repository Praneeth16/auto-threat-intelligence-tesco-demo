"""query_telemetry(domain) -> dns/proxy/email hits (counts + samples).

Pure-logic core takes the bronze frames so it is testable offline; the UC
function wrapper reads the same tables in-workspace. All indicators are returned
plain here (data-layer matching); the agent defangs on render.
"""

from __future__ import annotations

import pandas as pd


def query_telemetry(
    domain: str,
    dns: pd.DataFrame,
    proxy: pd.DataFrame,
    email: pd.DataFrame,
    sample_n: int = 5,
) -> dict:
    """Return dns/proxy/email activity for a domain: counts, users, samples."""
    dns_hits = dns[dns["query_domain"] == domain]
    proxy_hits = proxy[proxy["domain"] == domain]
    email_hits = email[email["url_clicked"].fillna("").str.contains(domain, regex=False)]

    users = set(dns_hits["employee_id"]) | set(proxy_hits["employee_id"])
    posts = proxy_hits[proxy_hits["method"] == "POST"]

    return {
        "domain": domain,
        "dns_hits": int(len(dns_hits)),
        "proxy_hits": int(len(proxy_hits)),
        "email_clicks": int(len(email_hits)),
        "distinct_users": len({u for u in users if pd.notna(u)}),
        "credential_posts": int(len(posts)),
        "sample_users": sorted({u for u in users if pd.notna(u)})[:sample_n],
    }
