"""The 13 unstructured reports plus per-report ground truth.

Reports vary format and voice; extraction robustness is the point. R02/R04 are
fully defanged (hxxps / [.]). R14 carries the feed-gap domain and one IP present
in no feed. R15 carries one sender and one URL present in no feed and no
telemetry. Prose is competent vendor/analyst tone, not mad-libs, and stays
defanged where the plan requires it.

Each report has a matching ground_truth/R##.json with the planted entities.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from datagen import config
from datagen.common import defang


@dataclass
class Report:
    report_id: str
    fmt: str  # md | txt | html
    body: str
    ground_truth: dict = field(default_factory=dict)


def _gt(actors=None, iocs=None, ttps=None, brands=None, kits=None, detections=None):
    return {
        "actors": actors or [],
        "iocs": iocs or [],  # list of {value, type}
        "ttps": ttps or [],
        "targeted_brands": brands or [],
        "kit_ids": kits or [],
        "recommended_detections_present": detections or [],
    }


def _ioc(value, itype):
    return {"value": value, "type": itype}


def build_reports() -> list[Report]:
    """Return all 13 reports with ground truth (PLAN 5.7)."""
    reports: list[Report] = []
    hero = config.HERO_DOMAIN

    # ---- R01-R05, FreshCart (A) ----------------------------------------
    reports.append(Report(
        "R01", "md",
        f"""# RetailISAC Advisory: FreshCart credential phishing

Threat group TA-FreshCart is running a Clubcard rewards phishing operation
against UK grocery brand customers and staff. The lure claims loyalty points
expire within 48 hours and drives victims to a credential harvest page.

Confirmed infrastructure includes {hero} and tesco-rewards-login.com, both
served from AS208877. The kit fingerprint is fc-kit-v3 and the harvest path is
/wp-login-secure/. Observed technique maps to MITRE T1566.002 (spearphishing
link) with follow-on credential use under T1539.

Recommended detections: proxy URI contains /wp-login-secure/, and DNS queries
for the listed domains.
""",
        _gt(
            actors=["TA-FreshCart"],
            iocs=[_ioc(hero, "domain"), _ioc("tesco-rewards-login.com", "domain")],
            ttps=["T1566.002", "T1539"],
            brands=["tesco", "clubcard"],
            kits=["fc-kit-v3"],
            detections=["proxy_uri_wp_login_secure", "dns_freshcart_domains"],
        ),
    ))

    reports.append(Report(
        "R02", "txt",
        f"""FreshCart takedown notice (defanged)

Our DFIR team confirms an active credential harvest at {defang('https://' + hero)}.
The page posts stolen credentials over {defang('https://' + hero)}/wp-login-secure/.
A sibling host {defang('tescobank-secure-auth.com')} was registered more
recently and resolves to the same AS208877 block. Kit: fc-kit-v3.

Analysts should treat any staff submission to these hosts as a confirmed
credential compromise and force a reset.
""",
        _gt(
            actors=["TA-FreshCart"],
            iocs=[_ioc(hero, "domain"), _ioc("tescobank-secure-auth.com", "domain")],
            ttps=["T1566.002"],
            brands=["tesco", "clubcard"],
            kits=["fc-kit-v3"],
        ),
    ))

    reports.append(Report(
        "R03", "md",
        f"""# DFIR writeup: anatomy of a Clubcard phish

The operator sends a rewards-expiry email from rewards@{hero}. Victims who
click reach a cloned login. Three staff at one org submitted credentials and
saw failed logins within the hour, consistent with automated credential
stuffing from a foreign ASN.

The harvest path /wp-login-secure/index.php returns a 302 on submit. Payload
hashes match the fc-kit-v3 family.
""",
        _gt(
            actors=["TA-FreshCart"],
            iocs=[_ioc(hero, "domain"),
                  _ioc(f"https://{hero}/wp-login-secure/index.php", "url")],
            ttps=["T1566.002", "T1539"],
            brands=["tesco", "clubcard"],
            kits=["fc-kit-v3"],
        ),
    ))

    reports.append(Report(
        "R04", "html",
        f"""<html><body>
<h2>Social thread (defanged)</h2>
<p>Seeing a fresh Clubcard scam. Domain is {defang(hero)} and it is nasty.
Also spotted {defang('tesco-rewards-login.com')} on the same host.</p>
<p>Do not click. Report to your SOC. Kit looks like fc-kit-v3.</p>
</body></html>
""",
        _gt(
            iocs=[_ioc(hero, "domain"), _ioc("tesco-rewards-login.com", "domain")],
            brands=["tesco", "clubcard"],
            kits=["fc-kit-v3"],
        ),
    ))

    reports.append(Report(
        "R05", "txt",
        f"""Takedown email to registrar

Subject: Abuse report for {hero}

The domain {hero} hosts a phishing kit targeting Tesco Clubcard customers.
Registrar NameDodger LLC, registrant hostmaster@freshcart-ops.example. Please
suspend. Harvest path /wp-login-secure/. MITRE T1566.002.
""",
        _gt(
            iocs=[_ioc(hero, "domain")],
            ttps=["T1566.002"],
            brands=["tesco", "clubcard"],
            kits=["fc-kit-v3"],
        ),
    ))

    # ---- R06-R07, SupplierPay (B) --------------------------------------
    reports.append(Report(
        "R06", "md",
        """# Invoice fraud advisory: SupplierPay

