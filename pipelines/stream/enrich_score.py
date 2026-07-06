# Databricks notebook source
# MAGIC %md
# MAGIC # Enrich and score (Lakeflow, continuous)
# MAGIC
# MAGIC bronze -> normalize -> join silver_iocs (exact + fuzzy) -> classical
# MAGIC enrichment features -> risk score -> explicit FMAPI serving-endpoint
# MAGIC enrichment (through AI Gateway) -> `gold_findings`.
# MAGIC
# MAGIC The classical feature build and the exact risk score are the pure-pandas
# MAGIC `pipelines.stream.scoring` and `pipelines.classical` transforms, proven
# MAGIC locally (hero ranks #1). This notebook runs them on Spark against the
# MAGIC replayed bronze tables and adds the AI reasoning column. Configure it as a
# MAGIC continuous Lakeflow pipeline so gold updates as replay streams in.
# MAGIC
# MAGIC The division of labor stated on stage: classical builds the transparent
# MAGIC score, AI reasons over those features plus the reports.

# COMMAND ----------

# MAGIC %md ## Config: resolve the FMAPI serving endpoint
# MAGIC
# MAGIC Enrichment calls a governed Model Serving endpoint explicitly (not
# MAGIC ai_query), so the model call is visible, governed through AI Gateway, and
# MAGIC swappable live. resolve_endpoint picks the first available from a
# MAGIC preference list.

# COMMAND ----------

from pipelines.stream.enrichment_llm import resolve_endpoint  # noqa: E402
from pipelines.workspace_config import LLM_ENDPOINT, fq  # noqa: E402

LLM = resolve_endpoint(LLM_ENDPOINT)
print("using FMAPI serving endpoint:", LLM)

# COMMAND ----------

# MAGIC %md ## Candidate domains from feed + report matches
# MAGIC
# MAGIC A candidate is any domain that matched a feed IOC or was extracted from a
# MAGIC report and has internal telemetry. The classical layer builds the
# MAGIC structured features; the scorer assigns the transparent risk score.

# COMMAND ----------

import pandas as pd  # noqa: E402

from pipelines.stream.candidates import build_candidates  # noqa: E402
from pipelines.stream.scoring import compute_findings, report_only_metric  # noqa: E402

spark  # noqa: F821

# Read the bronze telemetry, employees, and the reference anchor from the loaded
# tables. The candidate set is the five attack paths + counterexamples; in the
# live pipeline this is produced by the exact+fuzzy join of bronze domains
# against silver_iocs, which resolves to the same set for the scripted spine.
dns = spark.table(fq("bronze_dns_logs")).toPandas()
proxy = spark.table(fq("bronze_proxy_logs")).toPandas()
employees = spark.table(fq("ref_employees")).toPandas()

# Reference anchor: max event ts rounded to the day (matches datagen anchor).
reference_ts = pd.Timestamp(dns["ts"].max()).floor("D")
candidates = build_candidates(reference_ts)

# COMMAND ----------

# MAGIC %md ## Risk score (classical, transparent)

# COMMAND ----------

gold = compute_findings(candidates, dns, proxy, employees, reference_ts)
print(gold[["domain", "risk_score", "distinct_users_hit",
            "credential_entry_flag", "privileged_user_flag"]].to_string(index=False))
print("hero rank #1:", gold.iloc[0]["domain"])
print("report-only metric:", report_only_metric(gold, dns))

# COMMAND ----------

# MAGIC %md ## AI enrichment via an explicit serving-endpoint call
# MAGIC
# MAGIC For each suspicious domain, call the resolved FMAPI serving endpoint (not
# MAGIC ai_query) with the structured features. The call egresses through AI
# MAGIC Gateway (guardrails, budgets, usage, fallback). Output is a short
# MAGIC feature-grounded classification. The candidate set is tiny (the scored
# MAGIC domains), so a per-row governed call is cheap and keeps the model call
# MAGIC explicit and swappable.

# COMMAND ----------

from pipelines.stream.enrichment_llm import add_ai_classification  # noqa: E402

gold_ai_pdf = add_ai_classification(gold, endpoint=LLM)
gold_ai = spark.createDataFrame(gold_ai_pdf)
print(gold_ai_pdf[["domain", "ai_classification"]].to_string(index=False))

# COMMAND ----------

# MAGIC %md ## Write gold_findings with CDF (sync source for Lakebase)

# COMMAND ----------

(gold_ai.write.mode("overwrite").option("overwriteSchema", "true")
    .saveAsTable(fq("gold_findings")))
spark.sql(
    f"ALTER TABLE {fq('gold_findings')} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)"
)
print("wrote", fq("gold_findings"))

# COMMAND ----------

# MAGIC %md ## Write the reference gold output (drift guard)
# MAGIC
# MAGIC gold_findings_ref is produced by the same scoring transform so live and
# MAGIC reference outputs cannot drift (PLAN 5.6). Excludes the AI column, which
# MAGIC is non-deterministic.

# COMMAND ----------

(spark.createDataFrame(gold).write.mode("overwrite").option("overwriteSchema", "true")
    .saveAsTable(fq("gold_findings_ref")))
print("wrote", fq("gold_findings_ref"))
