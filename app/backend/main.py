"""FastAPI backend for the SOC console (PLAN 9.2-9.4).

Serves the built React bundle and the API. Authenticates as the App service
principal for system actions; captures OBO user identity on approve/reject and
stamps resolver_identity. Talks to Lakebase for hot reads/writes, triggers the
replay Job and agent invocations, and multiplexes typed events over one SSE
stream.

The repository is injected (app.state.repo) so contract tests substitute an
in-memory fake; in-workspace it is a LakebaseRepository over the OAuth pool.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.backend import events, replay_control
from app.backend.auth import resolver_identity
from app.backend.simulator import simulator
from app.backend.sse import broker


# ---- request models --------------------------------------------------------
class ReplayStart(BaseModel):
    scenario: str = "full"
    speed: float = 720.0


class ReplayInject(BaseModel):
    path_id: str


class ReplaySeek(BaseModel):
    to_ts: str


class Resolution(BaseModel):
    reason_code: str | None = None
    notes: str | None = None


def _default_repo():
    """Build a repository: Lakebase in-workspace, in-memory fake otherwise."""
    if os.environ.get("PGHOST"):
        from app.backend.repository import LakebaseRepository
        from app.db.connection import make_pool

        return LakebaseRepository(make_pool(min_size=1, max_size=4))
    from app.backend.fake_repository import FakeRepository

    return FakeRepository()


def create_app(repo=None) -> FastAPI:
    app = FastAPI(title="Tesco SOC console")
    app.state.repo = repo or _default_repo()

    # ---- replay control ----------------------------------------------------
    @app.post("/api/replay/start")
    async def replay_start(body: ReplayStart):
        # Drive the in-app simulator so Run actually streams the storyline over
        # SSE. Also mirror control state to Lakebase for the record.
        replay_control.start(app.state.repo, body.scenario, body.speed)
        await simulator.start(body.speed)
        return {"running": True, "speed": body.speed}

    @app.post("/api/replay/inject")
    async def replay_inject(body: ReplayInject):
        # Director override: pull a path to the front. If the stream is not
        # running, start it first (start resets state) THEN mark the override,
        # so the injected path is honored on the next tick.
        if not simulator.running:
            await simulator.start(720.0)
        simulator.inject(body.path_id)
        return {"injected_paths": sorted(simulator.injected), "running": simulator.running}

    @app.post("/api/replay/pause")
    async def replay_pause():
        await simulator.stop()
        replay_control.pause(app.state.repo)
        return {"running": False}

    @app.post("/api/replay/seek")
    async def replay_seek(body: ReplaySeek):
        return replay_control.seek(app.state.repo, body.to_ts)

    @app.post("/api/replay/jump")
    async def replay_jump():
        # Director beat control: fast-forward the running simulator to the
        # decision point (hero peaks, agent fires). Mirrors sim_clock for the
        # record, then drives the actual in-app stream.
        replay_control.seek(app.state.repo, "T-1")
        await simulator.jump_to_decision()
        return {"running": simulator.running, "jumped_to": "decision"}

    # ---- findings / queue --------------------------------------------------
    @app.get("/api/findings")
    async def get_findings():
        return app.state.repo.list_findings()

    @app.get("/api/queue")
    async def get_queue():
        return app.state.repo.list_queue()

    @app.get("/api/queue/{queue_id}")
    async def get_queue_item(queue_id: int):
        item = app.state.repo.get_queue_item(queue_id)
        if not item:
            return JSONResponse({"detail": "not found"}, status_code=404)
        return item

    @app.post("/api/queue/{queue_id}/approve")
    async def approve(queue_id: int, body: Resolution, request: Request):
        identity = resolver_identity(request)
        item = app.state.repo.resolve_queue_item(queue_id, "approved", identity)
        if not item:
            return JSONResponse({"detail": "not found"}, status_code=404)
        # Approval records an agreeing feedback record.
        app.state.repo.write_feedback(
            decision_id=1, source="human", verdict="agree",
            reason_code=body.reason_code, notes=body.notes,
        )
        await broker.publish(events.QUEUE_UPDATED, events.queue_updated(queue_id, "approved"))
        return item

    @app.post("/api/queue/{queue_id}/reject")
    async def reject(queue_id: int, body: Resolution, request: Request):
        if not body.reason_code:
            return JSONResponse({"detail": "reason_code required"}, status_code=422)
        identity = resolver_identity(request)
        item = app.state.repo.resolve_queue_item(queue_id, "rejected", identity)
        if not item:
            return JSONResponse({"detail": "not found"}, status_code=404)
        app.state.repo.write_feedback(
            decision_id=1, source="human", verdict="disagree",
            reason_code=body.reason_code, notes=body.notes,
        )
        await broker.publish(events.QUEUE_UPDATED, events.queue_updated(queue_id, "rejected"))
        return item

    @app.post("/api/decisions/{decision_id}/rollback")
    async def rollback(decision_id: int):
        return app.state.repo.rollback_decision(decision_id)

    @app.get("/api/metrics")
    async def metrics():
        return app.state.repo.metrics()

    @app.get("/api/agent/traces/{finding_id}")
    async def traces(finding_id: str):
        # The full MLflow trace is fetched by finding; stubbed shape here.
        return {"finding_id": finding_id, "steps": []}

    # ---- SSE stream --------------------------------------------------------
    @app.get("/api/stream")
    async def stream(request: Request):
        last = request.headers.get("last-event-id")
        last_id = int(last) if last and last.isdigit() else None

        async def gen():
            async for payload in broker.subscribe(last_event_id=last_id):
                if await request.is_disconnected():
                    break
                yield payload

        return EventSourceResponse(gen())

    # ---- static frontend (built React bundle) ------------------------------
    _dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
    if _dist.exists():
        app.mount("/", StaticFiles(directory=str(_dist), html=True), name="spa")

    return app


app = create_app()
