PRAGMA foreign_keys = OFF;

ALTER TABLE stock_movements RENAME TO stock_movements_old_v2;

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
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id),
    FOREIGN KEY (stock_entry_id) REFERENCES stock_entries(stock_entry_id)
);

INSERT INTO stock_movements (
    stock_movement_id,
    product_id,
    invoice_id,
    stock_entry_id,
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
    stock_entry_id,
    movement_type,
    quantity_delta,
    balance_after,
    notes,
    created_at
FROM stock_movements_old_v2;

DROP TABLE stock_movements_old_v2;

CREATE INDEX IF NOT EXISTS idx_stock_movements_product_id ON stock_movements(product_id);
CREATE INDEX IF NOT EXISTS idx_stock_movements_invoice_id ON stock_movements(invoice_id);
CREATE INDEX IF NOT EXISTS idx_stock_movements_stock_entry_id ON stock_movements(stock_entry_id);

PRAGMA foreign_keys = ON;
