"""Lakebase connection helpers.

Canonical pattern from the Lakebase Autoscaling skill: a psycopg ConnectionPool
whose connection class mints a fresh OAuth database credential just-in-time, so
physical connections recycle before the ~1-hour token expiry. Used by the seed
script, the schema applier, and the FastAPI backend (Stage 6).

Auth facts:
- Mint with WorkspaceClient().postgres.generate_database_credential(endpoint=...).
- Use cred.token as the Postgres password (NOT a workspace-scoped token).
- Always connect with sslmode=require.
"""

from __future__ import annotations

import os

import psycopg
from psycopg_pool import ConnectionPool

from pipelines.workspace_config import LAKEBASE_DATABASE, LAKEBASE_INSTANCE


def _endpoint_name() -> str:
    return os.environ.get("SOC_LAKEBASE_INSTANCE", LAKEBASE_INSTANCE)


def mint_credential_token() -> str:
    """Return a Lakebase database password.

    In a deployed Databricks App the DB resource injects a rotated PGPASSWORD,
    so use that directly and do not call the SDK (the App runtime SDK may not
    expose w.database). Locally (no PGPASSWORD), mint a fresh OAuth credential
    via w.database.generate_database_credential(instance_names=[...]); the older
    w.postgres...endpoint= signature is stale and rejects a plain instance name.
    """
    injected = os.environ.get("PGPASSWORD")
    if injected:
        return injected

    import uuid

    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient()
    cred = w.database.generate_database_credential(
        request_id=str(uuid.uuid4()),
        instance_names=[_endpoint_name()],
    )
    return cred.token


class OAuthConnection(psycopg.Connection):
    """psycopg connection that injects the Lakebase password.

    When PGPASSWORD is injected (deployed App), psycopg already uses it from the
    environment, so this connection class only overrides the password in the
    local-dev path where a fresh OAuth token must be minted per connection.
    """

    @classmethod
    def connect(cls, conninfo: str = "", **kwargs):
        if not os.environ.get("PGPASSWORD"):
            kwargs["password"] = mint_credential_token()
        return super().connect(conninfo, **kwargs)


def _conninfo() -> str:
    return (
        f"dbname={os.environ.get('PGDATABASE', LAKEBASE_DATABASE)} "
        f"user={os.environ['PGUSER']} "
        f"host={os.environ['PGHOST']} "
        f"port={os.environ.get('PGPORT', '5432')} "
        f"sslmode={os.environ.get('PGSSLMODE', 'require')}"
    )


def make_pool(min_size: int = 1, max_size: int = 10, open_now: bool = True) -> ConnectionPool:
    """Return a Lakebase connection pool. Recycles physical conns at 45 min."""
    return ConnectionPool(
        conninfo=_conninfo(),
        connection_class=OAuthConnection,
        min_size=min_size,
        max_size=max_size,
        max_lifetime=2700,  # 45 min, before the ~60 min token expiry
        open=open_now,
    )
