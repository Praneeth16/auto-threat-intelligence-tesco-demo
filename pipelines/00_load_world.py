# Databricks notebook source
# MAGIC %md
# MAGIC # 00 - Load the synthetic world (instructor run-once)
# MAGIC
# MAGIC Calls the `datagen` package, writes raw feed and report files to a Unity
# MAGIC Catalog Volume, writes bronze/reference/ground-truth/reference-output
# MAGIC tables to Unity Catalog, and enables Change Data Feed on the tables that
# MAGIC Stage 3 syncs to Lakebase.
# MAGIC
# MAGIC Runs on serverless. Idempotent: re-running rebuilds the world from the
# MAGIC same seed and overwrites the tables. The reference anchor re-floors to
# MAGIC the current day so recency reads live on demo day.
# MAGIC
# MAGIC Gate after this notebook: `99_validate`.

# COMMAND ----------

# MAGIC %pip install faker tldextract rapidfuzz iocextract stix2 pymisp --quiet

# COMMAND ----------

# dbutils is only available inside the Databricks runtime.
dbutils.library.restartPython()  # noqa: F821

# COMMAND ----------

import json
import sys
from pathlib import Path

# Make the repo importable when run from a Databricks Git folder or Workspace.
_REPO = None
for _cand in (".", "..", "/Workspace/Repos"):
    if (Path(_cand) / "datagen").exists():
        _REPO = str(Path(_cand).resolve())
        break
if _REPO and _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from datagen.common import defang  # noqa: E402
from datagen.feeds import write_csv_feed, write_misp_events, write_stix_bundle  # noqa: E402
from datagen.ground_truth import build_world  # noqa: E402
from pipelines.workspace_config import (  # noqa: E402
    CATALOG,
    RAW_ROOT,
    SCHEMA,
    VOLUME,
    fq,
)

spark  # noqa: F821  (provided by the runtime)

# COMMAND ----------

# MAGIC %md ## Ensure catalog, schema, and volume exist

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.{VOLUME}")
print(f"catalog={CATALOG} schema={SCHEMA} volume={VOLUME}")
print(f"raw root: {RAW_ROOT}")

# COMMAND ----------

# MAGIC %md ## Build the world (deterministic, live day anchor)

# COMMAND ----------

world = build_world()  # no anchor -> re-floors to the current day
print("reference_ts:", world.reference_ts)
print("employees:", len(world.employees))
print("structured IOCs:", len(world.iocs))
print("bronze rows:",
      len(world.telemetry.dns), len(world.telemetry.proxy),
      len(world.telemetry.email), len(world.telemetry.auth))
print("reports:", len(world.reports))
print("filler pool:", len(world.filler_pool))

# COMMAND ----------

# MAGIC %md ## Write raw feed and report files to the Volume

# COMMAND ----------

feeds_misp = Path(RAW_ROOT) / "feeds" / "misp"
feeds_stix = Path(RAW_ROOT) / "feeds" / "stix"
feeds_csv = Path(RAW_ROOT) / "feeds" / "csv"
reports_dir = Path(RAW_ROOT) / "reports"
reports_gt_dir = reports_dir / "ground_truth"
reference_dir = Path(RAW_ROOT) / "reference"
for d in (feeds_misp, feeds_stix, feeds_csv, reports_dir, reports_gt_dir, reference_dir):
    d.mkdir(parents=True, exist_ok=True)

write_misp_events(world.iocs, feeds_misp, world.reference_ts)
write_stix_bundle(world.iocs, feeds_stix, world.reference_ts)
write_csv_feed(world.iocs, feeds_csv, world.reference_ts)

for rep in world.reports:
    ext = {"md": "md", "txt": "txt", "html": "html"}[rep.fmt]
    (reports_dir / f"{rep.report_id}.{ext}").write_text(rep.body)
    (reports_gt_dir / f"{rep.report_id}.json").write_text(json.dumps(rep.ground_truth, indent=2))

# Reference vocab files.
world.brand_assets.to_csv(reference_dir / "brand_assets.csv", index=False)
import pandas as pd  # noqa: E402
pd.DataFrame({"domain": world.benign_domains}).to_csv(
    reference_dir / "benign_top_domains.csv", index=False
)
print("raw files written under", RAW_ROOT)

