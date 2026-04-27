-- PostgreSQL schema for billing app
CREATE TABLE IF NOT EXISTS customers (
    customer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_code VARCHAR(30) NOT NULL UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    tax_number VARCHAR(30),
    phone VARCHAR(30),
    email VARCHAR(120),
    address_line VARCHAR(255),
    city VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_customers_full_name_not_blank CHECK (TRIM(full_name) <> ''),
    CONSTRAINT chk_customers_email_format CHECK (
        email IS NULL OR POSITION('@' IN email) > 1
    )
);

CREATE TABLE IF NOT EXISTS product_categories (
    category_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category_code VARCHAR(30) NOT NULL UNIQUE,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_product_categories_name_not_blank CHECK (TRIM(category_name) <> '')
);

CREATE TABLE IF NOT EXISTS products (
    product_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_code VARCHAR(30) NOT NULL UNIQUE,
    barcode VARCHAR(50) UNIQUE,
    category_id BIGINT REFERENCES product_categories(category_id),
    product_name VARCHAR(150) NOT NULL,
    description VARCHAR(255),
    unit VARCHAR(20) NOT NULL DEFAULT 'UN',
    cost_price NUMERIC(18, 2) NOT NULL DEFAULT 0,
    sale_price NUMERIC(18, 2) NOT NULL,
    stock_quantity NUMERIC(18, 3) NOT NULL DEFAULT 0,
    minimum_stock NUMERIC(18, 3) NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_products_name_not_blank CHECK (TRIM(product_name) <> ''),
    CONSTRAINT chk_products_cost_price_non_negative CHECK (cost_price >= 0),
    CONSTRAINT chk_products_sale_price_non_negative CHECK (sale_price >= 0),
    CONSTRAINT chk_products_stock_quantity_non_negative CHECK (stock_quantity >= 0),
    CONSTRAINT chk_products_minimum_stock_non_negative CHECK (minimum_stock >= 0)
);

CREATE TABLE IF NOT EXISTS invoices (
    invoice_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    invoice_number VARCHAR(30) NOT NULL UNIQUE,
    customer_id BIGINT REFERENCES customers(customer_id),
    issue_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    notes TEXT,
    subtotal NUMERIC(18, 2) NOT NULL DEFAULT 0,
    discount_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
    tax_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
    total_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_invoices_status CHECK (status IN ('OPEN', 'PAID', 'CANCELLED')),
    CONSTRAINT chk_invoices_subtotal_non_negative CHECK (subtotal >= 0),
    CONSTRAINT chk_invoices_discount_non_negative CHECK (discount_amount >= 0),
    CONSTRAINT chk_invoices_tax_non_negative CHECK (tax_amount >= 0),
    CONSTRAINT chk_invoices_total_non_negative CHECK (total_amount >= 0),
    CONSTRAINT chk_invoices_total_logic CHECK (
        total_amount = subtotal - discount_amount + tax_amount
    )
);

CREATE TABLE IF NOT EXISTS invoice_items (
    invoice_item_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    invoice_id BIGINT NOT NULL REFERENCES invoices(invoice_id) ON DELETE CASCADE,
    product_id BIGINT NOT NULL REFERENCES products(product_id),
    line_number INTEGER NOT NULL,
    quantity NUMERIC(18, 3) NOT NULL,
    unit_price NUMERIC(18, 2) NOT NULL,
    discount_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
    line_total NUMERIC(18, 2) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_invoice_items_line UNIQUE (invoice_id, line_number),
    CONSTRAINT chk_invoice_items_quantity_positive CHECK (quantity > 0),
    CONSTRAINT chk_invoice_items_unit_price_non_negative CHECK (unit_price >= 0),
    CONSTRAINT chk_invoice_items_discount_non_negative CHECK (discount_amount >= 0),
    CONSTRAINT chk_invoice_items_line_total_non_negative CHECK (line_total >= 0),
    CONSTRAINT chk_invoice_items_total_logic CHECK (
        line_total = (quantity * unit_price) - discount_amount
    )
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    invoice_id BIGINT NOT NULL REFERENCES invoices(invoice_id) ON DELETE CASCADE,
    payment_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    payment_method VARCHAR(20) NOT NULL,
    amount NUMERIC(18, 2) NOT NULL,
    reference_number VARCHAR(50),
    notes VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_payments_method CHECK (
        payment_method IN ('CASH', 'CARD', 'TRANSFER', 'MOBILE', 'OTHER')
    ),
    CONSTRAINT chk_payments_amount_positive CHECK (amount > 0)
);

CREATE TABLE IF NOT EXISTS app_users (
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

CREATE TABLE IF NOT EXISTS app_sessions (
    session_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES app_users(user_id) ON DELETE CASCADE,
    session_token VARCHAR(255) NOT NULL UNIQUE,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS suppliers (
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

CREATE TABLE IF NOT EXISTS stock_entries (
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

CREATE TABLE IF NOT EXISTS stock_entry_items (
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

CREATE TABLE IF NOT EXISTS stock_movements (
    stock_movement_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(product_id),
    invoice_id BIGINT REFERENCES invoices(invoice_id),
    stock_entry_id BIGINT REFERENCES stock_entries(stock_entry_id),
    movement_type VARCHAR(20) NOT NULL,
    quantity_delta NUMERIC(18, 3) NOT NULL,
    balance_after NUMERIC(18, 3) NOT NULL CHECK (balance_after >= 0),
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_stock_movements_type CHECK (
        movement_type IN ('INITIAL', 'SALE', 'CANCEL_RETURN', 'ADJUSTMENT', 'PURCHASE')
    )
);

CREATE TABLE IF NOT EXISTS cash_sessions (
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

CREATE TABLE IF NOT EXISTS cash_movements (
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

CREATE TABLE IF NOT EXISTS audit_logs (
    audit_log_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT REFERENCES app_users(user_id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(100),
    details TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS business_settings (
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

-- Views
CREATE OR REPLACE VIEW invoice_financials AS
SELECT
    i.invoice_id,
    COALESCE(SUM(p.amount), 0) AS paid_amount,
    i.total_amount - COALESCE(SUM(p.amount), 0) AS balance_due
FROM invoices i
LEFT JOIN payments p ON p.invoice_id = i.invoice_id
GROUP BY i.invoice_id, i.total_amount;

-- Indices
CREATE INDEX IF NOT EXISTS idx_products_category_id ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_invoices_customer_id ON invoices(customer_id);
CREATE INDEX IF NOT EXISTS idx_invoices_issue_date ON invoices(issue_date);
CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice_id ON invoice_items(invoice_id);
CREATE INDEX IF NOT EXISTS idx_invoice_items_product_id ON invoice_items(product_id);
CREATE INDEX IF NOT EXISTS idx_payments_invoice_id ON payments(invoice_id);
CREATE INDEX IF NOT EXISTS idx_payments_payment_date ON payments(payment_date);
CREATE INDEX IF NOT EXISTS idx_app_sessions_token ON app_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_app_sessions_user_id ON app_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_stock_entries_supplier_id ON stock_entries(supplier_id);
CREATE INDEX IF NOT EXISTS idx_stock_entry_items_entry_id ON stock_entry_items(stock_entry_id);
CREATE INDEX IF NOT EXISTS idx_stock_movements_product_id ON stock_movements(product_id);
CREATE INDEX IF NOT EXISTS idx_stock_movements_invoice_id ON stock_movements(invoice_id);
CREATE INDEX IF NOT EXISTS idx_stock_movements_stock_entry_id ON stock_movements(stock_entry_id);
CREATE INDEX IF NOT EXISTS idx_cash_movements_session_id ON cash_movements(cash_session_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
