"""Central configuration: counts, names, seeds, campaign and filler specs.

Every value marked [exact] in PLAN.md Section 5 lives here verbatim. The demo
script and validation suite depend on these; change them only alongside the
validation suite.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------
SEED = 42  # one RNG seed for all data (PLAN Section 0, rule 2)

# ---------------------------------------------------------------------------
# Safety and brand reference (PLAN 5.1)
# ---------------------------------------------------------------------------
# Synthetic employee email domain [exact]. Never @tesco.com for demo people.
EMPLOYEE_EMAIL_DOMAIN = "tesco-demo.example"

# Protected-brand reference (the legitimate premise) [exact].
PROTECTED_BRAND_DOMAINS = [
    "tesco.com",
    "tescobank.com",
    "tescoplc.com",
    "tescomobile.com",
    "tesco.ie",
]
PROTECTED_BRAND_TOKENS = ["clubcard", "tesco"]

# ---------------------------------------------------------------------------
# Scale (PLAN 4.5, 5.6)
# ---------------------------------------------------------------------------
N_EMPLOYEES = 200
N_PRIVILEGED = 12
N_VIP = 5

BRONZE_DNS_ROWS = 60_000
BRONZE_PROXY_ROWS = 25_000
BRONZE_EMAIL_ROWS = 6_000
BRONZE_AUTH_ROWS = 9_000

# Total structured IOCs across all feeds [exact] (PLAN 5.2).
TOTAL_STRUCTURED_IOCS = 455

# Row-count tolerance for validation (PLAN 13.1: within +/-2%).
ROW_COUNT_TOLERANCE = 0.02

# ---------------------------------------------------------------------------
# Offices and countries (PLAN 5.3)
# ---------------------------------------------------------------------------
# office_location -> usual_country
OFFICES = {
    "Welwyn Garden City": "GB",
    "London": "GB",
    "Dundee": "GB",
    "Bengaluru": "IN",
}

PRIVILEGED_GROUPS = ["Cloud-Admins", "Domain-Admins", "Payments-Ops"]

DEPARTMENTS = [
    "Cloud Platform",
    "Finance",
    "Customer Care",
    "Engineering",
    "Security",
    "HR",
    "Legal",
    "Marketing",
    "Supply Chain",
    "Retail Operations",
]


@dataclass(frozen=True)
class NamedEmployee:
    """A scripted character whose identity the storyline depends on [exact]."""

    employee_id: str
    full_name: str
    department: str
    job_title: str
    ad_groups: tuple[str, ...]
    office_location: str
    is_privileged: bool
    is_vip: bool


# Named characters [exact] (PLAN 5.3). Faker fills the remaining rows.
NAMED_EMPLOYEES = [
    NamedEmployee(
        employee_id="E0001",
        full_name="Priya Nair",
        department="Cloud Platform",
        job_title="Senior Cloud Platform Engineer",
        ad_groups=("Cloud-Admins",),
        office_location="Bengaluru",
        is_privileged=True,
        is_vip=False,
    ),
    NamedEmployee(
        employee_id="E0002",
        full_name="Mark Whitfield",
        department="Finance",
        job_title="Accounts Payable Analyst",
        # Deliberately NOT privileged, so AP1 stays the only privileged
        # finding in the top 5.
        ad_groups=("AP-Team",),
        office_location="Welwyn Garden City",
        is_privileged=False,
        is_vip=False,
    ),
    NamedEmployee(
        employee_id="E0003",
        full_name="Sophie Clarke",
        department="Customer Care",
        job_title="Customer Care Advisor",
        ad_groups=("CustomerCare-Agents",),
        office_location="Dundee",
        is_privileged=False,
        is_vip=False,
    ),
]

# ---------------------------------------------------------------------------
# Campaign universe (PLAN 5.2)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CampaignSpec:
    campaign_id: str
    name: str
    theme: str
    ioc_count: int
    hosting_ip_prefix: str  # e.g. "185.163.44." with host range below
    hosting_ip_range: tuple[int, int]
    asn_label: str
    registrar: str
    registrant_email: str
    kit_path: str
    kit_id: str
    # domains / urls / ips / senders / hashes counts (A only specified fully)
    n_domains: int
    n_urls: int
    n_ips: int
    n_senders: int
    n_hashes: int


CAMPAIGNS = [
    CampaignSpec(
        campaign_id="A",
        name="FreshCart PhishOps",  # [exact]
        theme="Clubcard/rewards credential phishing",
        ioc_count=120,
        hosting_ip_prefix="185.163.44.",
        hosting_ip_range=(10, 15),
        asn_label="AS208877 BulletHost-Demo",
        registrar="NameDodger LLC",
        registrant_email="hostmaster@freshcart-ops.example",
        kit_path="/wp-login-secure/",
        kit_id="fc-kit-v3",
        n_domains=45,
        n_urls=30,
        n_ips=25,
        n_senders=12,
        n_hashes=8,
    ),
    CampaignSpec(
        campaign_id="B",
        name="SupplierPay",
        theme="Supplier/invoice BEC vs finance",
        ioc_count=60,
        hosting_ip_prefix="45.148.121.",
        hosting_ip_range=(20, 23),
        asn_label="AS49392 FastFlux-Demo",
        registrar="QuickReg Ltd",
        registrant_email="billing-admin@supplierpay.example",
        kit_path="/portal/login",
        kit_id="sp-kit-1",
        n_domains=22,
        n_urls=18,
        n_ips=12,
        n_senders=6,
        n_hashes=2,
    ),
    CampaignSpec(
        campaign_id="C",
        name="CareerLure",
        theme="Fake recruitment vs jobseekers",
        ioc_count=45,
        hosting_ip_prefix="103.152.78.",
        hosting_ip_range=(5, 7),
        asn_label="AS135377 CloudCheap-Demo",
        registrar="DomainsRUs",
        registrant_email="hr-verify@careerlure.example",
        kit_path="/apply/verify",
        kit_id="cl-kit-2",
        n_domains=18,
        n_urls=14,
        n_ips=8,
        n_senders=4,
        n_hashes=1,
    ),
]

N_NOISE_IOCS = 200  # unrelated C2/ransomware/scanner, zero internal hits
N_DECOY_DOMAINS = 30  # benign lookalikes

# Named domains that must exist [exact] (PLAN 5.2).
HERO_DOMAIN = "tesco-clubcard-support.com"  # AP1 hero

CAMPAIGN_A_NAMED_DOMAINS = [
    "tesco-clubcard-support.com",  # the hero
    "tesco-rewards-login.com",  # AP5
    "tescobank-secure-auth.com",  # AP4
]
CAMPAIGN_B_NAMED_DOMAINS = ["tesco-supplier-billing.com"]  # AP2
CAMPAIGN_C_NAMED_DOMAINS = ["tesco-careers-verify.com"]  # counterexample

# Decoy, report-only, and vendor false-positive domains [exact].
DECOY_DOMAIN = "tesco-fans-forum.com"  # similarity ~78, confidence 20
REPORT_ONLY_DOMAIN = "tesco-parcel-tracking.net"  # AP3, in NO structured feed
VENDOR_FP_DOMAIN = "clubcard-summer-deals.com"  # legit, powers Act 4 exception
VENDOR_FP_SIBLING = "clubcard-autumn-deals.com"  # auto-close from memory

# Report-only single indicators (R14) [exact].
R14_IP = "194.5.249.211"

# ---------------------------------------------------------------------------
# Attack path specifications (PLAN 5.4) [exact]
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AttackPathSpec:
    path_id: str
    domain: str
    campaign_id: str
    feed_name: str
    feed_confidence: int
    first_seen_offset_days: float  # negative = days before REFERENCE_TS


ATTACK_PATHS = [
    AttackPathSpec("AP1", HERO_DOMAIN, "A", "RetailISAC-Demo", 90, -6),
    AttackPathSpec("AP2", "tesco-supplier-billing.com", "B", "VendorX ThreatFeed", 75, -9),
    # AP3 is report-only: no feed. first_seen supplied at extraction time.
    AttackPathSpec("AP3", REPORT_ONLY_DOMAIN, "A", "report_ai_extraction", 60, -4),
    AttackPathSpec("AP4", "tescobank-secure-auth.com", "A", "RetailISAC-Demo", 88, -1),
    AttackPathSpec("AP5", "tesco-rewards-login.com", "A", "RetailISAC-Demo", 85, -3),
]

# AP1 [exact] parameters
AP1_EMAIL_SUBJECT = "Action needed: your Clubcard points expire in 48 hours"
AP1_SENDER = "rewards@tesco-clubcard-support.com"
AP1_EMAIL_RECIPIENTS = 60
AP1_CLICKERS = 17  # distinct employees who click
AP1_CREDENTIAL_SUBMITTERS = 3  # of the 17, submit credentials
AP1_FAILED_LOGIN_MIN = 5  # 5-8 failed logins per submitter
AP1_FAILED_LOGIN_MAX = 8
AP1_FAILED_LOGIN_DELAY_MIN_MINUTES = 20  # 20-45 min after click
AP1_FAILED_LOGIN_DELAY_MAX_MINUTES = 45
AP1_PRIYA_SUCCESS_OFFSET_DAYS = -1  # T-1 22:37 RO success
AP1_PRIYA_SUCCESS_HOUR = 22
AP1_PRIYA_SUCCESS_MINUTE = 37
AP1_PRIYA_SUCCESS_COUNTRY = "RO"
AP1_PRIYA_SUCCESS_ASN = "GreyStack-Demo"

# AP2 [exact]
AP2_EMAIL_SUBJECT = "Updated bank details for PO 4471182"
AP2_SUCCESS_COUNTRY = "RO"

# AP5 [exact]
AP5_VISITS = 9  # Sophie Clarke visits across T-3..T-1

# Counterexamples [exact]
CAREERS_VERIFY_CONFIDENCE = 95  # highest confidence, 1 guest-wifi hit
CAREERS_VERIFY_DNS_HITS = 1
FANS_FORUM_SIMILARITY = 78
FANS_FORUM_CONFIDENCE = 20
FANS_FORUM_VISITS = 3

# Repeat-access flag threshold (any single user >= this many hits).
REPEAT_ACCESS_THRESHOLD = 5

# Feed overlap: fraction of cluster IOCs appearing in two feeds (PLAN 5.2).
FEED_OVERLAP_FRACTION = 0.10

# ---------------------------------------------------------------------------
# Filler pool (PLAN 5.5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FillerCategory:
    name: str
    count: int
    ground_truth_label: str
    expected_route: str


FILLER_CATEGORIES = [
    FillerCategory("commodity_phish", 50, "true_positive_low", "tier0_auto_close"),
    FillerCategory("scanner_recon", 35, "benign_noise", "prefilter_close"),
    FillerCategory("known_false_positive", 20, "benign_dup", "prefilter_close"),
    FillerCategory("ambiguous_lookalike", 15, "needs_review", "agent_queue"),
]
FILLER_POOL_SIZE = sum(c.count for c in FILLER_CATEGORIES)  # ~120

# ---------------------------------------------------------------------------
# Reports (PLAN 5.7). Sparse IDs: gaps where cut reports used to sit.
# ---------------------------------------------------------------------------
REPORT_IDS = [
    "R01", "R02", "R03", "R04", "R05",  # FreshCart (A)
    "R06", "R07",  # SupplierPay (B)
    "R09", "R10",  # CareerLure (C)
    "R14",  # feed-gap [exact]
    "R15",  # exclusive-but-quiet [exact]
    "R19", "R20",  # unrelated noise
]
N_REPORTS = len(REPORT_IDS)  # 13

# ---------------------------------------------------------------------------
# Source-name confidences for merged report IOCs (PLAN 7.3)
# ---------------------------------------------------------------------------
SOURCE_CONFIDENCE_REPORT_REGEX = 55
SOURCE_CONFIDENCE_REPORT_AI = 60


@dataclass(frozen=True)
class Config:
    seed: int = SEED
    employee_email_domain: str = EMPLOYEE_EMAIL_DOMAIN
    n_employees: int = N_EMPLOYEES
    total_structured_iocs: int = TOTAL_STRUCTURED_IOCS
    campaigns: list[CampaignSpec] = field(default_factory=lambda: list(CAMPAIGNS))
    attack_paths: list[AttackPathSpec] = field(default_factory=lambda: list(ATTACK_PATHS))
    filler_categories: list[FillerCategory] = field(
        default_factory=lambda: list(FILLER_CATEGORIES)
    )
    report_ids: list[str] = field(default_factory=lambda: list(REPORT_IDS))


CONFIG = Config()
