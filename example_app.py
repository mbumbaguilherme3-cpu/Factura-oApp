"""
Example Flask app with rate limiting and audit logging.
Shows integration of rate limiter and archiving modules.
"""

from flask import Flask, jsonify
from billing_app.rate_limiter import rate_limit, apply_global_rate_limit, get_limiter_stats
from billing_app.database import get_connection, initialize_database
from billing_app.archiving import archive_old_audit_logs


app = Flask(__name__)


@app.before_request
def init_db():
    """Initialize database on first request."""
    try:
        initialize_database(with_seed=False)  # Skip seed in app initialization
    except Exception:
        pass  # DB already initialized


# Example 1: Rate limit specific routes
@app.route("/api/invoices", methods=["GET"])
@rate_limit(limit=100, window=60)  # 100 requests per minute
def get_invoices():
    """Get all invoices (rate limited)."""
    return jsonify({
        "invoices": [
            {"invoice_id": 1, "total_amount": 1000},
            {"invoice_id": 2, "total_amount": 2000},
        ]
    })


@app.route("/api/invoices/<int:invoice_id>", methods=["GET"])
@rate_limit(limit=200, window=60)  # Higher limit for individual lookups
def get_invoice(invoice_id):
    """Get specific invoice."""
    return jsonify({
        "invoice_id": invoice_id,
        "total_amount": 1000,
        "status": "OPEN"
    })


@app.route("/api/invoices", methods=["POST"])
@rate_limit(limit=10, window=60)  # Stricter limit for writes
def create_invoice():
    """Create invoice (stricter rate limit)."""
    return jsonify({
        "success": True,
        "invoice_id": 999,
        "message": "Invoice created"
    }), 201


# Example 2: Public routes without rate limiting
@app.route("/health", methods=["GET"])
def health():
    """Health check (no rate limiting)."""
    return jsonify({"status": "ok"})


# Example 3: Admin operations
@app.route("/admin/audit/archive", methods=["POST"])
@rate_limit(limit=1, window=3600)  # 1 per hour (admin operation)
def archive_audit_logs():
    """Archive old audit logs (admin only - very restrictive)."""
    connection = get_connection()
    try:
        result = archive_old_audit_logs(connection, days=90)
        return jsonify(result)
    finally:
        connection.close()


@app.route("/admin/rate-limit/stats", methods=["GET"])
@rate_limit(limit=5, window=60)
def rate_limit_stats():
    """Get rate limiter statistics (admin debugging)."""
    stats = get_limiter_stats()
    return jsonify(stats)


# Example 4: Custom rate limit key (by user role)
@app.route("/api/reports/advanced", methods=["GET"])
@rate_limit(
    limit=50,
    window=60,
    by_user=True,
    by_ip=False,  # Use user ID instead of IP
)
def advanced_reports():
    """Advanced reports (limited by user)."""
    return jsonify({
        "report": "Advanced analytics",
        "data": [...]
    })


# Error handlers
@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded."""
    return jsonify({
        "error": "Too Many Requests",
        "message": "You have exceeded the rate limit. Please try again later.",
    }), 429


@app.errorhandler(500)
def internal_error(e):
    """Handle internal errors."""
    return jsonify({
        "error": "Internal Server Error",
        "message": str(e),
    }), 500


if __name__ == "__main__":
    # Initialize database
    try:
        initialize_database(with_seed=True)
        print("✅ Database initialized")
    except Exception as e:
        print(f"⚠️  Database init warning: {e}")
    
    # Uncomment to enable global rate limiting on all requests
    # apply_global_rate_limit(app)
    
    # Run development server
    app.run(debug=True, host="0.0.0.0", port=5000)
