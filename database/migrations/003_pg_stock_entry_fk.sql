-- PostgreSQL Migration: 003_stock_entry_fk
ALTER TABLE stock_movements
ADD CONSTRAINT fk_stock_movements_stock_entry_id
FOREIGN KEY (stock_entry_id)
REFERENCES stock_entries(stock_entry_id);

CREATE INDEX idx_stock_movements_stock_entry_id ON stock_movements(stock_entry_id);
