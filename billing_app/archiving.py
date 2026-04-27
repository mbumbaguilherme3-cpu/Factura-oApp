"""
Audit log archiving module - manages retention and archiving of audit logs.
Keeps recent logs for quick access and archives old ones for compliance.
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


ARCHIVE_RETENTION_DAYS = int(os.getenv("AUDIT_RETENTION_DAYS", "90"))
ARCHIVE_DIR = Path(__file__).resolve().parent.parent / "database" / "archives"


def archive_old_audit_logs(connection: Any, days: int = ARCHIVE_RETENTION_DAYS) -> dict:
    """
    Archive audit logs older than specified days to file.
    
    Args:
        connection: Database connection
        days: Days to retain in database (default: 90)
    
    Returns:
        Dictionary with archive stats (count, file_path, etc.)
    """
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    
    cutoff_date = datetime.now() - timedelta(days=days)
    cutoff_str = cutoff_date.strftime("%Y-%m-%d %H:%M:%S")
    
    # Detect database type
    db_type = os.getenv("DB_TYPE", "sqlite").lower()
    
    if db_type == "postgresql":
        return _archive_postgresql(connection, cutoff_str)
    else:
        return _archive_sqlite(connection, cutoff_str)


def _archive_sqlite(connection: Any, cutoff_str: str) -> dict:
    """Archive SQLite audit logs."""
    import sqlite3
    import json
    
    # Export logs to JSON
    cursor = connection.execute(
        """
        SELECT 
            audit_log_id,
            user_id,
            action,
            entity_type,
            entity_id,
            details,
            ip_address,
            created_at
        FROM audit_logs
        WHERE created_at < ?
        ORDER BY created_at DESC
        """,
        (cutoff_str,),
    )
    
    rows = cursor.fetchall()
    if not rows:
        return {"archived_count": 0, "message": "No logs to archive"}
    
    # Convert to list of dicts
    logs = []
    for row in rows:
        logs.append({
            "audit_log_id": row["audit_log_id"],
            "user_id": row["user_id"],
            "action": row["action"],
            "entity_type": row["entity_type"],
            "entity_id": row["entity_id"],
            "details": row["details"],
            "ip_address": row["ip_address"],
            "created_at": row["created_at"],
        })
    
    # Save to JSON file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_file = ARCHIVE_DIR / f"audit_logs_{timestamp}.json"
    
    with open(archive_file, "w") as f:
        json.dump(logs, f, indent=2)
    
    # Delete archived logs from database
    connection.execute(
        "DELETE FROM audit_logs WHERE created_at < ?",
        (cutoff_str,),
    )
    connection.commit()
    
    return {
        "archived_count": len(logs),
        "archive_file": str(archive_file),
        "cutoff_date": cutoff_str,
        "message": f"Archived {len(logs)} audit logs",
    }


def _archive_postgresql(connection: Any, cutoff_str: str) -> dict:
    """Archive PostgreSQL audit logs."""
    import json
    
    cursor = connection.cursor()
    
    # Export logs
    cursor.execute(
        """
        SELECT 
            audit_log_id,
            user_id,
            action,
            entity_type,
            entity_id,
            details,
            ip_address,
            created_at
        FROM audit_logs
        WHERE created_at < %s
        ORDER BY created_at DESC
        """,
        (cutoff_str,),
    )
    
    rows = cursor.fetchall()
    if not rows:
        cursor.close()
        return {"archived_count": 0, "message": "No logs to archive"}
    
    # Convert to list of dicts
    logs = []
    for row in rows:
        logs.append({
            "audit_log_id": row[0],
            "user_id": row[1],
            "action": row[2],
            "entity_type": row[3],
            "entity_id": row[4],
            "details": row[5],
            "ip_address": row[6],
            "created_at": row[7].isoformat() if hasattr(row[7], 'isoformat') else str(row[7]),
        })
    
    # Save to JSON file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_file = ARCHIVE_DIR / f"audit_logs_{timestamp}.json"
    
    with open(archive_file, "w") as f:
        json.dump(logs, f, indent=2)
    
    # Delete archived logs from database
    cursor.execute(
        "DELETE FROM audit_logs WHERE created_at < %s",
        (cutoff_str,),
    )
    connection.commit()
    cursor.close()
    
    return {
        "archived_count": len(logs),
        "archive_file": str(archive_file),
        "cutoff_date": cutoff_str,
        "message": f"Archived {len(logs)} audit logs",
    }


def restore_from_archive(archive_file: str | Path) -> dict:
    """
    Restore archived audit logs from JSON file (read-only for compliance).
    
    Args:
        archive_file: Path to JSON archive file
    
    Returns:
        Archive metadata and sample of logs
    """
    archive_path = Path(archive_file)
    
    if not archive_path.exists():
        return {"error": f"Archive file not found: {archive_path}"}
    
    import json
    
    with open(archive_path, "r") as f:
        logs = json.load(f)
    
    return {
        "archive_file": str(archive_path),
        "total_logs": len(logs),
        "date_range": {
            "earliest": min(log["created_at"] for log in logs),
            "latest": max(log["created_at"] for log in logs),
        },
        "sample_logs": logs[:5],  # First 5 logs as sample
    }


def cleanup_archives(keep_days: int = 730) -> dict:
    """
    Clean up old archive files (default: keep 2 years).
    
    Args:
        keep_days: Days of archives to keep
    
    Returns:
        Cleanup statistics
    """
    if not ARCHIVE_DIR.exists():
        return {"cleaned_count": 0, "message": "Archive directory not found"}
    
    cutoff_date = datetime.now() - timedelta(days=keep_days)
    cleaned_count = 0
    
    for archive_file in ARCHIVE_DIR.glob("audit_logs_*.json"):
        file_mtime = datetime.fromtimestamp(archive_file.stat().st_mtime)
        if file_mtime < cutoff_date:
            archive_file.unlink()
            cleaned_count += 1
    
    return {
        "cleaned_count": cleaned_count,
        "keep_days": keep_days,
        "cutoff_date": cutoff_date.strftime("%Y-%m-%d"),
        "message": f"Cleaned up {cleaned_count} archive files",
    }
