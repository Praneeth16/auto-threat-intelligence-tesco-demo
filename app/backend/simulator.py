"""In-app replay simulator: the engine that makes Run actually stream.

When the Director Console presses Run, this async task drives the whole
storyline over the SSE broker: telemetry ingests tick up, the five attack-path
findings appear and their risk climbs, the hero crosses threshold and the agent
fires its tool loop, the tier-2 action queues, and filler events auto-resolve
into the metrics counters. Pause cancels the task.

The storyline is a deterministic script (final scores and climb curves baked
in) so it is demo-safe and does not need to build the 60k-row world at app
runtime. The numbers match the datagen ground truth.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from app.backend import events
from app.backend.sse import broker

# The scripted spine: each finding's final score, the tick it first appears, and
# how many climb steps it takes. Ordered so the hero dominates. Scores match the
# datagen scoring output (hero 82, then the AP tail).
@dataclass
class ScriptedFinding:
    path_id: str  # AP1..AP5, the id the Director "override" buttons send
    finding_id: str
    domain: str
    final_score: float
    appear_tick: int
    climb_ticks: int
    fires_agent: bool = False
    components: dict = field(default_factory=dict)


SPINE = [
    # The hero appears first and climbs the longest, so the room watches its
    # score rise. Tail findings enter shortly after so the board fills early.
    ScriptedFinding("AP1", "F-tesco-clubcard-support.com", "tesco-clubcard-support.com",
                    82.0, 2, 16, fires_agent=True,
                    components={"brand_similarity": 90, "users": 17, "credential_entry": 1, "privileged": 1}),
    ScriptedFinding("AP4", "F-tescobank-secure-auth.com", "tescobank-secure-auth.com",
                    54.0, 4, 8, components={"brand_similarity": 75, "users": 4, "recency": 1}),
    ScriptedFinding("AP2", "F-tesco-supplier-billing.com", "tesco-supplier-billing.com",
                    46.0, 5, 8, components={"brand_similarity": 75, "users": 1, "credential_entry": 1}),
    ScriptedFinding("AP5", "F-tesco-rewards-login.com", "tesco-rewards-login.com",
                    49.0, 6, 7, components={"brand_similarity": 75, "users": 1, "repeat_access": 1}),
    ScriptedFinding("AP3", "F-tesco-parcel-tracking.net", "tesco-parcel-tracking.net",
                    48.0, 8, 6, components={"brand_similarity": 75, "users": 2, "report_only": 1}),
]

# Resolve a Director override id (AP1..AP5) to the scripted domain it fronts.
PATH_TO_DOMAIN = {f.path_id: f.domain for f in SPINE}

# The hero agent's tool loop, shown as live step markers.
AGENT_TOOLS = [
    "query_telemetry", "check_auth_anomalies", "get_user_context",
    "get_campaign_cluster", "get_report_context", "search_case_memory",
]

HERO = SPINE[0]
AGENT_START_TICK = HERO.appear_tick + HERO.climb_ticks  # agent fires once hero peaks
TOTAL_TICKS = 46  # ~30-40s of stream at the default cadence

# Filler auto-lane volume that accumulates into the metrics counters (PLAN 5.5).
FILLER_TIER0 = 50   # commodity phish, exact IOC -> auto-close
FILLER_PREFILTER = 55  # scanner + dup -> prefilter close


def _clamp(v: float) -> float:
    return max(0.0, min(100.0, v))


class ReplaySimulator:
    """Owns the single running replay task and its accumulated state."""

    def __init__(self):
        self._task: asyncio.Task | None = None
        # Serializes stop/reset/create so racing start() calls cannot leave an
        # orphan _run task publishing SSE and mutating counters.
        self._lifecycle_lock = asyncio.Lock()
        self.reset_state()

    def reset_state(self) -> None:
        self.tick = 0
        self.events_dns = 0
        self.events_proxy = 0
        self.events_email = 0
        self.events_auth = 0
        self.anomalies = 0
        self.auto_resolved = 0
        self.auto_executed = 0
        self.queued = 0
        self.tokens = 0
        self.injected: set[str] = set()
        # When set, the run loop skips its per-tick sleep until the tick counter
        # reaches this target, fast-forwarding the storyline to a beat.
        self._fast_forward_to = 0

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self, speed: float) -> None:
        # The whole cancel-old, reset, create-new sequence runs under the lock,
        # so two concurrent starts cannot both create a task; the second waits
        # for the first to finish creating, then cancels and replaces it. No
        # orphan can survive with _task pointing elsewhere.
        async with self._lifecycle_lock:
            await self._stop_locked()
            self.reset_state()
            self._task = asyncio.ensure_future(self._run(speed))

    async def stop(self) -> None:
        async with self._lifecycle_lock:
            await self._stop_locked()

    async def _stop_locked(self) -> None:
        """Cancel and await the current task. Caller must hold the lock."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
        self._task = None

    async def jump_to_decision(self, speed: float = 720.0) -> None:
        """Director beat control: fast-forward the storyline to the decision
        point where the hero peaks and the agent fires.

        If a run is active, arm the fast-forward so the loop stops sleeping and
        races to AGENT_START_TICK; if none is active, start one first. Findings
        emitted before the target still stream, so the board is never left empty.
        """
        async with self._lifecycle_lock:
            if not (self._task and not self._task.done()):
                self.reset_state()
                self._task = asyncio.ensure_future(self._run(speed))
            self._fast_forward_to = AGENT_START_TICK

    def inject(self, path_id: str) -> None:
        """Director override: pull a path to the front so it appears next tick.

        Resolves the path id (AP1..AP5) to the scripted domain the run loop
        tests against; unknown ids are stored as-is so a raw domain also works.
        """
        self.injected.add(PATH_TO_DOMAIN.get(path_id, path_id))

    async def _run(self, speed: float) -> None:
        # Cadence: faster speed -> shorter wall gap, bounded so the show lands in
        # ~30-60s regardless of the slider.
        gap = max(0.4, min(1.2, 900.0 / max(speed, 60.0)))
        agent_fired = False
        try:
            for t in range(1, TOTAL_TICKS + 1):
                self.tick = t

                # Telemetry ingest per tick (events counter climbs).
                d, p, e, a = 900, 380, 90, 140
                self.events_dns += d
                self.events_proxy += p
                self.events_email += e
                self.events_auth += a
                await broker.publish(
                    events.REPLAY_TICK,
                    events.replay_tick(f"T-{max(0, 3 - t // 15)}", speed, True, d, p, e, a),
                )

                # Findings appear and climb.
                for f in SPINE:
                    appear = 1 if f.domain in self.injected else f.appear_tick
                    if t < appear:
                        continue
                    progress = min(1.0, (t - appear + 1) / max(1, f.climb_ticks))
                    score = round(_clamp(f.final_score * progress), 1)
                    status = "queued" if (f.fires_agent and progress >= 1.0) else "triaging"
                    await broker.publish(
                        events.FINDING_UPDATED,
                        events.finding_updated(f.finding_id, f.domain, score, f.components, status),
                    )
                    if progress >= 1.0 and f is not HERO:
                        # Tail findings quietly count as anomalies once peaked.
                        pass
                self.anomalies = sum(1 for f in SPINE if t >= (1 if f.domain in self.injected else f.appear_tick))

                # Filler auto-lane accumulation, spread across the run.
                if t <= TOTAL_TICKS:
                    self.auto_resolved = min(FILLER_PREFILTER, int(FILLER_PREFILTER * t / TOTAL_TICKS))
                    self.auto_executed = min(FILLER_TIER0, int(FILLER_TIER0 * t / TOTAL_TICKS))
                    self.tokens += 1200

                # Hero agent fires once it peaks.
                if not agent_fired and t >= AGENT_START_TICK:
                    agent_fired = True
                    await self._fire_agent(gap)
                    self.queued = 1

                await self._emit_metrics()
                # While fast-forwarding to an armed beat, skip the wall gap so
                # the storyline races to the target tick; yield only.
                if t < self._fast_forward_to:
                    await asyncio.sleep(0)
                else:
                    self._fast_forward_to = 0
                    await asyncio.sleep(gap)

            # Final tick: mark running false.
            await broker.publish(events.REPLAY_TICK,
                                 events.replay_tick("T-0", speed, False, 0, 0, 0, 0))
        except asyncio.CancelledError:
            await broker.publish(events.REPLAY_TICK,
                                 events.replay_tick(f"T-{max(0, 3 - self.tick // 15)}", speed, False, 0, 0, 0, 0))
            raise

    async def _fire_agent(self, gap: float) -> None:
        run_id = "run-hero-001"
        await broker.publish(events.AGENT_STARTED,
                             events.agent_started(HERO.finding_id, run_id))
        for tool in AGENT_TOOLS:
            await broker.publish(events.AGENT_STEP, events.agent_step(run_id, tool))
            self.tokens += 800
            await asyncio.sleep(min(gap, 0.6))
        brief = ("What happened: The domain tesco-clubcard-support[.]com is part of "
                 "FreshCart PhishOps and drew internal contact. Who is affected: Priya "
                 "Nair. Evidence: 17 distinct users, 3 credential submissions. "
                 "Recommended action: password-reset (tier 2). Confidence: 90%.")
        await broker.publish(
            events.AGENT_COMPLETED,
            events.agent_completed(run_id, HERO.finding_id, brief, "password-reset", 2, 0.9, 0.95),
        )
        await broker.publish(
            events.DECISION_ROUTED,
            events.decision_routed(1, HERO.finding_id, "human_queue", 2, "password-reset"),
        )
        await broker.publish(events.QUEUE_UPDATED, events.queue_updated(1, "pending_review"))

    async def _emit_metrics(self) -> None:
        agreement = 0.9 if self.queued else None
        escalation = round(self.queued / max(1, self.anomalies), 2) if self.anomalies else None
        events_total = self.events_dns + self.events_proxy + self.events_email + self.events_auth
        await broker.publish(
            events.METRICS_UPDATED,
            events.metrics_updated(self.auto_resolved, self.auto_executed, self.queued,
                                   agreement, escalation, self.tokens,
                                   events_total=events_total, anomalies=self.anomalies),
        )


# Module-level singleton the routes drive.
simulator = ReplaySimulator()
