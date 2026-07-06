# Databricks notebook source
# MAGIC %md
# MAGIC # Agent optimization: v1 vs v2 (PLAN 10.3)
# MAGIC
# MAGIC **Highest platform-API risk item in the build.** The Agent Bricks
# MAGIC evaluation-and-optimization loop is the newest capability in the plan, so
# MAGIC its invocation pattern is the least likely to be stable. Do NOT run the
# MAGIC optimizer live during the demo.
# MAGIC
# MAGIC This notebook produces the pre-baked v1-vs-v2 MLflow comparison rendered
# MAGIC in Act 4. By default it uses the ILLUSTRATIVE path: a hand-authored but
# MAGIC plausible comparison, explicitly labeled as illustrative, so the demo
# MAGIC never blocks on a brand-new API. Set RUN_LIVE_OPTIMIZER=true only if the
# MAGIC Agent Bricks optimize API has been verified working in this workspace.
# MAGIC
# MAGIC The rest of the demo does not depend on this; only Act 4's batch-
# MAGIC improvement reveal does, and that reveal has the live retrieval-learning
# MAGIC beat (Section 10.5 item 1) as its stronger, lower-risk sibling.

# COMMAND ----------

import os  # noqa: E402

import mlflow  # noqa: E402

RUN_LIVE_OPTIMIZER = os.environ.get("RUN_LIVE_OPTIMIZER", "false").lower() == "true"

# COMMAND ----------

# MAGIC %md ## Illustrative v1-vs-v2 comparison (default, demo-safe)
# MAGIC
# MAGIC Metrics move in the direction the accumulated disagreements imply: auto-
# MAGIC close precision up, escalation rate down, agent-human agreement up. These
# MAGIC are plausible and internally consistent, and are logged as an MLflow run
# MAGIC tagged illustrative so the presenter can truthfully caveat them.

# COMMAND ----------

ILLUSTRATIVE = {
    "v1": {"auto_close_precision": 0.86, "escalation_rate": 0.34, "agreement_rate": 0.81},
    "v2": {"auto_close_precision": 0.94, "escalation_rate": 0.22, "agreement_rate": 0.90},
}


def log_illustrative() -> None:
    for version, metrics in ILLUSTRATIVE.items():
        with mlflow.start_run(run_name=f"agent_{version}_illustrative"):
            mlflow.set_tag("comparison", "v1_vs_v2")
            mlflow.set_tag("status", "ILLUSTRATIVE")  # presenter must caveat
            mlflow.set_tag("agent_version", version)
            for k, v in metrics.items():
                mlflow.log_metric(k, v)
    print("logged illustrative v1-vs-v2 comparison (tagged ILLUSTRATIVE)")


# COMMAND ----------

# MAGIC %md ## Live optimizer (guarded; off by default)

# COMMAND ----------

def run_live_optimizer() -> None:
    """Invoke the Agent Bricks optimize loop against the grown eval set.

    Guarded because this API is the least stable in the plan. If it raises,
    fall back to the illustrative comparison rather than blocking the build.
    """
    try:
        # The Agent Bricks optimize invocation is workspace/version specific;
        # verify the current signature before enabling. Placeholder call site:
        from databricks.agents import optimize  # type: ignore

        result = optimize(
            agent="soc_triage_agent",
            eval_dataset="eval_dataset",
        )
        with mlflow.start_run(run_name="agent_v2_live"):
            mlflow.set_tag("comparison", "v1_vs_v2")
            mlflow.set_tag("status", "LIVE")
            for k, v in getattr(result, "metrics", {}).items():
                mlflow.log_metric(k, v)
        print("live optimizer run complete")
    except Exception as exc:
        print(f"live optimizer unavailable ({exc}); using illustrative comparison")
        log_illustrative()


# COMMAND ----------

if RUN_LIVE_OPTIMIZER:
    run_live_optimizer()
else:
    log_illustrative()
