# Databricks notebook source
# MAGIC %md
# MAGIC # Build the versioned MLflow eval dataset (PLAN 10.3)
# MAGIC
# MAGIC Feedback records + agent traces become a versioned MLflow eval dataset
# MAGIC that grows by itself. Reads the Delta mirrors of the Lakebase feedback
# MAGIC and decision tables (synced back by the Stage 8 reverse Job), joins the
# MAGIC MLflow traces, and writes a new dataset version.

# COMMAND ----------

import mlflow  # noqa: E402
import pandas as pd  # noqa: E402

from pipelines.workspace_config import fq  # noqa: E402

spark  # noqa: F821

# COMMAND ----------

# MAGIC %md ## Read feedback + decisions from the Delta mirrors

# COMMAND ----------

def _read_or_empty(table: str, cols: list[str]) -> pd.DataFrame:
    try:
        return spark.table(fq(table)).toPandas()
    except Exception:
        return pd.DataFrame(columns=cols)


feedback = _read_or_empty("mirror_feedback_records",
                          ["feedback_id", "decision_id", "source", "verdict",
                           "reason_code", "notes", "ground_truth_label"])
decisions = _read_or_empty("mirror_decisions",
                           ["decision_id", "finding_id", "route", "action",
                            "action_tier", "confidence_composite"])

# COMMAND ----------

# MAGIC %md ## Join into eval examples and version the dataset
# MAGIC
# MAGIC Each example: the finding + the agent's recommendation + the confirmed
# MAGIC verdict + the ground-truth label. Only reason-coded, confirmed decisions
# MAGIC become eval examples (PLAN 10.1); ambiguous ones stay out.

# COMMAND ----------

examples = feedback.merge(decisions, on="decision_id", how="inner")
examples = examples[examples["reason_code"].notna()]

eval_table = fq("eval_dataset")
if len(examples):
    (spark.createDataFrame(examples).write.mode("overwrite")
        .option("overwriteSchema", "true").saveAsTable(eval_table))

# Version the dataset in MLflow so it is reproducible and grows over time.
with mlflow.start_run(run_name="eval_dataset_build"):
    mlflow.log_metric("eval_examples", len(examples))
    mlflow.log_metric("reason_coded", int(examples["reason_code"].notna().sum()) if len(examples) else 0)
    mlflow.set_tag("dataset_table", eval_table)

print(f"eval dataset built: {len(examples)} examples -> {eval_table}")
