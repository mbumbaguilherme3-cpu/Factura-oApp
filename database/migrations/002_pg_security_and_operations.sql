-- PostgreSQL Migration: 002_security_and_operations
CREATE TABLE app_users (
    user_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'CASHIER',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_app_users_role CHECK (role IN ('ADMIN', 'MANAGER', 'CASHIER', 'STOCK'))
);

CREATE TABLE app_sessions (
    session_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES app_users(user_id) ON DELETE CASCADE,
    session_token VARCHAR(255) NOT NULL UNIQUE,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

CREATE TABLE suppliers (
    supplier_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    supplier_code VARCHAR(30) NOT NULL UNIQUE,
    supplier_name VARCHAR(150) NOT NULL,
    tax_number VARCHAR(30),
    phone VARCHAR(30),
    email VARCHAR(120),
    address_line VARCHAR(255),
    city VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_suppliers_name_not_blank CHECK (TRIM(supplier_name) <> '')
);

CREATE TABLE stock_entries (
    stock_entry_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entry_number VARCHAR(30) NOT NULL UNIQUE,
    supplier_id BIGINT REFERENCES suppliers(supplier_id),
    received_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    total_cost NUMERIC(18, 2) NOT NULL DEFAULT 0 CHECK (total_cost >= 0),
    created_by_user_id BIGINT REFERENCES app_users(user_id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE stock_entry_items (
    stock_entry_item_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    stock_entry_id BIGINT NOT NULL REFERENCES stock_entries(stock_entry_id) ON DELETE CASCADE,
    product_id BIGINT NOT NULL REFERENCES products(product_id),
    line_number INTEGER NOT NULL,
    quantity NUMERIC(18, 3) NOT NULL,
    unit_cost NUMERIC(18, 2) NOT NULL,
    line_total NUMERIC(18, 2) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_stock_entry_items_line UNIQUE (stock_entry_id, line_number),
    CONSTRAINT chk_stock_entry_items_quantity_positive CHECK (quantity > 0),
    CONSTRAINT chk_stock_entry_items_unit_cost_non_negative CHECK (unit_cost >= 0),
    CONSTRAINT chk_stock_entry_items_line_total_non_negative CHECK (line_total >= 0)
);

CREATE TABLE cash_sessions (
    cash_session_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_number VARCHAR(30) NOT NULL UNIQUE,
    status VARCHAR(10) NOT NULL DEFAULT 'OPEN',
    opening_amount NUMERIC(18, 2) NOT NULL DEFAULT 0 CHECK (opening_amount >= 0),
    expected_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
    counted_amount NUMERIC(18, 2),
    difference_amount NUMERIC(18, 2),
    notes TEXT,
    opened_by_user_id BIGINT NOT NULL REFERENCES app_users(user_id),
    closed_by_user_id BIGINT REFERENCES app_users(user_id),
    opened_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    CONSTRAINT chk_cash_sessions_status CHECK (status IN ('OPEN', 'CLOSED'))
);

CREATE TABLE cash_movements (
    cash_movement_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cash_session_id BIGINT NOT NULL REFERENCES cash_sessions(cash_session_id) ON DELETE CASCADE,
    movement_type VARCHAR(20) NOT NULL,
    amount_delta NUMERIC(18, 2) NOT NULL,
    payment_id BIGINT REFERENCES payments(payment_id),
    invoice_id BIGINT REFERENCES invoices(invoice_id),
    notes TEXT,
    created_by_user_id BIGINT REFERENCES app_users(user_id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_cash_movements_type CHECK (
        movement_type IN ('OPENING', 'SALE_PAYMENT', 'MANUAL_IN', 'MANUAL_OUT', 'CLOSING')
    )
);

CREATE TABLE audit_logs (
    audit_log_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT REFERENCES app_users(user_id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(100),
    details TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE business_settings (
    settings_id INTEGER PRIMARY KEY CHECK (settings_id = 1),
    company_name VARCHAR(150) NOT NULL DEFAULT 'Minha Loja',
    tax_id VARCHAR(50),
    company_address VARCHAR(255),
    company_phone VARCHAR(30),
    company_email VARCHAR(120),
    currency_code VARCHAR(3) NOT NULL DEFAULT 'AOA',
    currency_symbol VARCHAR(5) NOT NULL DEFAULT 'Kz',
    tax_label VARCHAR(20) NOT NULL DEFAULT 'IVA',
    default_tax_rate NUMERIC(5, 2) NOT NULL DEFAULT 0,
    invoice_prefix VARCHAR(10) NOT NULL DEFAULT 'INV',
    receipt_footer TEXT,
    legal_notice TEXT,
    require_customer_tax_number BOOLEAN NOT NULL DEFAULT FALSE
);

INSERT INTO business_settings (
    settings_id,
    company_name,
    currency_code,
    currency_symbol,
    tax_label,
    default_tax_rate,
    invoice_prefix
)
VALUES (1, 'Minha Loja', 'AOA', 'Kz', 'IVA', 0, 'INV')
ON CONFLICT DO NOTHING;

CREATE INDEX idx_app_sessions_token ON app_sessions(session_token);
CREATE INDEX idx_stock_entries_supplier_id ON stock_entries(supplier_id);
CREATE INDEX idx_stock_entry_items_entry_id ON stock_entry_items(stock_entry_id);
CREATE INDEX idx_cash_movements_session_id ON cash_movements(cash_session_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
