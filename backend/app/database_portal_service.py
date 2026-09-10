import re
import time
import datetime
import uuid
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

try:
    from app.config import settings
    from app.database import engine as local_engine
except ImportError:
    from .config import settings
    from .database import engine as local_engine


logger = logging.getLogger("washqueue-db-portal")

# Cached cloud engine
_cloud_engine: Optional[AsyncEngine] = None

def get_cloud_engine() -> Optional[AsyncEngine]:
    global _cloud_engine
    cloud_url = settings.async_cloud_database_url
    if not cloud_url:
        return None
    if _cloud_engine is None:
        _cloud_engine = create_async_engine(cloud_url, pool_pre_ping=True)
    return _cloud_engine

def _get_engine_for_target(target: str):
    if target == "local":
        return local_engine, "sqlite"
    elif target == "cloud":
        cloud_eng = get_cloud_engine()
        if cloud_eng is None:
            raise ValueError("Cloud database is not configured. Please add CLOUD_DATABASE_URL (or SUPABASE_DATABASE_URL) to your .env file.")
        return cloud_eng, "postgresql"
    else:
        raise ValueError(f"Unknown database target: '{target}'. Must be 'local' or 'cloud'.")

def _serialize_val(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, (datetime.datetime, datetime.date, datetime.time)):
        return val.isoformat()
    if isinstance(val, uuid.UUID):
        return str(val)
    if isinstance(val, bytes):
        return f"<binary {len(val)} bytes>"
    return val

class DatabasePortalService:
    """
    Service for inspecting and executing queries across both Local (SQLite)
    and Cloud (Supabase / PostgreSQL) databases.
    """

    @staticmethod
    async def get_status(target: str = "local") -> Dict[str, Any]:
        """
        Returns connection health, dialect, and list of tables with row counts.
        """
        try:
            engine, dialect = _get_engine_for_target(target)
            tables = []

            async with engine.connect() as conn:
                if dialect == "sqlite":
                    res = await conn.execute(text(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                    ))
                    table_names = [row[0] for row in res.fetchall()]
                else:
                    res = await conn.execute(text(
                        "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name"
                    ))
                    table_names = [row[0] for row in res.fetchall()]

                for tbl in table_names:
                    # Sanitize table name (only alphanumeric and underscore)
                    if not re.match(r"^[a-zA-Z0-9_]+$", tbl):
                        continue
                    count_res = await conn.execute(text(f"SELECT COUNT(*) FROM \"{tbl}\""))
                    cnt = count_res.scalar() or 0
                    tables.append({
                        "name": tbl,
                        "row_count": cnt
                    })

            return {
                "target": target,
                "connected": True,
                "dialect": dialect,
                "tables": tables,
                "error": None
            }
        except Exception as e:
            logger.warning(f"Failed to connect to target database '{target}': {e}")
            return {
                "target": target,
                "connected": False,
                "dialect": "unknown",
                "tables": [],
                "error": str(e)
            }

    @staticmethod
    async def get_table_data(
        target: str = "local",
        table_name: str = "machines",
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Returns table schema and paginated rows.
        """
        # Validate table name to prevent SQL injection
        if not re.match(r"^[a-zA-Z0-9_]+$", table_name):
            raise ValueError(f"Invalid table name: '{table_name}'")

        engine, dialect = _get_engine_for_target(target)

        async with engine.connect() as conn:
            # Get total count
            count_res = await conn.execute(text(f"SELECT COUNT(*) FROM \"{table_name}\""))
            total = count_res.scalar() or 0

            # Get rows
            query = text(f"SELECT * FROM \"{table_name}\" LIMIT :limit OFFSET :offset")
            res = await conn.execute(query, {"limit": limit, "offset": offset})
            columns = list(res.keys())
            raw_rows = res.fetchall()

            rows = []
            for r in raw_rows:
                row_dict = {}
                for idx, col in enumerate(columns):
                    row_dict[col] = _serialize_val(r[idx])
                rows.append(row_dict)

            return {
                "target": target,
                "table_name": table_name,
                "total": total,
                "limit": limit,
                "offset": offset,
                "columns": columns,
                "rows": rows
            }

    @staticmethod
    async def execute_query(target: str, query_str: str) -> Dict[str, Any]:
        """
        Executes a raw read-only SQL query against the target database.
        Enforces safety guardrails to block destructive commands.
        """
        cleaned_query = query_str.strip()
        if not cleaned_query:
            raise ValueError("Query string cannot be empty.")

        # Read-only guardrail
        # Allow: SELECT, WITH, PRAGMA, EXPLAIN
        upper_q = cleaned_query.upper()
        allowed_starts = ("SELECT", "WITH", "PRAGMA", "EXPLAIN")
        if not any(upper_q.startswith(kw) for kw in allowed_starts):
            raise ValueError("Only read-only queries (SELECT, WITH, PRAGMA, EXPLAIN) are permitted in this console.")

        # Block dangerous keywords if appearing as independent statements
        destructive_pattern = r"\b(DROP|DELETE|TRUNCATE|UPDATE|INSERT|ALTER|CREATE|GRANT|REVOKE|REPLACE)\b"
        if re.search(destructive_pattern, upper_q):
            raise ValueError("Destructive commands (DROP, DELETE, UPDATE, INSERT, ALTER, etc.) are strictly prohibited.")

        engine, dialect = _get_engine_for_target(target)

        t1 = time.perf_counter()
        async with engine.connect() as conn:
            res = await conn.execute(text(cleaned_query))
            t2 = time.perf_counter()
            execution_time_ms = round((t2 - t1) * 1000, 2)

            columns = list(res.keys()) if res.returns_rows else []
            raw_rows = res.fetchall() if res.returns_rows else []

            rows = []
            for r in raw_rows:
                row_dict = {}
                for idx, col in enumerate(columns):
                    row_dict[col] = _serialize_val(r[idx])
                rows.append(row_dict)

            return {
                "target": target,
                "dialect": dialect,
                "query": cleaned_query,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "execution_time_ms": execution_time_ms
            }
