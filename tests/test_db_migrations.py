import os
import sqlite3
from pathlib import Path
import pytest

# Only import PostgreSQL if available
try:
    import psycopg2
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

from billing_app.database import initialize_database, DB_TYPE


@pytest.mark.skipif(DB_TYPE != "sqlite", reason="SQLite-only test")
def test_migrations_and_seed_sqlite(tmp_path: Path):
    """Test SQLite migrations and seed data."""
    # Set DB_TYPE to sqlite for this test
    os.environ["DB_TYPE"] = "sqlite"
    
    db_file = tmp_path / "store.db"
    os.environ.pop("DB_PATH", None)  # Clear any previous DB_PATH
    
    # Manually initialize SQLite
    import sqlite3
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    
    try:
        # Create migrations table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                migration_name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        
        # Read and execute migrations
        migrations_dir = Path(__file__).resolve().parent.parent / "database" / "migrations"
        for migration_path in sorted(migrations_dir.glob("00*_initial_core.sql")):
            if "_pg_" in migration_path.name:
                continue
            
            migration_sql = migration_path.read_text(encoding="utf-8")
            conn.executescript(migration_sql)
            conn.execute(
                "INSERT INTO schema_migrations (migration_name) VALUES (?)",
                (migration_path.name,),
            )
        
        # Apply remaining migrations
        for migration_path in sorted(migrations_dir.glob("002*.sql")):
            if "_pg_" in migration_path.name:
                continue
            
            migration_sql = migration_path.read_text(encoding="utf-8")
            conn.executescript(migration_sql)
            conn.execute(
                "INSERT INTO schema_migrations (migration_name) VALUES (?)",
                (migration_path.name,),
            )
        
        for migration_path in sorted(migrations_dir.glob("003*.sql")):
            if "_pg_" in migration_path.name:
                continue
            
            migration_sql = migration_path.read_text(encoding="utf-8")
            conn.executescript(migration_sql)
            conn.execute(
                "INSERT INTO schema_migrations (migration_name) VALUES (?)",
                (migration_path.name,),
            )
        
        # Load and execute seed data
        seed_path = Path(__file__).resolve().parent.parent / "database" / "seed.sql"
        seed_sql = seed_path.read_text(encoding="utf-8")
        conn.executescript(seed_sql)
        
        conn.commit()
        
        # Verify
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        )
        assert cur.fetchone() is not None, "schema_migrations table not found"
        
        rows = conn.execute("SELECT migration_name FROM schema_migrations").fetchall()
        names = {r[0] for r in rows}
        assert len(names) >= 3, f"Expected at least 3 migrations, got {len(names)}"
        
        # Verify seed data
        pc = conn.execute("SELECT COUNT(*) FROM product_categories").fetchone()[0]
        assert pc >= 1, "No product categories found"
        
        prod = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        assert prod >= 1, "No products found"
        
        cust = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        assert cust >= 1, "No customers found"
        
    finally:
        conn.close()


@pytest.mark.skipif(not PSYCOPG2_AVAILABLE, reason="psycopg2 not installed")
@pytest.mark.skipif(DB_TYPE != "postgresql", reason="PostgreSQL-only test")
def test_migrations_and_seed_postgresql():
    """Test PostgreSQL migrations and seed data."""
    pytest.skip("PostgreSQL test requires running database - configure in CI")


def test_password_hashing():
    """Test password hashing and verification."""
    from billing_app.security import hash_password, verify_password, validate_password_strength
    
    password = "SecurePass123"
    
    # Test hashing
    hashed = hash_password(password)
    assert hashed != password, "Password should not be stored in plaintext"
    
    # Test verification
    assert verify_password(password, hashed), "Valid password should verify successfully"
    assert not verify_password("WrongPass123", hashed), "Invalid password should fail"
    
    # Test password strength
    weak_pass = "weak"
    is_strong, msg = validate_password_strength(weak_pass)
    assert not is_strong, f"Weak password should not validate: {msg}"
    
    strong_pass = "StrongPass123"
    is_strong, msg = validate_password_strength(strong_pass)
    assert is_strong, f"Strong password should validate: {msg}"