# COMMAND ----------

# MAGIC %md ## Write bronze telemetry, reference, ground-truth, and bronze_reports tables

# COMMAND ----------

def write_delta(pdf, table: str, comment: str = "") -> None:
    """Write a pandas frame to a managed Delta table, overwriting."""
    sdf = spark.createDataFrame(pdf)
    (sdf.write.mode("overwrite").option("overwriteSchema", "true")
        .saveAsTable(fq(table)))
    if comment:
        spark.sql(f"COMMENT ON TABLE {fq(table)} IS '{comment}'")
    print(f"wrote {fq(table)}  rows={len(pdf)}")


# Bronze telemetry.
write_delta(world.telemetry.dns, "bronze_dns_logs", "Synthetic DNS logs")
write_delta(world.telemetry.proxy, "bronze_proxy_logs", "Synthetic proxy logs")
write_delta(world.telemetry.email, "bronze_email_events", "Synthetic email events")
write_delta(world.telemetry.auth, "bronze_auth_logs", "Synthetic auth logs")

# Bronze reports (one row per report, raw body + format for the extract stage).
reports_pdf = pd.DataFrame([
    {"report_id": r.report_id, "fmt": r.fmt, "body": r.body}
    for r in world.reports
])
write_delta(reports_pdf, "bronze_reports", "Unstructured CTI reports")

# COMMAND ----------

# Reference tables.
write_delta(world.employees, "ref_employees", "Employee directory")
write_delta(world.brand_assets, "ref_brand_assets", "Protected brand reference")
write_delta(world.ioc_enrichment, "ref_ioc_enrichment",
            "Registrar/ASN/hosting/kit enrichment for campaigns A-C")

# COMMAND ----------

# Ground-truth tables.
write_delta(world.gt_campaigns, "gt_campaigns", "Campaign ground truth")
write_delta(world.gt_attack_paths, "gt_attack_paths", "Attack-path evidence counts")
write_delta(world.gt_expected_findings, "gt_expected_findings",
            "Expected top-5 findings in rank order")
write_delta(world.gt_report_entities, "gt_report_entities", "Per-report planted entities")
write_delta(world.gt_filler_labels, "gt_filler_labels", "Filler pool labels and routes")

# COMMAND ----------

# Structured IOC universe and filler pool (used by classical + pipeline stages).
write_delta(world.iocs, "structured_iocs", "Full structured IOC universe (455)")
write_delta(world.overlap_pairs, "gt_feed_overlap", "IOCs genuinely present in two feeds")
write_delta(world.filler_pool, "filler_pool", "Labeled filler event pool")

# COMMAND ----------

# MAGIC %md ## Enable Change Data Feed on tables Stage 3 syncs to Lakebase
# MAGIC
# MAGIC Triggered/continuous synced tables require CDF on the source. The gold
# MAGIC findings table is produced by Stage 4; enabling CDF on the reference
# MAGIC tables the app also reads keeps sync options open.

# COMMAND ----------

for _t in ("ref_employees", "structured_iocs"):
    spark.sql(
        f"ALTER TABLE {fq(_t)} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)"
    )
print("CDF enabled on ref_employees, structured_iocs")

# COMMAND ----------

# MAGIC %md ## Defang self-check on rendered report bodies
# MAGIC
# MAGIC The defanged reports (R02/R04) must carry no bare hero domain. This is a
# MAGIC cheap in-notebook guard; the full assertion suite is `99_validate`.

# COMMAND ----------

from datagen import config as _cfg  # noqa: E402

for _rid in ("R02", "R04"):
    _rep = next(r for r in world.reports if r.report_id == _rid)
    assert _cfg.HERO_DOMAIN not in _rep.body, f"{_rid} leaks bare hero domain"
    assert defang(_cfg.HERO_DOMAIN) in _rep.body, f"{_rid} missing defanged hero"
print("defang self-check passed")

# COMMAND ----------

# MAGIC %md ## Done
# MAGIC
# MAGIC Next: run `99_validate` before the demo. Stage 3 creates the Lakebase
# MAGIC schema and the synced `findings` table.

# COMMAND ----------

print("00_load_world complete.")
print(f"Tables written under {CATALOG}.{SCHEMA}")
