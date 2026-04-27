#!/usr/bin/env python3
"""
Database backup utility for SQLite and PostgreSQL.
Usage:
    python backup.py --db-type sqlite [--output backup.sql]
    python backup.py --db-type postgresql --host localhost --db billing_app --user postgres [--output backup.sql]
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def backup_sqlite(db_path: str | Path = None, output: str | Path = None) -> Path:
    """Backup SQLite database using .dump command."""
    if db_path is None:
        base_dir = Path(__file__).resolve().parent.parent
        db_path = base_dir / "database" / "runtime" / "store.db"
    
    if output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = Path(f"backup_sqlite_{timestamp}.sql")
    else:
        output = Path(output)
    
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"❌ SQLite database not found: {db_path}")
        return None
    
    print(f"📦 Backing up SQLite database: {db_path}")
    
    try:
        with open(db_path, "rb") as db_file, open(output, "wb") as backup_file:
            subprocess.run(
                ["sqlite3", str(db_path), ".dump"],
                stdout=backup_file,
                check=True,
                text=False,
            )
        
        size_mb = output.stat().st_size / (1024 * 1024)
        print(f"✅ Backup created: {output} ({size_mb:.2f} MB)")
        return output
    except subprocess.CalledProcessError as e:
        print(f"❌ Backup failed: {e}")
        return None
    except FileNotFoundError:
        print("❌ sqlite3 command not found. Install sqlite3 package.")
        return None


def backup_postgresql(
    host: str = "localhost",
    port: int = 5432,
    db_name: str = "billing_app",
    user: str = "postgres",
    password: str = None,
    output: str | Path = None,
) -> Path:
    """Backup PostgreSQL database using pg_dump."""
    if output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = Path(f"backup_postgresql_{timestamp}.sql")
    else:
        output = Path(output)
    
    print(f"📦 Backing up PostgreSQL: {user}@{host}:{db_name}")
    
    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password
    
    try:
        with open(output, "w") as backup_file:
            subprocess.run(
                [
                    "pg_dump",
                    "-h", host,
                    "-p", str(port),
                    "-U", user,
                    "-d", db_name,
                    "--no-password",
                ],
                stdout=backup_file,
                stderr=subprocess.PIPE,
                check=True,
                env=env,
            )
        
        size_mb = output.stat().st_size / (1024 * 1024)
        print(f"✅ Backup created: {output} ({size_mb:.2f} MB)")
        return output
    except subprocess.CalledProcessError as e:
        print(f"❌ Backup failed: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr.decode('utf-8', errors='ignore')}")
        return None
    except FileNotFoundError:
        print("❌ pg_dump command not found. Install postgresql client tools.")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backup database")
    parser.add_argument(
        "--db-type",
        choices=["sqlite", "postgresql"],
        default="sqlite",
        help="Database type (default: sqlite)",
    )
    parser.add_argument("--output", "-o", help="Output backup file path")
    parser.add_argument("--db-path", help="SQLite database path (for sqlite)")
    
    # PostgreSQL arguments
    parser.add_argument("--host", default="localhost", help="PostgreSQL host")
    parser.add_argument("--port", type=int, default=5432, help="PostgreSQL port")
    parser.add_argument("--db", default="billing_app", help="PostgreSQL database name")
    parser.add_argument("--user", default="postgres", help="PostgreSQL user")
    parser.add_argument("--password", help="PostgreSQL password (optional)")
    
    args = parser.parse_args()
    
    if args.db_type == "sqlite":
        backup_sqlite(db_path=args.db_path, output=args.output)
    else:
        backup_postgresql(
            host=args.host,
            port=args.port,
            db_name=args.db,
            user=args.user,
            password=args.password,
            output=args.output,
        )
