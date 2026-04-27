# SSL/TLS Configuration for PostgreSQL

This guide covers setting up secure PostgreSQL connections in production.

## Quick Start (Production)

### 1. Generate Self-Signed Certificate (Development)

```bash
# Create certificate directory
mkdir -p ~/.postgresql

# Generate private key and certificate (10 years)
openssl req -x509 -newkey rsa:4096 -keyout ~/.postgresql/server.key \
  -out ~/.postgresql/server.crt -days 3650 -nodes \
  -subj "/C=AO/ST=Luanda/L=Luanda/O=YourCompany/CN=localhost"

# Set permissions (PostgreSQL requirement)
chmod 600 ~/.postgresql/server.key
```

### 2. Configure PostgreSQL (`postgresql.conf`)

```ini
# Enable SSL
ssl = on

# Certificate and key paths (absolute paths recommended)
ssl_cert_file = '/etc/postgresql/server.crt'
ssl_key_file = '/etc/postgresql/server.key'

# Optional: Require SSL for all connections
ssl_protocols = 'TLSv1.2,TLSv1.3'
```

### 3. Restart PostgreSQL

```bash
sudo systemctl restart postgresql
# or
pg_ctl -D /var/lib/postgresql/data restart
```

### 4. Connect with SSL from Python

Update `.env`:

```env
DB_TYPE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=billing_app
DB_USER=postgres
DB_PASSWORD=your_password
DB_SSL_MODE=require
DB_SSL_CERT=/path/to/client.crt
DB_SSL_KEY=/path/to/client.key
DB_SSL_ROOT_CERT=/path/to/root.crt
```

Update `billing_app/database.py`:

```python
import os
import psycopg2

# Get SSL settings from environment
ssl_mode = os.getenv("DB_SSL_MODE", "disable")  # disable, allow, prefer, require, verify-ca, verify-full
ssl_cert = os.getenv("DB_SSL_CERT")
ssl_key = os.getenv("DB_SSL_KEY")
ssl_root_cert = os.getenv("DB_SSL_ROOT_CERT")

# Build connection kwargs
conn_kwargs = {
    "host": DB_HOST,
    "port": DB_PORT,
    "database": DB_NAME,
    "user": DB_USER,
    "password": DB_PASSWORD,
    "sslmode": ssl_mode,
}

# Add SSL certificates if provided
if ssl_cert:
    conn_kwargs["sslcert"] = ssl_cert
if ssl_key:
    conn_kwargs["sslkey"] = ssl_key
if ssl_root_cert:
    conn_kwargs["sslrootcert"] = ssl_root_cert

conn = psycopg2.connect(**conn_kwargs)
```

## SSL Modes Explained

| Mode | Description | Use Case |
|------|-------------|----------|
| `disable` | No SSL | Development (not recommended) |
| `allow` | Try SSL, fallback to plain | Legacy systems |
| `prefer` | Prefer SSL, fallback to plain | Medium security |
| `require` | **Always use SSL** | Recommended for production |
| `verify-ca` | SSL + verify CA certificate | High security |
| `verify-full` | SSL + verify CA and hostname | Maximum security |

## Production Setup (AWS RDS / Cloud)

### AWS RDS PostgreSQL

1. **Download RDS CA certificate**:
   ```bash
   wget https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem
   ```

2. **Update `.env`**:
   ```env
   DB_TYPE=postgresql
   DB_HOST=your-instance.xxx.rds.amazonaws.com
   DB_PORT=5432
   DB_SSL_MODE=verify-full
   DB_SSL_ROOT_CERT=/path/to/global-bundle.pem
   ```

3. **Connect**:
   ```bash
   python -c "from billing_app.database import get_connection; c = get_connection(); print('Connected!')"
   ```

### DigitalOcean / Linode Managed Database

Most managed database providers provide a connection string with SSL already enabled. Example:

```env
# Connection string from provider dashboard
DB_TYPE=postgresql
DB_HOST=db-xxx-do-user-xxx.a.db.ondigitalocean.com
DB_PORT=25060
DB_NAME=billing_app
DB_USER=doadmin
DB_PASSWORD=xxxxx
DB_SSL_MODE=require
```

