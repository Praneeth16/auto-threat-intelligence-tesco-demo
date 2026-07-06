"""Enrichment module tests (no live endpoint; the SDK client is faked).

Proves the enrichment calls a served endpoint explicitly (not ai_query), builds
the feature line correctly, degrades gracefully on error, and retries without
temperature when a model rejects it.
"""

from __future__ import annotations

import pandas as pd

from pipelines.stream import enrichment_llm as e


class _FakeMsg:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMsg(content)


class _FakeResp:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeClient:
    """Records calls; optionally rejects temperature on the first attempt."""

    def __init__(self, reject_temperature=False, content="phishing likely"):
        self.reject_temperature = reject_temperature
        self.content = content
        self.calls = []

        class _SE:
            def __init__(inner):
                inner.parent = self

            def query(inner, **kwargs):
                self.calls.append(kwargs)
                if self.reject_temperature and "temperature" in kwargs:
                    raise RuntimeError("BAD_REQUEST: does not support the temperature")
                return _FakeResp(self.content)

        self.serving_endpoints = _SE()


def _gold_row():
    return pd.Series({
        "domain": "tesco-clubcard-support.com",
        "brand_similarity_score": 90,
        "distinct_users_hit": 17,
        "credential_entry_flag": 1,
        "privileged_user_flag": 1,
        "max_source_confidence": 90,
        "days_since_first_seen": 6.0,
    })


def test_feature_line_contains_all_features():
    line = e._feature_line(_gold_row())
    for token in ("tesco-clubcard-support.com", "brand_similarity: 90",
                  "distinct_users: 17", "credential_entry: 1", "privileged_user: 1"):
        assert token in line


def test_classify_domain_returns_content():
    client = _FakeClient(content="This is phishing.")
    out = e.classify_domain("ep", "features", client=client)
    assert out == "This is phishing."
    assert len(client.calls) == 1
    assert client.calls[0]["temperature"] == 0.0


def test_classify_domain_retries_without_temperature():
    client = _FakeClient(reject_temperature=True, content="ok")
    out = e.classify_domain("ep", "features", client=client)
    assert out == "ok"
    # First call had temperature, retry dropped it.
    assert len(client.calls) == 2
    assert "temperature" in client.calls[0]
    assert "temperature" not in client.calls[1]
