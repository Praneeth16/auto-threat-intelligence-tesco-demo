"""Typosquat / brand-distance features.

tldextract normalizes to the registered domain; rapidfuzz measures distance to
the protected-brand tokens. Emits brand_similarity_score (0-100) and the
nearest brand token. The similarity feature the risk score consumes and the
graph reuses (PLAN 7.4).
"""

from __future__ import annotations

import pandas as pd
import tldextract
from rapidfuzz import fuzz

from datagen import config

# Offline extractor: no live suffix-list fetch, so runs are deterministic and
# need no network.
_EXTRACT = tldextract.TLDExtract(suffix_list_urls=())

# Brand comparison vocabulary: protected registered-domain stems + tokens.
_BRAND_TERMS = [d.split(".")[0] for d in config.PROTECTED_BRAND_DOMAINS] + config.PROTECTED_BRAND_TOKENS


def registered_domain(value: str) -> str:
    """Return the registered domain (sld.suffix) for a domain or URL."""
    ext = _EXTRACT(value)
    if ext.domain and ext.suffix:
        return f"{ext.domain}.{ext.suffix}"
    return value


def _domain_stem(value: str) -> str:
    ext = _EXTRACT(value)
    return ext.domain or value


def brand_similarity(value: str) -> tuple[float, str]:
    """Return (best similarity 0-100, nearest brand term) for a domain/url.

    Brand-token coverage is the signal: phishing lookalikes embed whole brand
    tokens. A domain carrying one exact brand token scores a 75 base; each
    extra brand token adds 15 (the hero `tesco-clubcard-support` carries two,
    so it clears the >=85 threshold). Domains with no exact brand token fall
    back to a discounted fuzzy ratio, keeping genuinely unrelated domains
    (google, ransomware noise) well below the band. The single-token band sits
    ~75, matching the mid-table decoy discussion in PLAN 5.4.
    """
    stem = _domain_stem(value).lower()
    tokens = [t for t in stem.replace(".", "-").split("-") if t]

    exact = [t for t in tokens if t in _BRAND_TERMS]
    if exact:
        score = min(100.0, 75.0 + 15.0 * (len(set(exact)) - 1))
        # Nearest term is the longest exact brand token matched.
        best_term = max(set(exact), key=len)
        return score, best_term

    # No exact brand token: discounted fuzzy ratio to the nearest brand term.
    best_score = 0.0
    best_term = ""
    for term in _BRAND_TERMS:
        score = 0.6 * fuzz.ratio(stem, term)
        if score > best_score:
            best_score = score
            best_term = term
    return round(best_score, 1), best_term


def add_typosquat_features(domains: pd.DataFrame, col: str = "domain") -> pd.DataFrame:
    """Add brand_similarity_score and nearest_brand_token columns."""
    out = domains.copy()
    scores = out[col].map(brand_similarity)
    out["brand_similarity_score"] = [round(s, 1) for s, _ in scores]
    out["nearest_brand_token"] = [t for _, t in scores]
    out["registered_domain"] = out[col].map(registered_domain)
    return out
