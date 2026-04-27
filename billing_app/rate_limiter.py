"""
Rate limiting middleware for Flask API.
Prevents abuse by limiting requests per IP address and user.
"""

import os
import time
from functools import wraps
from typing import Optional, Callable, Any

from flask import request, jsonify
from werkzeug.exceptions import TooManyRequests


class RateLimiter:
    """Simple in-memory rate limiter (use Redis for production)."""
    
    def __init__(self):
        self.requests = {}  # {key: [(timestamp, count), ...]}
    
    def is_allowed(self, key: str, limit: int, window_seconds: int) -> bool:
        """
        Check if request is allowed under rate limit.
        
        Args:
            key: Identifier (IP, user_id, etc.)
            limit: Max requests allowed
            window_seconds: Time window in seconds
        
        Returns:
            True if request is allowed, False otherwise
        """
        now = time.time()
        cutoff = now - window_seconds
        
        if key not in self.requests:
            self.requests[key] = []
        
        # Clean old entries
        self.requests[key] = [
            (ts, count) for ts, count in self.requests[key]
            if ts > cutoff
        ]
        
        # Count requests in window
        current_count = sum(count for _, count in self.requests[key])
        
        if current_count < limit:
            if self.requests[key] and self.requests[key][-1][0] == now:
                # Increment count for same second
                self.requests[key][-1] = (now, self.requests[key][-1][1] + 1)
            else:
                self.requests[key].append((now, 1))
            return True
        
        return False


# Global rate limiter instance
_limiter = RateLimiter()

# Configuration (override via environment variables)
DEFAULT_RATE_LIMIT = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
DEFAULT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))


def get_client_ip() -> str:
    """Get client IP from request, handling proxies."""
    if request.environ.get("HTTP_X_FORWARDED_FOR"):
        return request.environ.get("HTTP_X_FORWARDED_FOR").split(",")[0].strip()
    return request.remote_addr


def get_user_id() -> Optional[str]:
    """Get user ID from session or auth header."""
    # Try to get from session (if user is logged in)
    if hasattr(request, 'user') and request.user:
        return str(request.user.get("user_id"))
    
    # Try to get from Authorization header (if using tokens)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]  # Simplified - in production validate token
    
    return None


def rate_limit(
    limit: int = DEFAULT_RATE_LIMIT,
    window: int = DEFAULT_WINDOW,
    key_func: Optional[Callable[[], str]] = None,
    by_ip: bool = True,
    by_user: bool = True,
) -> Callable:
    """
    Decorator for rate limiting Flask routes.
    
    Args:
        limit: Max requests in window
        window: Time window in seconds
        key_func: Custom function to generate rate limit key
        by_ip: Rate limit by IP address
        by_user: Rate limit by user ID
    
    Example:
        @app.route("/api/invoices")
        @rate_limit(limit=50, window=60)
        def get_invoices():
            return {"invoices": [...]}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if key_func:
                key = key_func()
            elif by_user and (user_id := get_user_id()):
                key = f"user:{user_id}"
            elif by_ip:
                key = f"ip:{get_client_ip()}"
            else:
                # No rate limiting key available
                return func(*args, **kwargs)
            
            if not _limiter.is_allowed(key, limit, window):
                return jsonify({
                    "error": "Rate limit exceeded",
                    "limit": limit,
                    "window_seconds": window,
                }), 429  # Too Many Requests
            
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def apply_global_rate_limit(app) -> None:
    """
    Apply global rate limiting to all requests (optional).
    
    Args:
        app: Flask application instance
    """
    @app.before_request
    def check_rate_limit() -> Optional[tuple]:
        key = f"ip:{get_client_ip()}"
        
        if not _limiter.is_allowed(key, DEFAULT_RATE_LIMIT, DEFAULT_WINDOW):
            return jsonify({
                "error": "Rate limit exceeded",
                "limit": DEFAULT_RATE_LIMIT,
                "window_seconds": DEFAULT_WINDOW,
            }), 429
        
        return None


def get_limiter_stats(key: Optional[str] = None) -> dict:
    """Get rate limiter statistics (for monitoring/debugging)."""
    if key:
        now = time.time()
        window = DEFAULT_WINDOW
        cutoff = now - window
        
        entries = _limiter.requests.get(key, [])
        entries = [(ts, count) for ts, count in entries if ts > cutoff]
        count = sum(c for _, c in entries)
        
        return {
            "key": key,
            "requests_in_window": count,
            "limit": DEFAULT_RATE_LIMIT,
            "window_seconds": DEFAULT_WINDOW,
            "remaining": max(0, DEFAULT_RATE_LIMIT - count),
        }
    
    # Return stats for all tracked keys
    return {
        "tracked_keys": len(_limiter.requests),
        "global_limit": DEFAULT_RATE_LIMIT,
        "global_window_seconds": DEFAULT_WINDOW,
    }
