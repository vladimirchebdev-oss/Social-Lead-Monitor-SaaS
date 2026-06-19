"""Apply db/init.sql on empty databases (no incremental migrations)."""

from __future__ import annotations

import logging
from pathlib import Path

from db.connection import get_connection

logger = logging.getLogger(__name__)

INIT_SQL = Path(__file__).resolve().parent / "init.sql"


def _schema_ready(conn) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass('public.users')")
        return cur.fetchone()[0] is not None


def ensure_schema() -> bool:
    """Run init.sql if SaaS tables are missing. Returns True if schema was applied."""
    with get_connection() as conn:
        if _schema_ready(conn):
            return False
        sql = INIT_SQL.read_text(encoding="utf-8")
        logger.info("Applying database schema from init.sql")
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        logger.info("Database schema ready")
        return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if ensure_schema():
        print("Schema applied.")
    else:
        print("Schema already present.")
