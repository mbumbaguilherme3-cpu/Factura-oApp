import os
import sqlite3
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "database" / "runtime" / "store.db"
MIGRATIONS_DIR = BASE_DIR / "database" / "migrations"

# Environment-based database selection
DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()  # "sqlite" or "postgresql"

if DB_TYPE == "postgresql":
    import psycopg2
    from psycopg2 import sql

    PG_HOST = os.getenv("DB_HOST", "localhost")
    PG_PORT = int(os.getenv("DB_PORT", "5432"))
    PG_NAME = os.getenv("DB_NAME", "billing_app")
    PG_USER = os.getenv("DB_USER", "postgres")
    PG_PASSWORD = os.getenv("DB_PASSWORD", "")

    POSTGRESQL_SCHEMA_PATH = BASE_DIR / "database" / "schema_postgresql.sql"
else:
    SQLITE_SCHEMA_PATH = BASE_DIR / "database" / "schema_sqlite.sql"

SEED_PATH = BASE_DIR / "database" / "seed.sql"


def get_connection() -> Any:
    """Get database connection (SQLite or PostgreSQL based on DB_TYPE env var)."""
    if DB_TYPE == "postgresql":
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            database=PG_NAME,
            user=PG_USER,
            password=PG_PASSWORD,
        )
        conn.autocommit = False
        return conn
    else:
        database_path = DEFAULT_DB_PATH
        database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


def initialize_database(with_seed: bool = True) -> None:
    """Initialize database schema, apply migrations, and optionally seed data."""
    from .admin import ensure_default_admin

    connection = get_connection()

    try:
        _ensure_migrations_table(connection)
        _apply_migrations(connection)
        ensure_default_admin(connection)

        if with_seed and _is_table_empty(connection, "product_categories"):
            _execute_seed(connection)

        connection.commit()
    finally:
        connection.close()


def _is_table_empty(connection: Any, table_name: str) -> bool:
    """Check if a table is empty."""
    if DB_TYPE == "postgresql":
        cursor = connection.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total = cursor.fetchone()[0]
        cursor.close()
    else:
        query = f"SELECT COUNT(*) AS total FROM {table_name}"
        total = connection.execute(query).fetchone()["total"]
    return total == 0


def _ensure_migrations_table(connection: Any) -> None:
    """Create schema_migrations table if it doesn't exist."""
    if DB_TYPE == "postgresql":
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                migration_name TEXT PRIMARY KEY,
                applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.close()
    else:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                migration_name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def _apply_migrations(connection: Any) -> None:
    """Apply pending migrations (database-specific)."""
    if DB_TYPE == "postgresql":
        cursor = connection.cursor()
        cursor.execute("SELECT migration_name FROM schema_migrations ORDER BY migration_name")
        applied = {row[0] for row in cursor.fetchall()}
        cursor.close()
    else:
        applied = {
            row["migration_name"]
            for row in connection.execute(
                "SELECT migration_name FROM schema_migrations ORDER BY migration_name"
            ).fetchall()
        }

    # Filter migrations by database type
    prefix = f"00*_pg_" if DB_TYPE == "postgresql" else f"00*_"
    migration_pattern = f"{prefix}*.sql" if DB_TYPE == "sqlite" else "00*_pg_*.sql"
    
    for migration_path in sorted(MIGRATIONS_DIR.glob(migration_pattern if DB_TYPE == "postgresql" else "00*.sql")):
        # Skip wrong database type
        if DB_TYPE == "postgresql" and "_pg_" not in migration_path.name:
            continue
        if DB_TYPE == "sqlite" and "_pg_" in migration_path.name:
            continue

        if migration_path.name in applied:
            continue

        migration_sql = migration_path.read_text(encoding="utf-8")

        if DB_TYPE == "postgresql":
            cursor = connection.cursor()
            cursor.execute(migration_sql)
            cursor.execute(
                "INSERT INTO schema_migrations (migration_name) VALUES (%s)",
                (migration_path.name,),
            )
            cursor.close()
        else:
            connection.executescript(migration_sql)
            connection.execute(
                "INSERT INTO schema_migrations (migration_name) VALUES (?)",
                (migration_path.name,),
            )


def _execute_seed(connection: Any) -> None:
    """Execute seed data SQL."""
    seed_sql = SEED_PATH.read_text(encoding="utf-8")
    if DB_TYPE == "postgresql":
        cursor = connection.cursor()
        cursor.execute(seed_sql)
        cursor.close()
    else:
        connection.executescript(seed_sql)
