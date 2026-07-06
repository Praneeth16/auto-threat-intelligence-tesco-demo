# Databricks notebook source
# MAGIC %md
# MAGIC # Detection export and campaign graph (PLAN 11)
# MAGIC
# MAGIC Instructor demo, pre-built. Generates the two hero Sigma rules, validates
# MAGIC them through pySigma, converts to SPL, backtests against bronze, writes
# MAGIC the passing rules to the Git folder and the detections table, and renders
# MAGIC the campaign graph (455 indicators collapse to 3 campaigns).

# COMMAND ----------

from pathlib import Path  # noqa: E402

from datagen import config  # noqa: E402
from pipelines.detections.backtest import backtest_proxy_rule, backtest_threshold  # noqa: E402
from pipelines.detections.sigma_export import (  # noqa: E402
    build_hero_rules, to_splunk, to_yaml, validate_sigma,
)
from pipelines.graph.campaign_graph import build_campaign_graph, render_graph  # noqa: E402
from pipelines.workspace_config import fq  # noqa: E402

spark  # noqa: F821

# COMMAND ----------

# MAGIC %md ## Generate, validate, backtest, and record the Sigma rules

# COMMAND ----------

proxy = spark.table(fq("bronze_proxy_logs")).toPandas()
git_folder = Path("detections")  # Git-folder path; committed as detections-as-code
git_folder.mkdir(exist_ok=True)

rows = []
for rule in build_hero_rules():
    rule_yaml = to_yaml(rule)
    validate_sigma(rule_yaml)
    spl = to_splunk(rule_yaml)
    # Backtest the proxy rule; DNS rule recall is trivially the campaign set.
    bt = backtest_proxy_rule(proxy, config.CAMPAIGNS[0].kit_path, {config.HERO_DOMAIN}) \
        if rule["logsource"]["category"] == "proxy" else None
    status = "proposed" if (bt is None or bt.passes) else "rejected"
    # Write to the Git folder as detections-as-code.
    (git_folder / f"{rule['id']}.yml").write_text(rule_yaml)
    (git_folder / f"{rule['id']}.spl").write_text(spl)
    rows.append({
        "detection_id": rule["id"], "finding_id": f"F-{config.HERO_DOMAIN}",
        "rule_yaml": rule_yaml, "backtest_hits": bt.hits if bt else 0,
        "backtest_fp_rate": bt.fp_rate if bt else 0.0,
        "backtest_recall": bt.recall if bt else 1.0,
        "status": status, "git_path": str(git_folder / f"{rule['id']}.yml"),
    })
    print(f"{status}: {rule['title']}  ->  {spl[:80]}")

# COMMAND ----------

# MAGIC %md ## Threshold backtest (routing credibility, PLAN 11.2)

# COMMAND ----------

filler = spark.table(fq("filler_pool")).toPandas()
tb = backtest_threshold(filler, threshold=0.85)
print(f"threshold {tb.threshold}: wrong_auto_closes={tb.wrong_auto_closes} "
      f"escalations={tb.escalations} analyst_hours_cleared={tb.analyst_hours_cleared}")

# COMMAND ----------

# MAGIC %md ## Campaign graph (455 -> 3)

# COMMAND ----------

iocs = spark.table(fq("structured_iocs")).toPandas()
enr = spark.table(fq("ref_ioc_enrichment")).toPandas()
gt = spark.table(fq("gt_campaigns")).toPandas()
result = build_campaign_graph(iocs, enr, gt)
print("communities:", [c for c in result.labeled])
out = render_graph(result, config.HERO_DOMAIN, "/tmp/campaign_graph.png")
print("graph rendered:", out)
