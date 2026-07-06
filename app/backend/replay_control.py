"""Replay driver control (PLAN 9.2).

Triggers the replay Job and mirrors its control state into Lakebase replay_state
so the Director Console and SSE ticks stay in sync. Job triggering uses the SDK
in-workspace; locally it just updates state so the UI and contract tests work.
"""

from __future__ import annotations

import os


def _job_id() -> str | None:
    return os.environ.get("SOC_REPLAY_JOB_ID")


def trigger_replay_job(command: str, **params) -> str | None:
    """Trigger the replay Job with parameters; return the run id, or None if no
    job is configured (local/test)."""
    job_id = _job_id()
    if not job_id:
        return None
    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient()
    run = w.jobs.run_now(
        job_id=int(job_id),
        job_parameters={"command": command, **{k: str(v) for k, v in params.items()}},
    )
    return str(run.run_id)


def start(repo, scenario: str, speed: float) -> dict:
    trigger_replay_job("start", scenario=scenario, speed=speed)
    return repo.set_replay_state(running=True, speed=speed)


def pause(repo) -> dict:
    trigger_replay_job("pause")
    return repo.set_replay_state(running=False)


def inject(repo, path_id: str) -> dict:
    trigger_replay_job("inject", path_id=path_id)
    state = repo.get_replay_state()
    injected = list(state.get("injected_paths") or [])
    if path_id not in injected:
        injected.append(path_id)
    return repo.set_replay_state(injected_paths=injected)


def seek(repo, to_ts: str) -> dict:
    trigger_replay_job("seek", to_ts=to_ts)
    return repo.set_replay_state(sim_clock=to_ts)
