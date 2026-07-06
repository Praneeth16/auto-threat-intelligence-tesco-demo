"""Campaign infrastructure and IOC generation.

Produces the structured IOC universe: 455 indicators across three campaigns
(A/B/C), 200 noise indicators, and 30 benign decoys. Named domains exist
verbatim; the rest are generated with token pools, connectors, TLDs, and a few
homoglyph/typo variants so the brand-similarity threshold has texture.

Also produces ref_ioc_enrichment (registrar/ASN/hosting/kit), populated for the
three campaigns and null for noise and decoys.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from datagen import config
from datagen.common import rng

# Token pools for programmatic lookalike generation.
_BRAND_TOKENS = ["tesco", "clubcard", "tescobank"]
_CONNECTORS = ["-", ""]
_SUFFIX_TOKENS = [
    "support", "login", "secure", "auth", "verify", "rewards", "account",
    "billing", "portal", "update", "signin", "points", "care", "help",
    "offers", "deals", "service", "member",
]
_TLDS = [".com", ".net", ".info", ".co", ".online", ".xyz", ".site"]

# Homoglyph / typo transforms applied to a base string for edit-distance texture.
_TYPO_MAP = {"o": "0", "l": "1", "e": "3", "i": "1", "s": "5"}


@dataclass
class Ioc:
    indicator_value: str
    indicator_type: str  # domain | url | ip | email | hash
    campaign_id: str  # A/B/C, N (noise), X (decoy)
    hosting_ip: str | None = None
    asn_label: str | None = None
    registrar: str | None = None
    registrant_email: str | None = None
    kit_id: str | None = None


def _typo_variant(base: str, r) -> str:
    """Return a homoglyph/typo variant of a base domain label."""
    chars = list(base)
    swaps = [i for i, c in enumerate(chars) if c in _TYPO_MAP]
    if swaps:
        i = r.choice(swaps)
        chars[i] = _TYPO_MAP[chars[i]]
    return "".join(chars)


def _gen_lookalike(r, used: set[str]) -> str:
    """Generate one unique lookalike domain from the token pools."""
    for _ in range(200):
        brand = r.choice(_BRAND_TOKENS)
        conn = r.choice(_CONNECTORS)
        suffix = r.choice(_SUFFIX_TOKENS)
        label = f"{brand}{conn}{suffix}" if conn else f"{brand}{suffix}"
        # ~25% get a homoglyph/typo twist for edit-distance variety.
        if r.random() < 0.25:
            label = _typo_variant(label, r)
        # Occasionally chain a second suffix for length variety.
        if r.random() < 0.2:
            label = f"{label}{r.choice(_CONNECTORS)}{r.choice(_SUFFIX_TOKENS)}"
        domain = f"{label}{r.choice(_TLDS)}"
        if domain not in used:
            used.add(domain)
            return domain
    raise RuntimeError("lookalike generator exhausted; widen token pools")


def _campaign_hosting_ips(spec: config.CampaignSpec) -> list[str]:
    lo, hi = spec.hosting_ip_range
    return [f"{spec.hosting_ip_prefix}{h}" for h in range(lo, hi + 1)]


def _named_domains_for(campaign_id: str) -> list[str]:
    return {
        "A": config.CAMPAIGN_A_NAMED_DOMAINS,
        "B": config.CAMPAIGN_B_NAMED_DOMAINS,
        "C": config.CAMPAIGN_C_NAMED_DOMAINS,
    }[campaign_id]


def _build_campaign_iocs(spec: config.CampaignSpec, r, used: set[str]) -> list[Ioc]:
    """Build the IOC set for one campaign, seeding named domains first."""
    iocs: list[Ioc] = []
    hosting_ips = _campaign_hosting_ips(spec)

    def add_domain(domain: str) -> None:
        used.add(domain)
        iocs.append(
            Ioc(
                indicator_value=domain,
                indicator_type="domain",
                campaign_id=spec.campaign_id,
                hosting_ip=r.choice(hosting_ips),
                asn_label=spec.asn_label,
                registrar=spec.registrar,
                registrant_email=spec.registrant_email,
                kit_id=spec.kit_id,
            )
        )

    # Named domains first (verbatim, must exist).
    named = _named_domains_for(spec.campaign_id)
    for d in named:
        add_domain(d)
    # Fill remaining domains programmatically.
    while sum(1 for i in iocs if i.indicator_type == "domain") < spec.n_domains:
        add_domain(_gen_lookalike(r, used))

    campaign_domains = [i.indicator_value for i in iocs if i.indicator_type == "domain"]

    # URLs: kit path appended to a campaign domain. Guarantee uniqueness with
    # a page counter so repeated domain picks do not collide.
    path = spec.kit_path.rstrip("/")
    url_seen: set[str] = set()
    while sum(1 for i in iocs if i.indicator_type == "url") < spec.n_urls:
        d = r.choice(campaign_domains)
        page = 1
        url = f"https://{d}{path}/index.php"
        while url in url_seen:
            page += 1
            url = f"https://{d}{path}/index{page}.php"
        url_seen.add(url)
        iocs.append(
            Ioc(
                indicator_value=url,
                indicator_type="url",
                campaign_id=spec.campaign_id,
                hosting_ip=r.choice(hosting_ips),
                asn_label=spec.asn_label,
                registrar=spec.registrar,
                registrant_email=spec.registrant_email,
                kit_id=spec.kit_id,
            )
        )

    # IPs: the hosting block plus a few adjacent.
    ip_pool = list(hosting_ips)
    base_last = spec.hosting_ip_range[1]
    extra = 1
    while len(ip_pool) < spec.n_ips:
        ip_pool.append(f"{spec.hosting_ip_prefix}{base_last + extra}")
        extra += 1
    for ip in ip_pool[: spec.n_ips]:
        iocs.append(
            Ioc(
                indicator_value=ip,
                indicator_type="ip",
                campaign_id=spec.campaign_id,
                hosting_ip=ip,
                asn_label=spec.asn_label,
                registrar=spec.registrar,
                registrant_email=spec.registrant_email,
                kit_id=spec.kit_id,
            )
        )

    # Sender emails: on campaign domains.
    sender_locals = ["rewards", "no-reply", "billing", "hr-verify", "alerts", "support"]
    for i in range(spec.n_senders):
        local = sender_locals[i % len(sender_locals)]
        d = r.choice(campaign_domains)
        iocs.append(
            Ioc(
                indicator_value=f"{local}@{d}",
                indicator_type="email",
                campaign_id=spec.campaign_id,
                asn_label=spec.asn_label,
                registrar=spec.registrar,
                registrant_email=spec.registrant_email,
                kit_id=spec.kit_id,
            )
        )

    # Hashes: kit payload fingerprints (deterministic hex).
    for i in range(spec.n_hashes):
        h = f"{(r.getrandbits(256)):064x}"
        iocs.append(
            Ioc(
                indicator_value=h,
                indicator_type="hash",
                campaign_id=spec.campaign_id,
                asn_label=spec.asn_label,
                registrar=spec.registrar,
                registrant_email=spec.registrant_email,
                kit_id=spec.kit_id,
            )
        )

    return iocs


def _build_noise_iocs(r, used: set[str]) -> list[Ioc]:
    """200 unrelated indicators with zero internal exposure. No enrichment."""
    iocs: list[Ioc] = []
    noise_words = ["c2node", "ransomgate", "botpanel", "scanhub", "payload",
                   "exfil", "beacon", "dropzone", "cryptovault", "stealer"]
    n = config.N_NOISE_IOCS
    # Mix of domains, ips, hashes.
    for _ in range(n):
        kind = r.choices(["domain", "ip", "hash"], weights=[5, 3, 2])[0]
        if kind == "domain":
            for _ in range(200):
                w = r.choice(noise_words)
                val = f"{w}{r.randint(1, 9999)}{r.choice(_TLDS)}"
                if val not in used:
                    used.add(val)
                    break
            iocs.append(Ioc(val, "domain", "N"))
        elif kind == "ip":
            val = ".".join(str(r.randint(1, 254)) for _ in range(4))
            iocs.append(Ioc(val, "ip", "N"))
        else:
            iocs.append(Ioc(f"{r.getrandbits(256):064x}", "hash", "N"))
    return iocs


def _build_decoy_iocs(r, used: set[str]) -> list[Ioc]:
    """30 benign lookalikes on shared consumer hosting. No enrichment."""
    iocs: list[Ioc] = []
    # The named decoy [exact] appears first.
    for d in [config.DECOY_DOMAIN]:
        used.add(d)
        iocs.append(Ioc(d, "domain", "X"))
    while len(iocs) < config.N_DECOY_DOMAINS:
        d = _gen_lookalike(r, used)
        iocs.append(Ioc(d, "domain", "X"))
    return iocs


@dataclass
class CampaignUniverse:
    iocs: pd.DataFrame  # all structured IOCs
    enrichment: pd.DataFrame  # ref_ioc_enrichment (A-C only)


def build_campaign_universe() -> CampaignUniverse:
    """Build the full structured IOC universe (455) plus enrichment table."""
    r = rng("campaigns")
    used: set[str] = set()
    all_iocs: list[Ioc] = []

    for spec in config.CAMPAIGNS:
        all_iocs.extend(_build_campaign_iocs(spec, r, used))
    all_iocs.extend(_build_noise_iocs(r, used))
    all_iocs.extend(_build_decoy_iocs(r, used))

    iocs_df = pd.DataFrame([i.__dict__ for i in all_iocs])

    # Enrichment table: rows for campaign IOCs that carry infra attributes.
    enriched = iocs_df[iocs_df["campaign_id"].isin(["A", "B", "C"])].copy()
    enrichment_df = enriched[
        ["indicator_value", "hosting_ip", "asn_label", "registrar",
         "registrant_email", "kit_id"]
    ].reset_index(drop=True)

    return CampaignUniverse(iocs=iocs_df, enrichment=enrichment_df)
