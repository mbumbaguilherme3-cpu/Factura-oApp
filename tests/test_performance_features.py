import os
import tempfile
import json
from pathlib import Path
import pytest
import sqlite3

from billing_app.rate_limiter import RateLimiter, get_client_ip, rate_limit
from billing_app.archiving import archive_old_audit_logs, restore_from_archive, cleanup_archives


class TestRateLimiter:
    """Tests for the rate limiting system."""
    
    def test_rate_limiter_allows_requests_below_limit(self):
        """Test that requests below limit are allowed."""
        limiter = RateLimiter()
        
        # Allow 3 requests per 60 seconds
        assert limiter.is_allowed("user:1", limit=3, window_seconds=60)
        assert limiter.is_allowed("user:1", limit=3, window_seconds=60)
        assert limiter.is_allowed("user:1", limit=3, window_seconds=60)
    
    def test_rate_limiter_rejects_requests_above_limit(self):
        """Test that requests above limit are rejected."""
        limiter = RateLimiter()
        
        # Allow 2 requests per 60 seconds
        assert limiter.is_allowed("user:1", limit=2, window_seconds=60)
        assert limiter.is_allowed("user:1", limit=2, window_seconds=60)
        assert not limiter.is_allowed("user:1", limit=2, window_seconds=60)  # 3rd should fail
    
    def test_rate_limiter_separate_keys(self):
        """Test that rate limits are per-key."""
        limiter = RateLimiter()
        
        # Each user has independent limit
        assert limiter.is_allowed("user:1", limit=2, window_seconds=60)
        assert limiter.is_allowed("user:2", limit=2, window_seconds=60)
        assert limiter.is_allowed("user:1", limit=2, window_seconds=60)
        assert limiter.is_allowed("user:2", limit=2, window_seconds=60)
        
        # Both should be at limit now
        assert not limiter.is_allowed("user:1", limit=2, window_seconds=60)
        assert not limiter.is_allowed("user:2", limit=2, window_seconds=60)
    
    def test_rate_limiter_different_windows(self):
        """Test rate limiter with different time windows."""
        limiter = RateLimiter()
        
        # Set up: 5 requests per 10 seconds
        for _ in range(5):
            assert limiter.is_allowed("ip:127.0.0.1", limit=5, window_seconds=10)
        
        # Should be rejected now
        assert not limiter.is_allowed("ip:127.0.0.1", limit=5, window_seconds=10)


class TestArchiving:
    """Tests for audit log archiving."""
    
    def test_archive_sqlite_audit_logs(self):
        """Test archiving audit logs from SQLite database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            os.environ["AUDIT_RETENTION_DAYS"] = "90"
            
            # Create test database with audit logs
            conn = sqlite3.connect(db_path)
            conn.execute("""
                CREATE TABLE audit_logs (
                    audit_log_id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    action TEXT,
                    entity_type TEXT,
                    entity_id TEXT,
                    details TEXT,
                    ip_address TEXT,
                    created_at TEXT
                )
            """)
            
            # Insert old log (older than 90 days)
            conn.execute("""
                INSERT INTO audit_logs VALUES (
                    1, 1, 'CREATE', 'INVOICE', '123',
                    'Invoice created', '127.0.0.1',
                    datetime('now', '-100 days')
                )
            """)
            
            # Insert recent log
            conn.execute("""
                INSERT INTO audit_logs VALUES (
                    2, 1, 'READ', 'INVOICE', '123',
                    'Invoice viewed', '127.0.0.1',
                    datetime('now')
                )
            """)
            
            conn.commit()
            
            # Archive old logs
            result = archive_old_audit_logs(conn, days=90)
            conn.close()
            
            # Verify results
            assert result["archived_count"] == 1, "Should archive 1 old log"
            assert "archive_file" in result
            assert Path(result["archive_file"]).exists()
            
            # Verify old log is gone
            conn = sqlite3.connect(db_path)
            remaining = conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
            conn.close()
            
            assert remaining == 1, "Should have 1 recent log remaining"
    
    def test_restore_from_archive(self):
        """Test restoring archived logs from JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            archive_dir = Path(tmpdir)
            
            # Create archive file
            archive_data = [
                {
                    "audit_log_id": 1,
                    "user_id": 1,
                    "action": "CREATE",
                    "entity_type": "INVOICE",
                    "entity_id": "123",
                    "details": "Invoice created",
                    "ip_address": "127.0.0.1",
                    "created_at": "2024-01-01 10:00:00"
                }
            ]
            
            archive_file = archive_dir / "audit_logs_20240101_100000.json"
            with open(archive_file, "w") as f:
                json.dump(archive_data, f)
            
            # Restore
            result = restore_from_archive(archive_file)
            
            assert result["total_logs"] == 1
            assert len(result["sample_logs"]) == 1
            assert result["sample_logs"][0]["action"] == "CREATE"
    
    def test_archive_file_not_found(self):
        """Test error handling for missing archive file."""
        result = restore_from_archive("/nonexistent/archive.json")
        assert "error" in result


class TestPasswordHashing:
    """Tests for password hashing (moved from earlier test)."""
    
    def test_bcrypt_hashing(self):
        """Test bcrypt password hashing."""
        from billing_app.security import hash_password, verify_password
        
        password = "SecurePass123"
        hashed = hash_password(password)
        
        # Should be hashed
        assert hashed != password
        assert "bcrypt$" in hashed or "pbkdf2" in hashed
        
        # Should verify
        assert verify_password(password, hashed)
        assert not verify_password("WrongPass123", hashed)
    
    def test_password_strength_validation(self):
        """Test password strength requirements."""
        from billing_app.security import validate_password_strength
        
        # Too short
        is_valid, msg = validate_password_strength("short")
        assert not is_valid
        
        # No uppercase
        is_valid, msg = validate_password_strength("lowercase123")
        assert not is_valid
        
        # No numbers
        is_valid, msg = validate_password_strength("PasswordOnly")
        assert not is_valid
        
        # Valid
        is_valid, msg = validate_password_strength("ValidPass123")
        assert is_valid
