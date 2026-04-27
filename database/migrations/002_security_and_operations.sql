PRAGMA foreign_keys = OFF;

ALTER TABLE stock_movements RENAME TO stock_movements_old;

CREATE TABLE stock_movements (
    stock_movement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    invoice_id INTEGER,
    stock_entry_id INTEGER,
    movement_type TEXT NOT NULL CHECK (
        movement_type IN ('INITIAL', 'SALE', 'CANCEL_RETURN', 'ADJUSTMENT', 'PURCHASE')
    ),
    quantity_delta NUMERIC NOT NULL,
    balance_after NUMERIC NOT NULL CHECK (balance_after >= 0),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id)
);

INSERT INTO stock_movements (
    stock_movement_id,
    product_id,
    invoice_id,
    movement_type,
    quantity_delta,
    balance_after,
    notes,
    created_at
)
SELECT
    stock_movement_id,
    product_id,
    invoice_id,
    movement_type,
    quantity_delta,
    balance_after,
    notes,
    created_at
FROM stock_movements_old;

DROP TABLE stock_movements_old;

CREATE TABLE IF NOT EXISTS app_users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('ADMIN', 'MANAGER', 'CASHIER', 'STOCK')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    last_login_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_token TEXT NOT NULL UNIQUE,
    ip_address TEXT,
    user_agent TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES app_users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_code TEXT NOT NULL UNIQUE,
    supplier_name TEXT NOT NULL,
    tax_number TEXT,
    phone TEXT,
    email TEXT,
    address_line TEXT,
    city TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (trim(supplier_name) <> '')
);

CREATE TABLE IF NOT EXISTS stock_entries (
    stock_entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_number TEXT NOT NULL UNIQUE,
    supplier_id INTEGER,
    received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    total_cost NUMERIC NOT NULL DEFAULT 0 CHECK (total_cost >= 0),
    created_by_user_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id),
    FOREIGN KEY (created_by_user_id) REFERENCES app_users(user_id)
);

CREATE TABLE IF NOT EXISTS stock_entry_items (
    stock_entry_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_entry_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    line_number INTEGER NOT NULL,
    quantity NUMERIC NOT NULL CHECK (quantity > 0),
    unit_cost NUMERIC NOT NULL CHECK (unit_cost >= 0),
    line_total NUMERIC NOT NULL CHECK (line_total >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (stock_entry_id, line_number),
    FOREIGN KEY (stock_entry_id) REFERENCES stock_entries(stock_entry_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS cash_sessions (
    cash_session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_number TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'CLOSED')),
    opening_amount NUMERIC NOT NULL DEFAULT 0 CHECK (opening_amount >= 0),
    expected_amount NUMERIC NOT NULL DEFAULT 0,
    counted_amount NUMERIC,
    difference_amount NUMERIC,
    notes TEXT,
    opened_by_user_id INTEGER NOT NULL,
    closed_by_user_id INTEGER,
    opened_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at TEXT,
    FOREIGN KEY (opened_by_user_id) REFERENCES app_users(user_id),
    FOREIGN KEY (closed_by_user_id) REFERENCES app_users(user_id)
);

CREATE TABLE IF NOT EXISTS cash_movements (
    cash_movement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cash_session_id INTEGER NOT NULL,
    movement_type TEXT NOT NULL CHECK (
        movement_type IN ('OPENING', 'SALE_PAYMENT', 'MANUAL_IN', 'MANUAL_OUT', 'CLOSING')
    ),
    amount_delta NUMERIC NOT NULL,
    payment_id INTEGER,
    invoice_id INTEGER,
    notes TEXT,
    created_by_user_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cash_session_id) REFERENCES cash_sessions(cash_session_id) ON DELETE CASCADE,
    FOREIGN KEY (payment_id) REFERENCES payments(payment_id),
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id),
    FOREIGN KEY (created_by_user_id) REFERENCES app_users(user_id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    audit_log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    details TEXT,
    ip_address TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES app_users(user_id)
);

CREATE TABLE IF NOT EXISTS business_settings (
    settings_id INTEGER PRIMARY KEY CHECK (settings_id = 1),
    company_name TEXT NOT NULL DEFAULT 'Minha Loja',
    tax_id TEXT,
    company_address TEXT,
    company_phone TEXT,
    company_email TEXT,
    currency_code TEXT NOT NULL DEFAULT 'AOA',
    currency_symbol TEXT NOT NULL DEFAULT 'Kz',
    tax_label TEXT NOT NULL DEFAULT 'IVA',
    default_tax_rate NUMERIC NOT NULL DEFAULT 0,
    invoice_prefix TEXT NOT NULL DEFAULT 'INV',
    receipt_footer TEXT,
    legal_notice TEXT,
    require_customer_tax_number INTEGER NOT NULL DEFAULT 0 CHECK (require_customer_tax_number IN (0, 1))
);

INSERT OR IGNORE INTO business_settings (
    settings_id,
    company_name,
    currency_code,
    currency_symbol,
    tax_label,
    default_tax_rate,
    invoice_prefix
)
VALUES (1, 'Minha Loja', 'AOA', 'Kz', 'IVA', 0, 'INV');

CREATE INDEX IF NOT EXISTS idx_app_sessions_token ON app_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_stock_entries_supplier_id ON stock_entries(supplier_id);
CREATE INDEX IF NOT EXISTS idx_stock_entry_items_entry_id ON stock_entry_items(stock_entry_id);
CREATE INDEX IF NOT EXISTS idx_cash_movements_session_id ON cash_movements(cash_session_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_stock_movements_stock_entry_id ON stock_movements(stock_entry_id);

PRAGMA foreign_keys = ON;
