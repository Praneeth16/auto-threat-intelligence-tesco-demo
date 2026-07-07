"""Simulator tests: Run streams the full storyline over the broker.

Verifies the in-app replay engine emits findings that climb, fires the hero
agent tool loop, queues the tier-2 action, and ticks the events/anomalies/
auto-lane counters. This is what makes Run actually stream (not the Job).
"""

from __future__ import annotations

import asyncio
import json

import pytest

from app.backend import simulator as sim_mod
from app.backend.sse import EventBroker


def _run_and_collect(total_ticks: int = 22, agent_tick: int = 18):
    """Run a shortened simulation against a fresh broker, collect events."""
    async def scenario():
        # Patch the module broker so this test is isolated.
        broker = EventBroker(buffer_size=4096)
        orig_broker = sim_mod.broker
        sim_mod.broker = broker
        orig_total, orig_agent = sim_mod.TOTAL_TICKS, sim_mod.AGENT_START_TICK
        sim_mod.TOTAL_TICKS = total_ticks
        sim_mod.AGENT_START_TICK = agent_tick
        sim = sim_mod.ReplaySimulator()

        seen: dict[str, int] = {}
        findings: dict[str, float] = {}
        agent_steps: list[str] = []

        async def collect():
            async for p in broker.subscribe():
                seen[p["event"]] = seen.get(p["event"], 0) + 1
                data = json.loads(p["data"])
                if p["event"] == "finding.updated":
                    findings[data["domain"]] = data["risk_score"]
                elif p["event"] == "agent.step":
                    agent_steps.append(data["tool"])

        task = asyncio.ensure_future(collect())
        await asyncio.sleep(0)
        await sim.start(1440)
        # Wait for the run to finish on its own: per-tick gap (~0.4s) plus the
        # agent's tool-loop sleeps, with generous headroom so nothing is cut off.
        await asyncio.sleep(0.4 * total_ticks + 12)
        await sim.stop()
        task.cancel()
        sim_mod.broker = orig_broker
        sim_mod.TOTAL_TICKS, sim_mod.AGENT_START_TICK = orig_total, orig_agent
        return seen, findings, agent_steps

    return asyncio.run(scenario())


@pytest.fixture(scope="module")
def result():
    return _run_and_collect()


def test_run_streams_all_event_types(result):
    seen, _, _ = result
    for evt in ("replay.tick", "finding.updated", "agent.started", "agent.step",
                "agent.completed", "decision.routed", "queue.updated", "metrics.updated"):
        assert seen.get(evt, 0) > 0, f"missing event: {evt}"


def test_all_five_findings_stream(result):
    _, findings, _ = result
    assert "tesco-clubcard-support.com" in findings
    assert len(findings) == 5


def test_hero_reaches_top_score(result):
    _, findings, _ = result
    assert findings["tesco-clubcard-support.com"] >= 80


def test_agent_runs_full_tool_loop(result):
    _, _, steps = result
    assert steps == sim_mod.AGENT_TOOLS


def test_inject_override_recorded():
    sim = sim_mod.ReplaySimulator()
    sim.inject("AP3")
    assert "AP3" in sim.injected
