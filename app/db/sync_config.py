"""Delta <-> Lakebase synced-table configuration (PLAN 6.2).

Direction and cadence:
- Delta gold `gold_findings` -> Lakebase `findings`, CONTINUOUS (seconds latency)
  so the Triage Board reads risk scores as they climb. Read-hot for the UI.
- App writes (`decisions`, `feedback_records`, `triage_queue` resolutions) sync
  back to Delta mirror tables for MLflow eval and Lakehouse Monitoring. That
  reverse path is Postgres-to-Delta, which Lakebase synced tables do NOT
  support (reverse ETL is Delta-to-Postgres only), so it is implemented as a
  scheduled Job that reads Postgres and appends to Delta mirrors (Stage 8),
  not as a synced table. Documented here so the direction is unambiguous.

Requires Change Data Feed on the source Delta table (set by 00_load_world for
reference tables; Stage 4 sets it on gold_findings when it creates that table).
"""

from __future__ import annotations

from pipelines.workspace_config import (
    CATALOG,
    LAKEBASE_DATABASE,
    LAKEBASE_INSTANCE,
    SCHEMA,
    fq,
)

# Source Delta table (Stage 4 gold output) -> Lakebase target.
GOLD_FINDINGS_SOURCE = fq("gold_findings")
FINDINGS_TARGET_TABLE = "findings"  # Postgres table name in Lakebase
FINDINGS_PRIMARY_KEY = ["finding_id"]

# Delta mirror tables the reverse Job (Stage 8) appends app writes into.
DELTA_MIRRORS = {
    "decisions": fq("mirror_decisions"),
    "feedback_records": fq("mirror_feedback_records"),
    "triage_resolutions": fq("mirror_triage_resolutions"),
}


def create_findings_sync() -> None:
    """Create/refresh the continuous synced table gold_findings -> findings.

    Run once by the instructor after gold_findings exists (Stage 4) and the
    Lakebase instance is up. Idempotent-ish: creating an existing synced table
    raises, so this catches that and reports.
    """
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.database import (
        NewPipelineSpec,
        SyncedDatabaseTable,
        SyncedTableSchedulingPolicy,
        SyncedTableSpec,
    )

    w = WorkspaceClient()
    # The synced table is registered as a UC object under the demo schema; its
    # Postgres projection lands in the Lakebase database.
    synced_name = f"{CATALOG}.{SCHEMA}.{FINDINGS_TARGET_TABLE}_synced"
    try:
        w.database.create_synced_database_table(
            SyncedDatabaseTable(
                name=synced_name,
                database_instance_name=LAKEBASE_INSTANCE,
                logical_database_name=LAKEBASE_DATABASE,
                spec=SyncedTableSpec(
                    source_table_full_name=GOLD_FINDINGS_SOURCE,
                    primary_key_columns=FINDINGS_PRIMARY_KEY,
                    scheduling_policy=SyncedTableSchedulingPolicy.CONTINUOUS,
                    new_pipeline_spec=NewPipelineSpec(
                        storage_catalog=CATALOG,
                        storage_schema=SCHEMA,
                    ),
                ),
            )
        )
        print(f"created synced table {synced_name} (CONTINUOUS)")
    except Exception as exc:  # already exists or transient; report, do not crash
        print(f"synced table create returned: {exc}")


def sync_status() -> None:
    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient()
    synced_name = f"{CATALOG}.{SCHEMA}.{FINDINGS_TARGET_TABLE}_synced"
    st = w.database.get_synced_database_table(name=synced_name)
    print("state:", st.data_synchronization_status.detailed_state)
    print("message:", st.data_synchronization_status.message)


if __name__ == "__main__":
    create_findings_sync()
