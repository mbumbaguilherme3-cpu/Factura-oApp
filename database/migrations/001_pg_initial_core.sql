-- PostgreSQL Migration: 001_initial_core
CREATE TABLE customers (
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

CREATE TABLE product_categories (
    category_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category_code VARCHAR(30) NOT NULL UNIQUE,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_product_categories_name_not_blank CHECK (TRIM(category_name) <> '')
);

CREATE TABLE products (
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

CREATE TABLE invoices (
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

CREATE TABLE invoice_items (
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

CREATE TABLE payments (
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

CREATE TABLE stock_movements (
    stock_movement_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(product_id),
    invoice_id BIGINT REFERENCES invoices(invoice_id),
    stock_entry_id BIGINT,
    movement_type VARCHAR(20) NOT NULL,
    quantity_delta NUMERIC(18, 3) NOT NULL,
    balance_after NUMERIC(18, 3) NOT NULL CHECK (balance_after >= 0),
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_stock_movements_type CHECK (
        movement_type IN ('INITIAL', 'SALE', 'CANCEL_RETURN', 'ADJUSTMENT', 'PURCHASE')
    )
);

CREATE VIEW invoice_financials AS
SELECT
    i.invoice_id,
    COALESCE(SUM(p.amount), 0) AS paid_amount,
    i.total_amount - COALESCE(SUM(p.amount), 0) AS balance_due
FROM invoices i
LEFT JOIN payments p ON p.invoice_id = i.invoice_id
GROUP BY i.invoice_id, i.total_amount;

CREATE INDEX idx_products_category_id ON products(category_id);
CREATE INDEX idx_invoices_customer_id ON invoices(customer_id);
CREATE INDEX idx_invoices_issue_date ON invoices(issue_date);
CREATE INDEX idx_invoice_items_invoice_id ON invoice_items(invoice_id);
CREATE INDEX idx_invoice_items_product_id ON invoice_items(product_id);
CREATE INDEX idx_payments_invoice_id ON payments(invoice_id);
CREATE INDEX idx_stock_movements_product_id ON stock_movements(product_id);
CREATE INDEX idx_stock_movements_invoice_id ON stock_movements(invoice_id);
