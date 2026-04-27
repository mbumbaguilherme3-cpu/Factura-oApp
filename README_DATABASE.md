# Database Setup & Operations

This project supports both **SQLite** (development/testing) and **PostgreSQL** (production).

## Quick Start

### SQLite (Default)

No additional setup needed! SQLite database will be created automatically at `database/runtime/store.db` when you initialize the app.

```bash
# Initialize database with migrations and seed data
python -m billing_app.database

# Or in Python:
from billing_app.database import initialize_database
initialize_database(with_seed=True)
```

### PostgreSQL (Production)

1. **Install PostgreSQL** and create a database:
   ```bash
   createdb billing_app
   ```

2. **Create `.env` file** (copy from `.env.example`):
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env`** with your PostgreSQL credentials:
   ```env
   DB_TYPE=postgresql
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=billing_app
   DB_USER=postgres
   DB_PASSWORD=your_password
   ```

4. **Initialize database**:
   ```bash
   python -m billing_app.database
   ```

## Schema Overview

### Core Tables
- **customers** - Customer information with contact details
- **product_categories** - Product categories and classifications
- **products** - Product inventory with pricing and stock
- **invoices** - Sales invoices with totals and status
- **invoice_items** - Line items for invoices
- **payments** - Payment records linked to invoices

### Operations
- **suppliers** - Supplier information
- **stock_entries** - Purchase orders from suppliers
- **stock_entry_items** - Line items for stock entries
- **stock_movements** - Complete audit trail of stock changes (INITIAL, SALE, PURCHASE, ADJUSTMENT)

### Security & Sessions
- **app_users** - User accounts with ADMIN/MANAGER/CASHIER/STOCK roles
- **app_sessions** - Active user sessions with tokens and expiry
- **audit_logs** - Complete audit trail of all system actions

### Business Operations
- **cash_sessions** - Daily cash reconciliation sessions
- **cash_movements** - All cash movements (opening, sales, manual adjustments)
- **business_settings** - Company configuration (name, tax rates, currency, etc.)

## Migrations

Migrations are versioned and applied automatically on app startup.

### SQLite Migrations
- `001_initial_core.sql` - Core tables (customers, products, invoices, payments)
- `002_security_and_operations.sql` - Users, sessions, suppliers, stock, cash, audit
- `003_stock_entry_fk.sql` - Foreign key constraints for stock entries

### PostgreSQL Migrations
- `001_pg_initial_core.sql` - Core tables
- `002_pg_security_and_operations.sql` - Security and operations
- `003_pg_stock_entry_fk.sql` - Foreign key constraints

Migration status is tracked in `schema_migrations` table.

## Backup & Restore

### Backup SQLite
```bash
python database/backup.py --db-type sqlite --output backup_$(date +%Y%m%d_%H%M%S).sql
```

### Backup PostgreSQL
```bash
python database/backup.py \
  --db-type postgresql \
  --host localhost \
  --db billing_app \
  --user postgres \
  --password your_password \
  --output backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restore SQLite
```bash
python database/restore.py --db-type sqlite --backup backup_20240101_120000.sql
```

### Restore PostgreSQL
```bash
python database/restore.py \
  --db-type postgresql \
  --backup backup_20240101_120000.sql \
  --host localhost \
  --db billing_app \
  --user postgres \
  --password your_password \
  --drop-first  # Optional: drops existing database before restoring
```

## Password Security

Passwords are hashed using **bcrypt** (12 rounds, resistant to GPU attacks) with PBKDF2 fallback for legacy systems.

### Password Requirements
- Minimum 8 characters
- Must contain: uppercase, lowercase, and digits
- Maximum 128 characters

```python
from billing_app.security import hash_password, verify_password, validate_password_strength

# Hash a password
hashed = hash_password("MySecure123Pass")

# Verify password
is_valid = verify_password("MySecure123Pass", hashed)

# Validate strength
is_strong, message = validate_password_strength("MySecure123Pass")
```

## Testing

### Run All Tests
```bash
pytest tests/ -v
```

### Test SQLite
```bash
DB_TYPE=sqlite pytest tests/ -v
```

### Test PostgreSQL
```bash
DB_TYPE=postgresql \
DB_HOST=localhost \
DB_PORT=5432 \
DB_NAME=billing_app_test \
DB_USER=postgres \
DB_PASSWORD=postgres \
pytest tests/ -v
```

### Coverage Report
```bash
pytest tests/ --cov=billing_app --cov-report=html
```

## Performance Tuning

### Indices
The schema includes optimized indices for common queries:
- `invoice_items`, `payments` - by invoice_id
- `stock_movements` - by product_id, invoice_id, stock_entry_id
- `app_sessions` - by session_token (fast lookups)
- `audit_logs` - by created_at and user_id

### Query Optimization
Monitor slow queries in production:

```sql
-- PostgreSQL: Check query execution times
EXPLAIN ANALYZE SELECT * FROM invoices WHERE issue_date > NOW() - INTERVAL '30 days';

-- SQLite: Enable query profiling
.timer ON
SELECT * FROM invoices WHERE issue_date > date('now', '-30 days');
```

## Troubleshooting

### Connection Issues
- **SQLite**: Ensure `database/runtime/` directory exists and is writable
- **PostgreSQL**: Check `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` in `.env`

### Migration Errors
- Check `schema_migrations` table to see which migrations have applied
- Manually inspect the migration file that failed
- For SQLite: delete `database/runtime/store.db` and reinitialize (development only!)
- For PostgreSQL: back up database, drop and recreate, then restore

### Performance Issues
- Run `ANALYZE` on tables (SQLite: `ANALYZE;`, PostgreSQL: `ANALYZE;`)
- Check `audit_logs` table size - may grow large in production (consider archiving)
- Monitor `cash_movements` and `stock_movements` for large inserts

## Production Deployment Checklist

- [ ] Use PostgreSQL (not SQLite)
- [ ] Enable SSL/TLS for database connections
- [ ] Set up automated daily backups
- [ ] Test restore procedures weekly
- [ ] Monitor database disk usage
- [ ] Enable query logging for debugging
- [ ] Set up alerts for failed connections
- [ ] Document recovery time objective (RTO) and recovery point objective (RPO)
- [ ] Schedule index maintenance/optimization
- [ ] Archive old audit logs regularly
