"""Apply schema.sql to the Lakebase database. Idempotent.

Run once by the instructor after the Lakebase instance exists:

    PGHOST=... PGUSER=... python -m app.db.apply_schema

Reads the OAuth token via the connection helper. The whole file is CREATE ...
IF NOT EXISTS / CREATE OR REPLACE, so re-running is safe.
"""

from __future__ import annotations

from pathlib import Path

from app.db.connection import make_pool

_SCHEMA = Path(__file__).with_name("schema.sql")


def apply_schema() -> None:
    sql = _SCHEMA.read_text()
    pool = make_pool(min_size=1, max_size=2)
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
    finally:
        pool.close()
    print(f"applied {_SCHEMA.name}")


if __name__ == "__main__":
    apply_schema()