## Certificate Management

### Renew Self-Signed Certificate

```bash
# Backup old certificate
cp ~/.postgresql/server.crt ~/.postgresql/server.crt.old

# Generate new certificate (before expiry)
openssl req -x509 -newkey rsa:4096 -keyout ~/.postgresql/server.key \
  -out ~/.postgresql/server.crt -days 3650 -nodes \
  -subj "/C=AO/ST=Luanda/L=Luanda/O=YourCompany/CN=your-domain"

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Use Let's Encrypt (Production)

1. **Obtain certificate**:
   ```bash
   sudo certbot certonly --standalone -d your-domain.com
   ```

2. **Configure PostgreSQL**:
   ```ini
   ssl_cert_file = '/etc/letsencrypt/live/your-domain.com/fullchain.pem'
   ssl_key_file = '/etc/letsencrypt/live/your-domain.com/privkey.pem'
   ```

3. **Auto-renew with cron**:
   ```bash
   # Add to crontab
   0 3 * * * certbot renew --quiet && systemctl restart postgresql
   ```

## Monitoring & Verification

### Test SSL Connection

```bash
# Using psql
psql -h localhost -U postgres -d billing_app --set=sslmode=require

# Check SSL status
SELECT version();
SHOW ssl;

# Verify certificate
openssl x509 -in ~/.postgresql/server.crt -text -noout
```

### Monitor SSL Usage (PostgreSQL)

```sql
-- Check active SSL connections
SELECT 
    datname,
    usename,
    application_name,
    ssl,
    ssl_version,
    ssl_cipher
FROM pg_stat_ssl
WHERE ssl = true;
```

## Troubleshooting

### "SSL not supported" Error

**Problem**: Connection refuses SSL
```
SSL error: SSL not supported
```

**Solution**: Verify PostgreSQL compiled with SSL support
```bash
postgres -V
pg_config --version
# Should show "with OpenSSL"
```

### "Certificate verify failed"

**Problem**: `verify-full` mode rejects certificate
```
SSL: CERTIFICATE_VERIFY_FAILED
```

**Solution**:
1. Verify hostname matches certificate CN
2. Check certificate expiry: `openssl x509 -in cert.pem -noout -dates`
3. Use `verify-ca` instead if CN mismatch is expected
4. Update CA bundle: `wget https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem`

### Connection Timeout with SSL

**Problem**: SSL handshake times out
```
SSL: SSL3_GET_RECORD:unexpected EOF
```

**Solution**:
1. Check firewall allows port 5432
2. Verify `ssl = on` in `postgresql.conf`
3. Check PostgreSQL logs: `sudo tail -f /var/log/postgresql/postgresql.log`
4. Try `sslmode=allow` to debug

## Performance Considerations

- **SSL overhead**: ~5-10% latency increase (acceptable for most apps)
- **CPU usage**: Hardware SSL acceleration (AES-NI) reduces CPU impact
- **Connection pooling**: Use PgBouncer to reduce SSL handshake overhead

```bash
# Example: pgbouncer config
[databases]
billing_app = host=localhost port=5432 dbname=billing_app

[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
```

## Compliance & Security

- **PCI DSS**: Requires SSL for database connections ✅
- **GDPR**: Transport encryption mandatory ✅
- **SOC 2**: Verifying certificates recommended ✅

For compliance audits, verify:
```bash
# Certificate validity
openssl x509 -in server.crt -noout -dates

# Encryption strength
openssl s_client -connect localhost:5432 -showcerts | grep Cipher

# TLS version
openssl s_client -connect localhost:5432 -tls1_2
```

## References

- [PostgreSQL SSL Documentation](https://www.postgresql.org/docs/current/ssl-tcp.html)
- [psycopg2 SSL Support](https://www.psycopg.org/psycopg2/docs/module.html#connection-factory)
- [OWASP: Transport Layer Protection](https://owasp.org/www-project-cheat-sheets/cheatsheets/Transport_Layer_Protection_Cheat_Sheet)
