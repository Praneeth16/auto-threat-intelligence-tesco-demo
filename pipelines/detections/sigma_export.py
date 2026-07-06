"""Sigma export (PLAN 11.1).

Generates two Sigma rules from a finding as Python dicts: (a) a proxy rule where
the URI contains the FreshCart kit path /wp-login-secure/; (b) a DNS rule where
the query is in the top-N campaign domains. Serializes to YAML, validates via
pySigma SigmaCollection, converts to SPL via the Splunk backend, and records the
rule in the detections table. Only a passing backtest proposes a rule.

Detections-as-code: the workflow a security-engineering room recognizes.
"""

from __future__ import annotations

import uuid

import yaml

from datagen import config

# Deterministic namespace for rule uuid5 (content-addressed, reproducible).
_RULE_NAMESPACE = uuid.UUID("7c2e9a10-1f3b-5d4e-8a6c-0d2f5e3a9c4b")


def _rule_id(content: str) -> str:
    return str(uuid.uuid5(_RULE_NAMESPACE, content))


def proxy_kit_path_rule(kit_path: str = "/wp-login-secure/") -> dict:
    """Proxy rule: URI contains the FreshCart kit path."""
    return {
        "title": "FreshCart phishing kit path in proxy URI",
        "id": _rule_id(f"proxy::{kit_path}"),
        "status": "experimental",
        "description": "Detects requests to the FreshCart credential-harvest kit path.",
        "logsource": {"category": "proxy"},
        "detection": {
            "selection": {"c-uri|contains": kit_path},
            "condition": "selection",
        },
        "tags": ["attack.credential_access", "attack.t1566.002"],
        "falsepositives": ["Legitimate paths that coincidentally match the string"],
        "level": "high",
    }


def dns_campaign_domains_rule(domains: list[str]) -> dict:
    """DNS rule: query in the top-N campaign domains."""
    return {
        "title": "FreshCart campaign domain DNS query",
        "id": _rule_id("dns::" + ",".join(sorted(domains))),
        "status": "experimental",
        "description": "Detects DNS resolution of known FreshCart campaign domains.",
        "logsource": {"category": "dns"},
        "detection": {
            "selection": {"query": sorted(domains)},
            "condition": "selection",
        },
        "tags": ["attack.command_and_control", "attack.t1566.002"],
        "falsepositives": ["Sinkholed or taken-down domains still queried by stale clients"],
        "level": "high",
    }


def to_yaml(rule: dict) -> str:
    return yaml.safe_dump(rule, sort_keys=False)


def validate_sigma(rule_yaml: str) -> bool:
    """Validate a rule through pySigma SigmaCollection. Raises on malformed."""
    from sigma.collection import SigmaCollection

    SigmaCollection.from_yaml(rule_yaml)  # raises SigmaError if invalid
    return True


def to_splunk(rule_yaml: str) -> str:
    """Convert a validated Sigma rule to a Splunk SPL query."""
    from sigma.backends.splunk import SplunkBackend
    from sigma.collection import SigmaCollection

    collection = SigmaCollection.from_yaml(rule_yaml)
    return SplunkBackend().convert(collection)[0]


def build_hero_rules() -> list[dict]:
    """The two rules the demo exports from the hero finding."""
    campaign_a = config.CAMPAIGN_A_NAMED_DOMAINS
    return [
        proxy_kit_path_rule(config.CAMPAIGNS[0].kit_path),
        dns_campaign_domains_rule(campaign_a),
    ]
