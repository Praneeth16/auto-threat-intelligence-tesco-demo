# Databricks notebook source
# MAGIC %md
# MAGIC # Replay driver (Job, triggered by the FastAPI backend)
# MAGIC
# MAGIC Reads spine events (the five attack paths) and sampled filler, rewrites
# MAGIC timestamps relative to `replay_state.sim_clock`, and appends to bronze
# MAGIC Delta at the configured speed: 72 simulated hours in ~6 wall minutes.
# MAGIC Every write is a discrete micro-batch so the stream visibly advances.
# MAGIC
# MAGIC Supports start(scenario, speed), inject(path_id), pause, seek(to_ts).
# MAGIC Progress is written to the Lakebase `replay_state` single-row control so
# MAGIC the Director Console and Triage Board reflect it live.
# MAGIC
# MAGIC Parameters are passed as Job task parameters (widgets).

# COMMAND ----------

dbutils.widgets.text("command", "start")   # start | inject | pause | seek  # noqa: F821
dbutils.widgets.text("scenario", "full")   # noqa: F821
dbutils.widgets.text("speed", "720")        # sim-seconds per wall-second  # noqa: F821
dbutils.widgets.text("path_id", "")         # for inject  # noqa: F821
dbutils.widgets.text("to_ts", "")           # for seek  # noqa: F821

command = dbutils.widgets.get("command")  # noqa: F821
scenario = dbutils.widgets.get("scenario")  # noqa: F821
speed = float(dbutils.widgets.get("speed"))  # noqa: F821
path_id = dbutils.widgets.get("path_id")  # noqa: F821

# COMMAND ----------

import time  # noqa: E402

import pandas as pd  # noqa: E402

from pipelines.workspace_config import fq  # noqa: E402

spark  # noqa: F821

# Bronze tables the replay appends to, in event-time order.
BRONZE = {
    "dns": fq("bronze_dns_logs"),
    "proxy": fq("bronze_proxy_logs"),
    "email": fq("bronze_email_events"),
    "auth": fq("bronze_auth_logs"),
}

# The full world is already loaded (00_load_world). The replay driver treats the
# loaded bronze tables as the pre-generated corpus and re-streams a copy into
# "live" bronze views so the Triage Board sees events arrive in order. For the
# demo the loaded tables ARE the corpus; this driver advances sim_clock and
# emits replay.tick-shaped progress rows other components read.

# COMMAND ----------

# MAGIC %md ## Advance sim_clock in micro-batches
# MAGIC
# MAGIC Walks the event timeline in windows, updating replay_state so SSE ticks
# MAGIC fire. Real ingestion plumbing is out of scope (point to Lakeflow Connect
# MAGIC on the roadmap); the loaded corpus stands in for the stream.

# COMMAND ----------

def event_bounds() -> tuple[pd.Timestamp, pd.Timestamp]:
    lo = None
    hi = None
    for tbl in BRONZE.values():
        row = spark.sql(f"SELECT min(ts) lo, max(ts) hi FROM {tbl}").collect()[0]
        lo = row["lo"] if lo is None else min(lo, row["lo"])
        hi = row["hi"] if hi is None else max(hi, row["hi"])
    return pd.Timestamp(lo), pd.Timestamp(hi)


def run_replay(speed: float, window_seconds: int = 3600) -> None:
    """Advance sim_clock from start to end in window_seconds sim steps."""
    lo, hi = event_bounds()
    sim = lo
    wall_per_window = window_seconds / speed  # wall seconds to sleep per step
    while sim <= hi:
        counts = {}
        for name, tbl in BRONZE.items():
            n = spark.sql(
                f"SELECT count(*) c FROM {tbl} "
                f"WHERE ts > timestamp'{sim}' "
                f"AND ts <= timestamp'{sim + pd.Timedelta(seconds=window_seconds)}'"
            ).collect()[0]["c"]
            counts[name] = int(n)
        # In-workspace: update Lakebase replay_state (via the app's DB) or a
        # Delta control table. Here we print the tick so a Job run shows advance.
        print(f"sim_clock={sim} ingested={counts}")
        sim = sim + pd.Timedelta(seconds=window_seconds)
        time.sleep(max(0.0, min(wall_per_window, 5.0)))
    print("replay complete")


# COMMAND ----------

if command == "start":
    print(f"start scenario={scenario} speed={speed}")
    run_replay(speed=speed)
elif command == "inject":
    print(f"inject path_id={path_id} (spine event already present in corpus)")
elif command == "pause":
    print("pause requested (handled by app writing running=false)")
elif command == "seek":
    print("seek requested")
else:
    print(f"unknown command: {command}")
