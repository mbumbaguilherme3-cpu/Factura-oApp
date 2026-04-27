from __future__ import annotations

from datetime import UTC, datetime, timedelta
import secrets

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False


SESSION_MAX_AGE_SECONDS = 60 * 60 * 12

ROLE_PERMISSIONS = {
    "ADMIN": {
        "dashboard",
        "customers",
        "categories",
        "products",
        "invoices",
        "payments",
        "stock",
        "suppliers",
        "stock_entries",
        "cash",
        "reports",
        "settings",
        "users",
        "audit",
        "backup",
    },
    "MANAGER": {
        "dashboard",
        "customers",
        "categories",
        "products",
        "invoices",
        "payments",
        "stock",
        "suppliers",
        "stock_entries",
        "cash",
        "reports",
        "settings",
        "backup",
    },
    "CASHIER": {
        "dashboard",
        "customers",
        "invoices",
        "payments",
        "cash",
        "reports",
    },
    "STOCK": {
        "dashboard",
        "categories",
        "products",
        "stock",
        "suppliers",
        "stock_entries",
        "reports",
    },
}


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt (if available) or PBKDF2 fallback.
    
    Args:
        password: Plaintext password string.
    
    Returns:
        Hashed password string.
    
    Raises:
        ValueError: If password is empty or too short.
    """
    if not password or not isinstance(password, str):
        raise ValueError("Password must be a non-empty string")
    
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    
    if BCRYPT_AVAILABLE:
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return f"bcrypt${hashed.decode('utf-8')}"
    else:
        # Fallback to PBKDF2 if bcrypt not available
        import hashlib
        import hmac
        
        salt = secrets.token_hex(16)
        iterations = 600_000
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        )
        return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verify a plaintext password against its stored hash (bcrypt or PBKDF2).
    
    Args:
        password: Plaintext password to verify.
        stored_hash: Hash stored in database.
    
    Returns:
        True if password matches hash, False otherwise.
    """
    if not password or not stored_hash:
        return False
    
    try:
        if stored_hash.startswith("bcrypt$"):
            if not BCRYPT_AVAILABLE:
                return False
            hashed_part = stored_hash.split("$", 1)[1]
            return bcrypt.checkpw(password.encode("utf-8"), hashed_part.encode("utf-8"))
        
        elif stored_hash.startswith("pbkdf2_sha256$"):
            import hashlib
            import hmac
            
            try:
                algorithm, iterations_text, salt, digest = stored_hash.split("$", 3)
            except ValueError:
                return False

            if algorithm != "pbkdf2_sha256":
                return False

            candidate = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                int(iterations_text),
            ).hex()
            return hmac.compare_digest(candidate, digest)
        
        else:
            return False
    except (ValueError, TypeError):
        return False


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength based on OWASP guidelines.
    
    Args:
        password: Plaintext password to validate.
    
    Returns:
        Tuple of (is_valid, message).
    """
    if not password:
        return False, "Password cannot be empty"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if len(password) > 128:
        return False, "Password must not exceed 128 characters"
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    
    if not (has_upper and has_lower and has_digit):
        return False, (
            "Password must contain uppercase letters, lowercase letters, and digits."
        )
    
    return True, "Password is strong"


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def session_expiry_timestamp() -> str:
    return (datetime.now(UTC) + timedelta(seconds=SESSION_MAX_AGE_SECONDS)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def role_allows(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())