A BEC operation targets accounts payable teams with updated bank detail
requests. Lure references a real-looking purchase order. Landing page is
tesco-supplier-billing.com/portal/login. Kit sp-kit-1. Successful logins have
been observed from anomalous geographies shortly after the click.
""",
        _gt(
            iocs=[_ioc("tesco-supplier-billing.com", "domain")],
            ttps=["T1566.002"],
            brands=["tesco"],
            kits=["sp-kit-1"],
        ),
    ))

    reports.append(Report(
        "R07", "txt",
        """Bank alert: supplier payment redirection

We are tracking supplier-impersonation fraud using tesco-supplier-billing.com.
Finance staff receive a bank-detail change request for an open PO. Verify any
such request out of band before paying.
""",
        _gt(
            iocs=[_ioc("tesco-supplier-billing.com", "domain")],
            brands=["tesco"],
            kits=["sp-kit-1"],
        ),
    ))

    # ---- R09-R10, CareerLure (C) ---------------------------------------
    reports.append(Report(
        "R09", "md",
        """# Consumer protection blog: fake recruitment scams

Jobseekers are being lured to tesco-careers-verify.com with a promise of fast
hiring. The site asks for identity verification and harvests personal data.
Kit cl-kit-2. Low enterprise relevance, but staff should be aware.
""",
        _gt(
            iocs=[_ioc("tesco-careers-verify.com", "domain")],
            brands=["tesco"],
            kits=["cl-kit-2"],
        ),
    ))

    reports.append(Report(
        "R10", "txt",
        """HR ISAC note: recruitment lure

A recruitment-themed phishing page at tesco-careers-verify.com is circulating.
Primarily a consumer threat. No evidence of enterprise credential targeting.
""",
        _gt(
            iocs=[_ioc("tesco-careers-verify.com", "domain")],
            brands=["tesco"],
        ),
    ))

    # ---- R14, feed-gap [exact] -----------------------------------------
    # Contains the report-only domain and one IP present in no feed. Defanged.
    r14_domain = config.REPORT_ONLY_DOMAIN
    r14_ip = config.R14_IP
    reports.append(Report(
        "R14", "txt",
        f"""Regional CERT Advisory 2026-114 (defanged)

Summary: a parcel-delivery themed phishing campaign is targeting UK retail
customers. The operators impersonate a well known grocer's parcel tracking
service. Unlike the widely reported Clubcard rewards campaign, this cluster has
not yet appeared in commercial threat feeds, so defenders relying only on feed
ingestion will not see it.

The primary domain is {defang(r14_domain)}. It resolves to {defang(r14_ip)},
a host on a bulletproof provider also seen serving unrelated malware. The lure
email links to a fake tracking page that asks for account login to "release" a
held parcel. No structured indicator for this campaign is currently published
by RetailISAC, VendorX, or the open CSV feeds.

Defenders should hunt their own DNS and proxy logs for {defang(r14_domain)}
directly, rather than waiting for a feed match. Early internal telemetry is the
only signal available for this cluster today.

Recommended action: add {defang(r14_domain)} and {defang(r14_ip)} to the
internal watch list and review any resolutions from the past week.
""",
        _gt(
            iocs=[_ioc(r14_domain, "domain"), _ioc(r14_ip, "ip")],
            ttps=["T1566.002"],
            brands=["tesco"],
            detections=["dns_hunt_parcel_tracking"],
        ),
    ))

    # ---- R15, exclusive-but-quiet [exact] ------------------------------
    # One sender + one URL in no feed and no telemetry; extraction still
    # enriches the watch list.
    r15_sender = "notices@tesco-account-hold.example"
    r15_url = "https://tesco-account-hold.example/verify"
    reports.append(Report(
        "R15", "md",
        f"""# Analyst note: quiet account-hold lure

We received a single sample of an account-hold phishing email. Sender is
{defang(r15_sender)} and the embedded link is {defang(r15_url)}. We have not
seen this domain in any feed and have no telemetry showing internal contact.

Logging here so the indicator is on the watch list if it resurfaces.
""",
        _gt(
            iocs=[_ioc(r15_sender, "email"), _ioc(r15_url, "url")],
            brands=["tesco"],
        ),
    ))

    # ---- R19-R20, unrelated noise --------------------------------------
    # Extraction must not hallucinate brand relevance; targeted_brands empty.
    reports.append(Report(
        "R19", "txt",
        """Threat bulletin: commodity ransomware crew

An unrelated ransomware affiliate is deploying a loader via malspam. No retail
targeting observed. Indicators are generic and rotate frequently. Included for
situational awareness only.
""",
        _gt(brands=[]),
    ))

    reports.append(Report(
        "R20", "md",
        """# Scanner activity roundup

Broad internet scanning from several hosting providers this week. Opportunistic,
not targeted. No brand impersonation. Nothing actionable for a specific
enterprise beyond normal perimeter hygiene.
""",
        _gt(brands=[]),
    ))

    return reports
