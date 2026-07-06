"""Data access for the backend, over Lakebase.

A thin repository around the Lakebase pool so routes stay DB-agnostic and the
contract tests can substitute an in-memory fake. The real implementation issues
the same SQL the app runs in-workspace.
"""

from __future__ import annotations

from typing import Protocol


class Repository(Protocol):
    def list_findings(self) -> list[dict]: ...
    def list_queue(self, status: str | None = None) -> list[dict]: ...
    def get_queue_item(self, queue_id: int) -> dict | None: ...
    def resolve_queue_item(self, queue_id: int, status: str, identity: str) -> dict: ...
    def write_feedback(self, decision_id, source, verdict, reason_code, notes) -> dict: ...
    def get_replay_state(self) -> dict: ...
    def set_replay_state(self, **fields) -> dict: ...
    def rollback_decision(self, decision_id: int) -> dict: ...
    def metrics(self) -> dict: ...


class LakebaseRepository:
    """Repository backed by a Lakebase psycopg pool."""

    def __init__(self, pool):
        self.pool = pool

    def _rows(self, sql, params=None) -> list[dict]:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(sql, params or ())
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]

    def _exec(self, sql, params=None) -> None:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(sql, params or ())
            conn.commit()

    def list_findings(self) -> list[dict]:
        return self._rows("SELECT * FROM findings ORDER BY risk_score DESC")

    def list_queue(self, status=None) -> list[dict]:
        if status:
            return self._rows("SELECT * FROM triage_queue WHERE status = %s "
                              "ORDER BY created_at DESC", (status,))
        return self._rows("SELECT * FROM triage_queue ORDER BY created_at DESC")

    def get_queue_item(self, queue_id):
        rows = self._rows("SELECT * FROM triage_queue WHERE queue_id = %s", (queue_id,))
        return rows[0] if rows else None

    def resolve_queue_item(self, queue_id, status, identity):
        self._exec(
            "UPDATE triage_queue SET status = %s, resolved_at = now(), "
            "resolver_identity = %s WHERE queue_id = %s",
            (status, identity, queue_id),
        )
        return self.get_queue_item(queue_id)

    def write_feedback(self, decision_id, source, verdict, reason_code, notes):
        rows = self._rows(
            "INSERT INTO feedback_records (decision_id, source, verdict, "
            "reason_code, notes) VALUES (%s, %s, %s, %s, %s) RETURNING *",
            (decision_id, source, verdict, reason_code, notes),
        )
        with self.pool.connection() as conn:
            conn.commit()
        return rows[0] if rows else {}

    def get_replay_state(self):
        rows = self._rows("SELECT * FROM replay_state WHERE id = 1")
        return rows[0] if rows else {}

    def set_replay_state(self, **fields):
        sets = ", ".join(f"{k} = %s" for k in fields)
        self._exec(f"UPDATE replay_state SET {sets}, updated_at = now() WHERE id = 1",
                   tuple(fields.values()))
        return self.get_replay_state()

    def rollback_decision(self, decision_id):
        self._exec("UPDATE decisions SET executed = false WHERE decision_id = %s "
                   "AND reversible = true", (decision_id,))
        rows = self._rows("SELECT * FROM decisions WHERE decision_id = %s", (decision_id,))
        return rows[0] if rows else {}

    def metrics(self):
        q = self._rows(
            "SELECT status, count(*) c FROM triage_queue GROUP BY status"
        )
        by_status = {r["status"]: r["c"] for r in q}
        return {
            "auto_resolved": by_status.get("auto_executed", 0),
            "auto_executed": by_status.get("auto_executed", 0),
            "queued": by_status.get("pending_review", 0),
        }
