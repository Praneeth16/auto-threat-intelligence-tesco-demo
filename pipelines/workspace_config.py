"""Workspace targets for the Tesco SOC demo on the lakebase-praneeth workspace.

Every pipeline, notebook, and app reads these so the catalog/schema/volume and
Lakebase instance are named in exactly one place. Overridable by environment
variables so the same code runs against a different workspace without edits.
"""

from __future__ import annotations

import os

# Unity Catalog target (managed catalog on fe-vm-lakebase-praneeth).
CATALOG = os.environ.get("SOC_CATALOG", "serverless_lakebase_praneeth_catalog")
SCHEMA = os.environ.get("SOC_SCHEMA", "tesco_soc_demo")

# UC Volume for raw feed/report files.
VOLUME = os.environ.get("SOC_VOLUME", "soc_shared")
VOLUME_ROOT = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}"
RAW_ROOT = f"{VOLUME_ROOT}/raw"

# Lakebase Autoscaling instance that backs the operational state (Stage 3).
# Reused across sessions; created once by the instructor if absent.
LAKEBASE_INSTANCE = os.environ.get("SOC_LAKEBASE_INSTANCE", "tesco-soc-lakebase")

# Lakebase (Postgres) database + schema the app reads/writes.
LAKEBASE_DATABASE = os.environ.get("SOC_LAKEBASE_DATABASE", "databricks_postgres")
LAKEBASE_SCHEMA = os.environ.get("SOC_LAKEBASE_SCHEMA", "public")

# FMAPI serving endpoint for enrichment (Stage 4), called explicitly (not
# ai_query). Default is a fast instruct model that returns chat content cleanly;
# the demo can flip it live to a stronger model to show the cost/quality
# tradeoff through AI Gateway. (gemini-3-5-flash returns empty content over the
# chat API and the newest reasoning models reject the temperature param, so an
# instruct model is the reliable default.)
LLM_ENDPOINT = os.environ.get("SOC_LLM_ENDPOINT", "databricks-meta-llama-3-3-70b-instruct")


def fq(table: str) -> str:
    """Fully qualify a Unity Catalog table name under the demo catalog/schema."""
    return f"{CATALOG}.{SCHEMA}.{table}"
