INSERT INTO customers (
    customer_code,
    full_name,
    phone,
    city
)
VALUES
    ('CUST-00001', 'Consumidor Final', '+244 900 000 000', 'Luanda'),
    ('CUST-00002', 'Empresa Horizonte', '+244 923 111 222', 'Luanda');

INSERT INTO product_categories (
    category_code,
    category_name,
    description
)
VALUES
    ('CAT-00001', 'Bebidas', 'Sumos, refrigerantes e aguas.'),
    ('CAT-00002', 'Mercearia', 'Produtos secos e alimentos de prateleira.'),
    ('CAT-00003', 'Higiene', 'Itens de limpeza e uso diario.');

INSERT INTO products (
    product_code,
    category_id,
    product_name,
    unit,
    cost_price,
    sale_price,
    stock_quantity,
    minimum_stock
)
VALUES
    ('PROD-00001', 1, 'Agua Mineral 1.5L', 'UN', 180.00, 250.00, 48.000, 10.000),
    ('PROD-00002', 1, 'Refrigerante Cola 2L', 'UN', 420.00, 600.00, 36.000, 8.000),
    ('PROD-00003', 2, 'Arroz 25Kg', 'SC', 14800.00, 16500.00, 12.000, 4.000),
    ('PROD-00004', 3, 'Detergente 500ml', 'UN', 380.00, 550.00, 20.000, 6.000);

INSERT INTO stock_movements (
    product_id,
    movement_type,
    quantity_delta,
    balance_after,
    notes
)
VALUES
    (1, 'INITIAL', 48.000, 48.000, 'Carga inicial da base.'),
    (2, 'INITIAL', 36.000, 36.000, 'Carga inicial da base.'),
    (3, 'INITIAL', 12.000, 12.000, 'Carga inicial da base.'),
    (4, 'INITIAL', 20.000, 20.000, 'Carga inicial da base.');
