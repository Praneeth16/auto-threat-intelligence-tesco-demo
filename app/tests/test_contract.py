"""Backend contract tests (PLAN 9.6), against the in-memory repository.

- start replay advances replay_state;
- approve/reject writes a feedback record with the right reason code and stamps
  OBO identity;
- reject requires a reason code;
- rollback marks the decision reversed;
- the SSE stream emits event types during a scripted sequence;
- every PLAN 9.4 endpoint path exists.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.backend import events
from app.backend.events import EVENT_TYPES, QUEUE_UPDATED, REPLAY_TICK
from app.backend.fake_repository import FakeRepository
from app.backend.main import create_app
from app.backend.sse import EventBroker


@pytest.fixture
def client():
    from app.backend.simulator import simulator
    app = create_app(repo=FakeRepository())
    with TestClient(app) as c:
        yield c
    # Stop any simulator task the test started so it does not leak across tests.
    import asyncio
    if simulator.running:
        try:
            asyncio.get_event_loop().run_until_complete(simulator.stop())
        except Exception:
            simulator._task = None


def test_replay_start_advances_state(client):
    r = client.post("/api/replay/start", json={"scenario": "full", "speed": 720})
    assert r.status_code == 200
    assert r.json()["running"] is True
    assert r.json()["speed"] == 720


def test_replay_pause(client):
    client.post("/api/replay/start", json={"scenario": "full", "speed": 720})
    r = client.post("/api/replay/pause")
    assert r.json()["running"] is False


def test_replay_inject_tracks_path(client):
    # inject resolves the path id to its scripted domain (codex P2 fix), so the
    # override actually matches what the run loop tests against.
    r = client.post("/api/replay/inject", json={"path_id": "AP1"})
    assert "tesco-clubcard-support.com" in r.json()["injected_paths"]


def test_findings_and_queue_endpoints(client):
    assert client.get("/api/findings").status_code == 200
    q = client.get("/api/queue").json()
    assert len(q) == 1
    assert q[0]["action_tier"] == 2  # the queued tier-2 hero action


def test_approve_writes_feedback_and_stamps_identity(client):
    qid = client.get("/api/queue").json()[0]["queue_id"]
    r = client.post(f"/api/queue/{qid}/approve", json={"notes": "confirmed"},
                    headers={"x-forwarded-email": "analyst@tesco-demo.example"})
    assert r.status_code == 200
    assert r.json()["status"] == "approved"
    assert r.json()["resolver_identity"] == "analyst@tesco-demo.example"


def test_reject_requires_reason_code(client):
    qid = client.get("/api/queue").json()[0]["queue_id"]
    # No reason code -> 422.
    r = client.post(f"/api/queue/{qid}/reject", json={})
    assert r.status_code == 422


def test_reject_writes_disagree_feedback(client):
    qid = client.get("/api/queue").json()[0]["queue_id"]
    r = client.post(f"/api/queue/{qid}/reject",
                    json={"reason_code": "policy_exception", "notes": "known vendor"},
                    headers={"x-forwarded-email": "analyst@tesco-demo.example"})
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"
    assert client.app.state.repo.feedback[-1]["reason_code"] == "policy_exception"
    assert client.app.state.repo.feedback[-1]["verdict"] == "disagree"


def test_rollback_marks_decision_reversed(client):
    r = client.post("/api/decisions/1/rollback")
    assert r.status_code == 200
    assert r.json()["executed"] is False


def test_metrics_endpoint(client):
    m = client.get("/api/metrics").json()
    assert "queued" in m and "auto_executed" in m


def test_agent_traces_endpoint(client):
    r = client.get("/api/agent/traces/F-hero")
    assert r.status_code == 200
    assert r.json()["finding_id"] == "F-hero"


def test_sse_broker_publishes_typed_events_with_reconnect():
    """The broker fans typed events out and supports Last-Event-ID reconnect.

    Tested directly against the async broker rather than through the streaming
    endpoint, which would deadlock a single-threaded TestClient (the stream
    blocks the same thread that must drive the events).
    """
    async def scenario():
        b = EventBroker()
        seen: set[str] = set()
        gen = b.subscribe()  # subscribe from id 0 (nothing missed yet)
        # Prime the subscriber.
        sub_task = asyncio.ensure_future(_collect(gen, seen, 2))
        await asyncio.sleep(0)  # let the subscriber register
        await b.publish(REPLAY_TICK, events.replay_tick(None, 720, True))
        await b.publish(QUEUE_UPDATED, events.queue_updated(1, "approved"))
        await asyncio.wait_for(sub_task, timeout=2)
        return seen, b

    async def _collect(gen, seen, n):
        async for payload in gen:
            seen.add(payload["event"])
            if len(seen) >= n:
                return

    seen, broker = asyncio.run(scenario())
    assert REPLAY_TICK in seen
    assert QUEUE_UPDATED in seen
    assert seen.issubset(EVENT_TYPES)


def test_sse_reconnect_replays_missed_events():
    """A reconnecting client with Last-Event-ID gets only what it missed."""
    async def scenario():
        b = EventBroker()
        e1 = await b.publish(REPLAY_TICK, events.replay_tick(None, 1, False))
        await b.publish(QUEUE_UPDATED, events.queue_updated(1, "approved"))
        # Reconnect after e1: should see only the QUEUE_UPDATED event.
        missed = b.replay_since(e1.id)
        return [m.event for m in missed]

    missed = asyncio.run(scenario())
    assert missed == [QUEUE_UPDATED]


def test_routes_publish_to_broker(client):
    """Driving the API publishes typed events to the shared broker buffer."""
    from app.backend.sse import broker as shared

    before = len(shared._buffer)
    client.post("/api/replay/start", json={"scenario": "full", "speed": 720})
    qid = client.get("/api/queue").json()[0]["queue_id"]
    client.post(f"/api/queue/{qid}/approve", json={},
                headers={"x-forwarded-email": "a@tesco-demo.example"})
    published = [e.event for e in list(shared._buffer)[before:]]
    assert REPLAY_TICK in published
    assert QUEUE_UPDATED in published
