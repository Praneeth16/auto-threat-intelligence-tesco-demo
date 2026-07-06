"""Telemetry generators: DNS, proxy, email, auth logs.

Builds benign background traffic plus the five planted attack paths. Every
attack-path fact (clicker counts, credential POSTs, failed-login bursts,
Priya's RO success) is planted here and recorded verbatim in ground_truth so it
is exactly rediscoverable.

All timestamps are offsets from REFERENCE_TS, computed when the world loads.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from datagen import config
from datagen.common import rng

# Column order for each bronze table (PLAN 5.6).
DNS_COLS = ["ts", "employee_id", "src_ip", "query_domain", "query_type",
            "response_ip", "source_tag"]
PROXY_COLS = ["ts", "employee_id", "src_ip", "method", "url", "domain",
              "status", "bytes_out", "bytes_in", "user_agent", "category"]
EMAIL_COLS = ["ts", "employee_id", "msg_id", "sender", "subject",
              "url_clicked", "action"]
AUTH_COLS = ["ts", "employee_id", "app", "result", "country", "asn_label", "device"]

_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) demo-agent/1.0"
_SOURCE_TAGS = ["corp", "vpn", "guest-wifi"]


@dataclass
class Telemetry:
    dns: pd.DataFrame
    proxy: pd.DataFrame
    email: pd.DataFrame
    auth: pd.DataFrame
    # Attack-path evidence captured for ground truth.
    attack_evidence: dict = field(default_factory=dict)


def _src_ip(r) -> str:
    return f"10.{r.randint(0, 40)}.{r.randint(0, 254)}.{r.randint(1, 254)}"


def _ts(reference_ts: pd.Timestamp, offset_days: float) -> pd.Timestamp:
    return reference_ts + pd.Timedelta(days=offset_days)


def _office_hours_offset(r, day_offset: float) -> float:
    """Return a day offset nudged into local office hours with weekend dips."""
    # Weight toward 08:00-18:00; occasional off-hours.
    hour = r.choices(
        population=list(range(24)),
        weights=[1, 1, 1, 1, 1, 2, 4, 8, 12, 14, 14, 12, 10, 12, 13, 12, 10, 8, 5, 3, 2, 2, 1, 1],
    )[0]
    minute = r.randint(0, 59)
    return day_offset + hour / 24.0 + minute / 1440.0


def _build_benign(employees: pd.DataFrame, benign_domains: list[str], reference_ts: pd.Timestamp):
    """Build benign background for all four tables up to near target counts."""
    r = rng("telemetry_benign")
    emp_ids = employees["employee_id"].tolist()
    emp_ip = {e: _src_ip(r) for e in emp_ids}
    emp_country = dict(zip(employees["employee_id"], employees["usual_country"]))

    dns_rows, proxy_rows, email_rows, auth_rows = [], [], [], []

    # Leave headroom for planted attack-path rows so exact totals land after.
    # Reserve headroom for planted attack-path rows so exact totals stay within
    # the +/-2% tolerance. Planted email is ~79 rows (60 wave + 17 clicks + 2
    # AP2), so keep the email reserve small enough to clear the lower bound.
    n_dns = config.BRONZE_DNS_ROWS - 200
    n_proxy = config.BRONZE_PROXY_ROWS - 100
    n_email = config.BRONZE_EMAIL_ROWS - 100
    n_auth = config.BRONZE_AUTH_ROWS - 100

    for _ in range(n_dns):
        emp = r.choice(emp_ids)
        day = -r.uniform(0, 14)
        dns_rows.append({
            "ts": _ts(reference_ts, _office_hours_offset(r, day)),
            "employee_id": emp,
            "src_ip": emp_ip[emp],
            "query_domain": r.choice(benign_domains),
            "query_type": r.choice(["A", "AAAA", "CNAME"]),
            "response_ip": _src_ip(r),
            "source_tag": r.choices(_SOURCE_TAGS, weights=[8, 2, 1])[0],
        })

    for _ in range(n_proxy):
        emp = r.choice(emp_ids)
        day = -r.uniform(0, 14)
        d = r.choice(benign_domains)
        proxy_rows.append({
            "ts": _ts(reference_ts, _office_hours_offset(r, day)),
            "employee_id": emp,
            "src_ip": emp_ip[emp],
            "method": r.choices(["GET", "POST"], weights=[9, 1])[0],
            "url": f"https://{d}/",
            "domain": d,
            "status": r.choices([200, 304, 404], weights=[8, 1, 1])[0],
            "bytes_out": r.randint(200, 1500),
            "bytes_in": r.randint(500, 50000),
            "user_agent": _USER_AGENT,
            "category": "general",
        })

    for _ in range(n_email):
        emp = r.choice(emp_ids)
        day = -r.uniform(0, 14)
        email_rows.append({
            "ts": _ts(reference_ts, _office_hours_offset(r, day)),
            "employee_id": emp,
            "msg_id": f"<{r.getrandbits(48):012x}@mail.example>",
            "sender": f"noreply@{r.choice(benign_domains)}",
            "subject": r.choice([
                "Weekly team sync notes", "Your order has shipped",
                "Payslip available", "Meeting reminder", "Newsletter",
            ]),
            "url_clicked": None,
            "action": r.choices(["delivered", "clicked", "reported"], weights=[7, 2, 1])[0],
        })

    # Base rate of scattered auth failures so AP bursts stand out.
    for _ in range(n_auth):
        emp = r.choice(emp_ids)
        day = -r.uniform(0, 14)
        auth_rows.append({
            "ts": _ts(reference_ts, _office_hours_offset(r, day)),
            "employee_id": emp,
            "app": r.choice(["vpn", "o365", "okta", "internal-portal"]),
            "result": r.choices(["success", "failure"], weights=[9, 1])[0],
            "country": emp_country[emp],
            "asn_label": "CorpISP-Demo",
            "device": r.choice(["managed-laptop", "managed-mobile"]),
        })

    return dns_rows, proxy_rows, email_rows, auth_rows, emp_ip, emp_country


def _plant_attack_paths(employees, dns_rows, proxy_rows, email_rows, auth_rows,
                        emp_ip, reference_ts):
    """Plant the five attack paths; return per-AP evidence for ground truth."""
    r = rng("telemetry_attack")
    emp_ids = employees["employee_id"].tolist()
    non_named = [e for e in emp_ids if e not in {"E0001", "E0002", "E0003"}]
    evidence: dict = {}

    def emp_src(emp):
        return emp_ip.get(emp, _src_ip(r))

    # ---- AP1: FreshCart hero -------------------------------------------
    ap1_domain = config.HERO_DOMAIN
    ap1_url = f"https://{ap1_domain}/wp-login-secure/index.php"
    # Recipients: 60 employees (email wave at T-2 09:14).
    recipients = [emp_ids[0]] + r.sample(non_named, k=config.AP1_EMAIL_RECIPIENTS - 1)
    wave_ts = _ts(reference_ts, -2) + pd.Timedelta(hours=9, minutes=14)
    for emp in recipients:
        email_rows.append({
            "ts": wave_ts,
            "employee_id": emp,
            "msg_id": f"<fc-{emp}@tesco-clubcard-support.example>",
            "sender": config.AP1_SENDER,
            "subject": config.AP1_EMAIL_SUBJECT,
            "url_clicked": None,
            "action": "delivered",
        })

    # Clickers: 17 distinct, including Priya (E0001). Clicks T-2 09:20..T-1 18:00.
    clickers = ["E0001"] + r.sample([e for e in recipients if e != "E0001"],
                                    k=config.AP1_CLICKERS - 1)
    click_start = _ts(reference_ts, -2) + pd.Timedelta(hours=9, minutes=20)
    click_end = _ts(reference_ts, -1) + pd.Timedelta(hours=18)
    span_seconds = int((click_end - click_start).total_seconds())
    click_times = {}
    for emp in clickers:
        click_ts = click_start + pd.Timedelta(seconds=r.randint(0, span_seconds))
        click_times[emp] = click_ts
        # email click action
        email_rows.append({
            "ts": click_ts,
            "employee_id": emp,
            "msg_id": f"<fc-click-{emp}@tesco-clubcard-support.example>",
            "sender": config.AP1_SENDER,
            "subject": config.AP1_EMAIL_SUBJECT,
            "url_clicked": ap1_url,
            "action": "clicked",
        })
        # matching proxy GET
        proxy_rows.append({
            "ts": click_ts + pd.Timedelta(seconds=r.randint(1, 30)),
            "employee_id": emp,
            "src_ip": emp_src(emp),
            "method": "GET",
            "url": ap1_url,
            "domain": ap1_domain,
            "status": 200,
            "bytes_out": r.randint(200, 500),
            "bytes_in": r.randint(1500, 6000),
            "user_agent": _USER_AGENT,
            "category": "uncategorized",
        })
        # matching DNS
        dns_rows.append({
            "ts": click_ts - pd.Timedelta(seconds=r.randint(1, 20)),
            "employee_id": emp,
            "src_ip": emp_src(emp),
            "query_domain": ap1_domain,
            "query_type": "A",
            "response_ip": "185.163.44.10",
            "source_tag": "corp",
        })

    # 3 of 17 submit credentials (Priya + 2 others): proxy POST ~200-400 bytes up.
    submitters = ["E0001"] + r.sample([e for e in clickers if e != "E0001"],
                                      k=config.AP1_CREDENTIAL_SUBMITTERS - 1)
    for emp in submitters:
        post_ts = click_times[emp] + pd.Timedelta(minutes=r.randint(1, 5))
        proxy_rows.append({
            "ts": post_ts,
            "employee_id": emp,
            "src_ip": emp_src(emp),
            "method": "POST",
            "url": ap1_url,
            "domain": ap1_domain,
            "status": 302,
            "bytes_out": r.randint(200, 400),
            "bytes_in": r.randint(200, 800),
            "user_agent": _USER_AGENT,
            "category": "uncategorized",
        })
        # 5-8 failed logins 20-45 min after click, then a lockout.
        n_fail = r.randint(config.AP1_FAILED_LOGIN_MIN, config.AP1_FAILED_LOGIN_MAX)
        delay = r.randint(config.AP1_FAILED_LOGIN_DELAY_MIN_MINUTES,
                          config.AP1_FAILED_LOGIN_DELAY_MAX_MINUTES)
        burst_start = click_times[emp] + pd.Timedelta(minutes=delay)
        for i in range(n_fail):
            auth_rows.append({
                "ts": burst_start + pd.Timedelta(minutes=i),
                "employee_id": emp,
                "app": "o365",
                "result": "failure",
                "country": "GB",
                "asn_label": "CorpISP-Demo",
                "device": "managed-laptop",
            })
        auth_rows.append({
            "ts": burst_start + pd.Timedelta(minutes=n_fail),
            "employee_id": emp,
            "app": "o365",
            "result": "lockout",
            "country": "GB",
            "asn_label": "CorpISP-Demo",
            "device": "managed-laptop",
        })

    # Priya: successful login T-1 22:37 from RO, GreyStack-Demo, unknown device.
    priya_success_ts = _ts(reference_ts, config.AP1_PRIYA_SUCCESS_OFFSET_DAYS) + pd.Timedelta(
        hours=config.AP1_PRIYA_SUCCESS_HOUR, minutes=config.AP1_PRIYA_SUCCESS_MINUTE
    )
    auth_rows.append({
        "ts": priya_success_ts,
        "employee_id": "E0001",
        "app": "o365",
        "result": "success",
        "country": config.AP1_PRIYA_SUCCESS_COUNTRY,
        "asn_label": config.AP1_PRIYA_SUCCESS_ASN,
        "device": "unknown",
    })
    evidence["AP1"] = {
        "domain": ap1_domain,
        "clickers": sorted(clickers),
        "submitters": sorted(submitters),
        "recipients": len(recipients),
    }

    # ---- AP2: BEC, Mark Whitfield (E0002) ------------------------------
    ap2_domain = "tesco-supplier-billing.com"
    ap2_url = f"https://{ap2_domain}/portal/login"
    ap2_click = _ts(reference_ts, -6) + pd.Timedelta(hours=11, minutes=9)
    email_rows.append({
        "ts": _ts(reference_ts, -6) + pd.Timedelta(hours=11, minutes=2),
        "employee_id": "E0002",
        "msg_id": "<sp-4471182@supplierpay.example>",
        "sender": "billing@tesco-supplier-billing.com",
        "subject": config.AP2_EMAIL_SUBJECT,
        "url_clicked": ap2_url,
        "action": "delivered",
    })
    email_rows.append({
        "ts": ap2_click,
        "employee_id": "E0002",
        "msg_id": "<sp-click-4471182@supplierpay.example>",
        "sender": "billing@tesco-supplier-billing.com",
        "subject": config.AP2_EMAIL_SUBJECT,
        "url_clicked": ap2_url,
        "action": "clicked",
    })
    dns_rows.append({
        "ts": ap2_click - pd.Timedelta(seconds=10),
        "employee_id": "E0002", "src_ip": emp_src("E0002"),
        "query_domain": ap2_domain, "query_type": "A",
        "response_ip": "45.148.121.20", "source_tag": "corp",
    })
    proxy_rows.append({
        "ts": ap2_click + pd.Timedelta(minutes=1),
        "employee_id": "E0002", "src_ip": emp_src("E0002"),
        "method": "POST", "url": ap2_url, "domain": ap2_domain,
        "status": 302, "bytes_out": r.randint(200, 400), "bytes_in": 400,
        "user_agent": _USER_AGENT, "category": "uncategorized",
    })
    auth_rows.append({
        "ts": _ts(reference_ts, -6) + pd.Timedelta(hours=17, minutes=40),
        "employee_id": "E0002", "app": "finance-portal", "result": "success",
        "country": config.AP2_SUCCESS_COUNTRY, "asn_label": "GreyStack-Demo",
        "device": "unknown",
    })
    evidence["AP2"] = {"domain": ap2_domain, "victim": "E0002"}

    # ---- AP3: feed-gap, DNS only (2 employees at T-4) ------------------
    ap3_domain = config.REPORT_ONLY_DOMAIN
    ap3_emps = r.sample(non_named, k=2)
    for emp in ap3_emps:
        dns_rows.append({
            "ts": _ts(reference_ts, -4) + pd.Timedelta(hours=r.randint(9, 17)),
            "employee_id": emp, "src_ip": emp_src(emp),
            "query_domain": ap3_domain, "query_type": "A",
            "response_ip": config.R14_IP, "source_tag": "corp",
        })
    evidence["AP3"] = {"domain": ap3_domain, "employees": sorted(ap3_emps)}

    # ---- AP4: fresh one, DNS T-1 (3 users) + T-0 (1 user) --------------
    ap4_domain = "tescobank-secure-auth.com"
    ap4_t1 = r.sample(non_named, k=3)
    ap4_t0 = r.sample([e for e in non_named if e not in ap4_t1], k=1)
    for emp in ap4_t1:
        dns_rows.append({
            "ts": _ts(reference_ts, -1) + pd.Timedelta(hours=14),
            "employee_id": emp, "src_ip": emp_src(emp),
            "query_domain": ap4_domain, "query_type": "A",
            "response_ip": "185.163.44.12", "source_tag": "corp",
        })
    for emp in ap4_t0:
        dns_rows.append({
            "ts": _ts(reference_ts, 0) + pd.Timedelta(hours=8),
            "employee_id": emp, "src_ip": emp_src(emp),
            "query_domain": ap4_domain, "query_type": "A",
            "response_ip": "185.163.44.12", "source_tag": "corp",
        })
    evidence["AP4"] = {"domain": ap4_domain, "users_t1": 3, "users_t0": 1}

    # ---- AP5: bookmark, Sophie (E0003) 9 visits T-3..T-1 ---------------
    ap5_domain = "tesco-rewards-login.com"
    ap5_url = f"https://{ap5_domain}/"
    for i in range(config.AP5_VISITS):
        # Spread across T-3..T-1.
        day = -3 + (i * 2.0 / max(1, config.AP5_VISITS - 1))  # -3..-1
        v_ts = _ts(reference_ts, _office_hours_offset(r, day))
        proxy_rows.append({
            "ts": v_ts, "employee_id": "E0003", "src_ip": emp_src("E0003"),
            "method": "GET", "url": ap5_url, "domain": ap5_domain,
            "status": 200, "bytes_out": 300, "bytes_in": 4000,
            "user_agent": _USER_AGENT, "category": "uncategorized",
        })
        dns_rows.append({
            "ts": v_ts - pd.Timedelta(seconds=5), "employee_id": "E0003",
            "src_ip": emp_src("E0003"), "query_domain": ap5_domain,
            "query_type": "A", "response_ip": "185.163.44.11", "source_tag": "corp",
        })
    evidence["AP5"] = {"domain": ap5_domain, "visitor": "E0003", "visits": config.AP5_VISITS}

    # ---- Counterexamples ------------------------------------------------
    # careers-verify: 1 DNS hit from guest-wifi.
    cv_emp = r.choice(non_named)
    dns_rows.append({
        "ts": _ts(reference_ts, -2) + pd.Timedelta(hours=12),
        "employee_id": cv_emp, "src_ip": emp_src(cv_emp),
        "query_domain": "tesco-careers-verify.com", "query_type": "A",
        "response_ip": "103.152.78.5", "source_tag": "guest-wifi",
    })
    # fans-forum: 3 benign visits.
    ff_emps = r.sample(non_named, k=3)
    for emp in ff_emps:
        proxy_rows.append({
            "ts": _ts(reference_ts, _office_hours_offset(r, -r.uniform(1, 5))),
            "employee_id": emp, "src_ip": emp_src(emp),
            "method": "GET", "url": f"https://{config.DECOY_DOMAIN}/",
            "domain": config.DECOY_DOMAIN, "status": 200,
            "bytes_out": 300, "bytes_in": 5000,
            "user_agent": _USER_AGENT, "category": "forums",
        })
    evidence["counterexamples"] = {
        "careers_verify_hits": 1,
        "fans_forum_visits": 3,
    }

    return evidence


def build_telemetry(employees: pd.DataFrame, benign_domains: list[str],
                    reference_ts: pd.Timestamp) -> Telemetry:
    """Build all four bronze tables plus attack-path ground-truth evidence."""
    dns_rows, proxy_rows, email_rows, auth_rows, emp_ip, _ = _build_benign(
        employees, benign_domains, reference_ts
    )
    evidence = _plant_attack_paths(
        employees, dns_rows, proxy_rows, email_rows, auth_rows, emp_ip, reference_ts
    )

    dns = pd.DataFrame(dns_rows, columns=DNS_COLS).sort_values("ts").reset_index(drop=True)
    proxy = pd.DataFrame(proxy_rows, columns=PROXY_COLS).sort_values("ts").reset_index(drop=True)
    email = pd.DataFrame(email_rows, columns=EMAIL_COLS).sort_values("ts").reset_index(drop=True)
    auth = pd.DataFrame(auth_rows, columns=AUTH_COLS).sort_values("ts").reset_index(drop=True)

    return Telemetry(dns=dns, proxy=proxy, email=email, auth=auth, attack_evidence=evidence)
