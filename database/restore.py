#!/usr/bin/env python3
"""
Database restore utility for SQLite and PostgreSQL.
Usage:
    python restore.py --db-type sqlite --backup backup.sql [--db-path store.db]
    python restore.py --db-type postgresql --backup backup.sql --host localhost --db billing_app --user postgres
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def restore_sqlite(backup_path: str | Path, db_path: str | Path = None) -> bool:
    """Restore SQLite database from backup file."""
    if db_path is None:
        base_dir = Path(__file__).resolve().parent.parent
        db_path = base_dir / "database" / "runtime" / "store.db"
    
    backup_path = Path(backup_path)
    db_path = Path(db_path)
    
    if not backup_path.exists():
        print(f"❌ Backup file not found: {backup_path}")
        return False
    
    print(f"📥 Restoring SQLite from: {backup_path}")
    
    # Create backup of current DB before restoring
    if db_path.exists():
        backup_dir = db_path.parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        import shutil
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"store_before_restore_{timestamp}.db"
        shutil.copy2(db_path, backup_file)
        print(f"💾 Current database backed up to: {backup_file}")
    
    try:
        # Remove existing database
        if db_path.exists():
            db_path.unlink()
        
        # Restore from backup
        with open(backup_path, "r") as backup_file:
            sql_script = backup_file.read()
        
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.executescript(sql_script)
        conn.commit()
        conn.close()
        
        print(f"✅ Database restored successfully: {db_path}")
        return True
    except Exception as e:
        print(f"❌ Restore failed: {e}")
        return False


def restore_postgresql(
    backup_path: str | Path,
    host: str = "localhost",
    port: int = 5432,
    db_name: str = "billing_app",
    user: str = "postgres",
    password: str = None,
    drop_first: bool = False,
) -> bool:
    """Restore PostgreSQL database from backup file."""
    backup_path = Path(backup_path)
    
    if not backup_path.exists():
        print(f"❌ Backup file not found: {backup_path}")
        return False
    
    print(f"📥 Restoring PostgreSQL: {user}@{host}:{db_name}")
    
    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password
    
    try:
        if drop_first:
            print(f"🗑️  Dropping database {db_name}...")
            subprocess.run(
                [
                    "psql",
                    "-h", host,
                    "-p", str(port),
                    "-U", user,
                    "-d", "postgres",
                    "-c", f"DROP DATABASE IF EXISTS {db_name};",
                    "--no-password",
                ],
                check=True,
                env=env,
                capture_output=True,
            )
            
            print(f"🆕 Creating database {db_name}...")
            subprocess.run(
                [
                    "psql",
                    "-h", host,
                    "-p", str(port),
                    "-U", user,
                    "-d", "postgres",
                    "-c", f"CREATE DATABASE {db_name};",
                    "--no-password",
                ],
                check=True,
                env=env,
                capture_output=True,
            )
        
        print(f"⏳ Restoring from {backup_path}...")
        with open(backup_path, "r") as backup_file:
            subprocess.run(
                [
                    "psql",
                    "-h", host,
                    "-p", str(port),
                    "-U", user,
                    "-d", db_name,
                    "--no-password",
                ],
                stdin=backup_file,
                check=True,
                env=env,
                capture_output=True,
            )
        
        print(f"✅ Database restored successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Restore failed: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr.decode('utf-8', errors='ignore')}")
        return False
    except FileNotFoundError:
        print("❌ psql command not found. Install postgresql client tools.")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Restore database from backup")
    parser.add_argument("--backup", "-b", required=True, help="Backup file path")
    parser.add_argument(
        "--db-type",
        choices=["sqlite", "postgresql"],
        default="sqlite",
        help="Database type (default: sqlite)",
    )
    parser.add_argument("--db-path", help="SQLite database path (for sqlite)")
    parser.add_argument("--drop-first", action="store_true", help="Drop database before restoring (PostgreSQL)")
    
    # PostgreSQL arguments
    parser.add_argument("--host", default="localhost", help="PostgreSQL host")
    parser.add_argument("--port", type=int, default=5432, help="PostgreSQL port")
    parser.add_argument("--db", default="billing_app", help="PostgreSQL database name")
    parser.add_argument("--user", default="postgres", help="PostgreSQL user")
    parser.add_argument("--password", help="PostgreSQL password (optional)")
    
    args = parser.parse_args()
    
    if args.db_type == "sqlite":
        success = restore_sqlite(backup_path=args.backup, db_path=args.db_path)
    else:
        success = restore_postgresql(
            backup_path=args.backup,
            host=args.host,
            port=args.port,
            db_name=args.db,
            user=args.user,
            password=args.password,
            drop_first=args.drop_first,
        )
    
    sys.exit(0 if success else 1)
