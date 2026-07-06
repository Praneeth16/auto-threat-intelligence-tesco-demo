"""In-memory repository for contract tests and local dev without Lakebase.

Implements the same interface as LakebaseRepository with dict-backed state, so
the backend contract tests (PLAN 9.6) run without the Apps proxy or a live DB.
Seeded with one finding and one queued tier-2 item so the approve/reject and
rollback paths are exercisable.
"""

from __future__ import annotations

import itertools


class FakeRepository:
    def __init__(self):
        self._qid = itertools.count(1)
        self._fid = itertools.count(1)
        self.findings = [{
            "finding_id": "F-tesco-clubcard-support.com",
            "domain": "tesco-clubcard-support.com",
            "risk_score": 82.37, "components": {}, "evidence": {},
            "intel_sources": ["RetailISAC-Demo"], "status": "queued",
        }]
        qid = next(self._qid)
        self.queue = [{
            "queue_id": qid, "finding_id": "F-tesco-clubcard-support.com",
            "brief": "Priya Nair credential compromise via the hero domain.",
            "recommended_action": "password-reset", "action_tier": 2,
            "agent_confidence": 0.9, "judge_groundedness": 0.95,
            "status": "pending_review", "resolved_at": None, "resolver_identity": None,
        }]
        self.decisions = [{
            "decision_id": 1, "finding_id": "F-tesco-clubcard-support.com",
            "queue_id": qid, "route": "human_queue", "action": "password-reset",
            "action_tier": 2, "executed": False, "reversible": True,
        }]
        self.feedback = []
        self.replay = {"id": 1, "sim_clock": None, "speed": 1, "running": False,
                       "injected_paths": []}

    def list_findings(self):
        return list(self.findings)

    def list_queue(self, status=None):
        if status:
            return [q for q in self.queue if q["status"] == status]
        return list(self.queue)

    def get_queue_item(self, queue_id):
        return next((q for q in self.queue if q["queue_id"] == queue_id), None)

    def resolve_queue_item(self, queue_id, status, identity):
        item = self.get_queue_item(queue_id)
        if item:
            item["status"] = status
            item["resolver_identity"] = identity
            item["resolved_at"] = "now"
        return item

    def write_feedback(self, decision_id, source, verdict, reason_code, notes):
        rec = {"feedback_id": len(self.feedback) + 1, "decision_id": decision_id,
               "source": source, "verdict": verdict, "reason_code": reason_code,
               "notes": notes}
        self.feedback.append(rec)
        return rec

    def get_replay_state(self):
        return dict(self.replay)

    def set_replay_state(self, **fields):
        self.replay.update(fields)
        return dict(self.replay)

    def rollback_decision(self, decision_id):
        d = next((x for x in self.decisions if x["decision_id"] == decision_id), None)
        if d and d["reversible"]:
            d["executed"] = False
        return d or {}

    def metrics(self):
        pending = sum(1 for q in self.queue if q["status"] == "pending_review")
        auto = sum(1 for q in self.queue if q["status"] == "auto_executed")
        return {"auto_resolved": auto, "auto_executed": auto, "queued": pending}
