from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime
import sqlite3


TWOPLACES = Decimal("0.01")
THREEPLACES = Decimal("0.001")


class ValidationError(Exception):
    """Erro de validacao de regra de negocio."""


def parse_money(value: str | int | float | Decimal | None) -> Decimal:
    return _parse_decimal(value, TWOPLACES, "valor monetario")


def parse_quantity(value: str | int | float | Decimal | None) -> Decimal:
    return _parse_decimal(value, THREEPLACES, "quantidade")


def money_to_db(value: Decimal) -> str:
    return str(value.quantize(TWOPLACES, rounding=ROUND_HALF_UP))


def quantity_to_db(value: Decimal) -> str:
    return str(value.quantize(THREEPLACES, rounding=ROUND_HALF_UP))


def money_from_db(value: object) -> Decimal:
    return Decimal(str(value or 0)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def quantity_from_db(value: object) -> Decimal:
    return Decimal(str(value or 0)).quantize(THREEPLACES, rounding=ROUND_HALF_UP)


def _parse_decimal(
    value: str | int | float | Decimal | None,
    precision: Decimal,
    label: str,
) -> Decimal:
    normalized = "0" if value in (None, "") else str(value).strip().replace(",", ".")

    try:
        decimal_value = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValidationError(f"O campo {label} precisa ser numerico.") from exc

    return decimal_value.quantize(precision, rounding=ROUND_HALF_UP)


def format_money(value: object) -> str:
    amount = money_from_db(value)
    text = f"{amount:,.2f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def format_quantity(value: object) -> str:
    amount = quantity_from_db(value)
    text = f"{amount:,.3f}"
    text = text.replace(",", "X").replace(".", ",").replace("X", ".")
    return text.rstrip("0").rstrip(",")


def create_customer(connection: sqlite3.Connection, form: dict[str, str]) -> int:
    full_name = form.get("full_name", "").strip()
    if not full_name:
        raise ValidationError("Informe o nome do cliente.")

    email = form.get("email", "").strip()
    if email and "@" not in email:
        raise ValidationError("O email do cliente parece invalido.")

    customer_code = _generate_code(connection, "customers", "customer_code", "CUST")
    cursor = connection.execute(
        """
        INSERT INTO customers (
            customer_code,
            full_name,
            tax_number,
            phone,
            email,
            address_line,
            city
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            customer_code,
            full_name,
            form.get("tax_number", "").strip() or None,
            form.get("phone", "").strip() or None,
            email or None,
            form.get("address_line", "").strip() or None,
            form.get("city", "").strip() or None,
        ),
    )
    return int(cursor.lastrowid)


def get_customer(connection: sqlite3.Connection, customer_id: int) -> dict[str, object] | None:
    row = connection.execute(
        """
        SELECT
            customer_id,
            customer_code,
            full_name,
            tax_number,
            phone,
            email,
            address_line,
            city,
            is_active
        FROM customers
        WHERE customer_id = ?
        """,
        (customer_id,),
    ).fetchone()
    return dict(row) if row else None


def update_customer(connection: sqlite3.Connection, customer_id: int, form: dict[str, str]) -> None:
    customer = get_customer(connection, customer_id)
    if customer is None:
        raise ValidationError("Cliente nao encontrado.")

    full_name = form.get("full_name", "").strip()
    if not full_name:
        raise ValidationError("Informe o nome do cliente.")

    email = form.get("email", "").strip()
    if email and "@" not in email:
        raise ValidationError("O email do cliente parece invalido.")

    connection.execute(
        """
        UPDATE customers
        SET full_name = ?,
            tax_number = ?,
            phone = ?,
            email = ?,
            address_line = ?,
            city = ?,
            is_active = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE customer_id = ?
        """,
        (
            full_name,
            form.get("tax_number", "").strip() or None,
            form.get("phone", "").strip() or None,
            email or None,
            form.get("address_line", "").strip() or None,
            form.get("city", "").strip() or None,
            1 if form.get("is_active", "1") not in {"0", "false", "False", ""} else 0,
            customer_id,
        ),
    )


def create_category(connection: sqlite3.Connection, form: dict[str, str]) -> int:
    category_name = form.get("category_name", "").strip()
    if not category_name:
        raise ValidationError("Informe o nome da categoria.")

    category_code = _generate_code(
        connection,
        "product_categories",
        "category_code",
        "CAT",
    )
    cursor = connection.execute(
        """
        INSERT INTO product_categories (
            category_code,
            category_name,
            description
        )
        VALUES (?, ?, ?)
        """,
        (
            category_code,
            category_name,
            form.get("description", "").strip() or None,
        ),
    )
    return int(cursor.lastrowid)


def create_product(connection: sqlite3.Connection, form: dict[str, str]) -> int:
    product_name = form.get("product_name", "").strip()
    if not product_name:
        raise ValidationError("Informe o nome do produto.")

    sale_price = parse_money(form.get("sale_price"))
    cost_price = parse_money(form.get("cost_price"))
    stock_quantity = parse_quantity(form.get("stock_quantity"))
    minimum_stock = parse_quantity(form.get("minimum_stock"))

    if sale_price < 0 or cost_price < 0:
        raise ValidationError("Os precos nao podem ser negativos.")

    if stock_quantity < 0 or minimum_stock < 0:
        raise ValidationError("O estoque nao pode ser negativo.")

    category_id = _parse_optional_int(form.get("category_id"))
    product_code = _generate_code(connection, "products", "product_code", "PROD")
    cursor = connection.execute(
        """
        INSERT INTO products (
            product_code,
            barcode,
            category_id,
            product_name,
            description,
            unit,
            cost_price,
            sale_price,
            stock_quantity,
            minimum_stock
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            product_code,
            form.get("barcode", "").strip() or None,
            category_id,
            product_name,
            form.get("description", "").strip() or None,
            form.get("unit", "").strip().upper() or "UN",
            money_to_db(cost_price),
            money_to_db(sale_price),
            quantity_to_db(stock_quantity),
            quantity_to_db(minimum_stock),
        ),
    )
    product_id = int(cursor.lastrowid)

    if stock_quantity > 0:
        connection.execute(
            """
            INSERT INTO stock_movements (
                product_id,
                movement_type,
                quantity_delta,
                balance_after,
                notes
            )
            VALUES (?, 'INITIAL', ?, ?, ?)
            """,
            (
                product_id,
                quantity_to_db(stock_quantity),
                quantity_to_db(stock_quantity),
                "Saldo inicial do produto.",
            ),
        )

    return product_id


def get_product(connection: sqlite3.Connection, product_id: int) -> dict[str, object] | None:
    row = connection.execute(
        """
        SELECT
            product_id,
            product_code,
            barcode,
            category_id,
            product_name,
            description,
            unit,
            cost_price,
            sale_price,
            stock_quantity,
            minimum_stock,
            is_active
        FROM products
        WHERE product_id = ?
        """,
        (product_id,),
    ).fetchone()
    return dict(row) if row else None


def update_product(connection: sqlite3.Connection, product_id: int, form: dict[str, str]) -> None:
    product = get_product(connection, product_id)
    if product is None:
        raise ValidationError("Produto nao encontrado.")

    product_name = form.get("product_name", "").strip()
    if not product_name:
        raise ValidationError("Informe o nome do produto.")

    sale_price = parse_money(form.get("sale_price"))
    cost_price = parse_money(form.get("cost_price"))
    minimum_stock = parse_quantity(form.get("minimum_stock"))

    if sale_price < 0 or cost_price < 0:
        raise ValidationError("Os precos nao podem ser negativos.")
    if minimum_stock < 0:
        raise ValidationError("O estoque minimo nao pode ser negativo.")

    connection.execute(
        """
        UPDATE products
        SET barcode = ?,
            category_id = ?,
            product_name = ?,
            description = ?,
            unit = ?,
            cost_price = ?,
            sale_price = ?,
            minimum_stock = ?,
            is_active = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE product_id = ?
        """,
        (
            form.get("barcode", "").strip() or None,
            _parse_optional_int(form.get("category_id")),
            product_name,
            form.get("description", "").strip() or None,
            form.get("unit", "").strip().upper() or "UN",
            money_to_db(cost_price),
            money_to_db(sale_price),
            quantity_to_db(minimum_stock),
            1 if form.get("is_active", "1") not in {"0", "false", "False", ""} else 0,
            product_id,
        ),
    )


def list_customers(connection: sqlite3.Connection) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT
            customer_id,
            customer_code,
            full_name,
            tax_number,
            phone,
            email,
            city,
            is_active
        FROM customers
        ORDER BY full_name
        """
    ).fetchall()
    return [dict(row) for row in rows]


def list_categories(connection: sqlite3.Connection) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT
            category_id,
            category_code,
            category_name,
            description,
            is_active
        FROM product_categories
        ORDER BY category_name
        """
    ).fetchall()
    return [dict(row) for row in rows]


def list_products(connection: sqlite3.Connection) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT
            p.product_id,
            p.product_code,
            p.barcode,
            p.product_name,
            p.unit,
            p.cost_price,
            p.sale_price,
            p.stock_quantity,
            p.minimum_stock,
            p.is_active,
            c.category_name
        FROM products p
        LEFT JOIN product_categories c ON c.category_id = p.category_id
        ORDER BY p.product_name
        """
    ).fetchall()

    products: list[dict[str, object]] = []
    for row in rows:
        product = dict(row)
        product["stock_alert"] = quantity_from_db(product["stock_quantity"]) <= quantity_from_db(
            product["minimum_stock"]
        )
        products.append(product)
    return products


def list_invoice_customers(connection: sqlite3.Connection) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT customer_id, full_name
        FROM customers
        WHERE is_active = 1
        ORDER BY full_name
        """
    ).fetchall()
    return [dict(row) for row in rows]


def list_invoice_products(connection: sqlite3.Connection) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT
            product_id,
            product_name,
            sale_price,
            stock_quantity,
            unit
        FROM products
        WHERE is_active = 1
        ORDER BY product_name
        """
    ).fetchall()
    return [dict(row) for row in rows]


def dashboard_snapshot(connection: sqlite3.Connection) -> dict[str, object]:
    metrics = connection.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM customers WHERE is_active = 1) AS customer_count,
            (SELECT COUNT(*) FROM products WHERE is_active = 1) AS product_count,
            (SELECT COUNT(*) FROM invoices) AS invoice_count,
            (
                SELECT COALESCE(SUM(total_amount), 0)
                FROM invoices
                WHERE date(issue_date) = date('now')
                  AND status <> 'CANCELLED'
            ) AS today_sales,
            (
                SELECT COALESCE(SUM(f.balance_due), 0)
                FROM invoice_financials f
                JOIN invoices i ON i.invoice_id = f.invoice_id
                WHERE i.status IN ('OPEN', 'PARTIAL')
            ) AS receivables
        """
    ).fetchone()

    low_stock_rows = connection.execute(
        """
        SELECT
            product_id,
            product_name,
            stock_quantity,
            minimum_stock,
            unit
        FROM products
        WHERE is_active = 1
          AND stock_quantity <= minimum_stock
        ORDER BY stock_quantity ASC, product_name
        LIMIT 8
        """
    ).fetchall()

    recent_invoice_rows = connection.execute(
        """
        SELECT
            i.invoice_id,
            i.invoice_number,
            COALESCE(c.full_name, 'Consumidor avulso') AS customer_name,
            i.issue_date,
            i.status,
            i.total_amount,
            f.paid_amount,
            f.balance_due
        FROM invoices i
        LEFT JOIN customers c ON c.customer_id = i.customer_id
        LEFT JOIN invoice_financials f ON f.invoice_id = i.invoice_id
        ORDER BY i.invoice_id DESC
        LIMIT 10
        """
    ).fetchall()

    return {
        "metrics": dict(metrics),
        "low_stock": [dict(row) for row in low_stock_rows],
        "recent_invoices": [dict(row) for row in recent_invoice_rows],
    }


def list_invoices(connection: sqlite3.Connection) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT
            i.invoice_id,
            i.invoice_number,
            COALESCE(c.full_name, 'Consumidor avulso') AS customer_name,
            i.issue_date,
            i.status,
            i.total_amount,
            f.paid_amount,
            f.balance_due
        FROM invoices i
        LEFT JOIN customers c ON c.customer_id = i.customer_id
        LEFT JOIN invoice_financials f ON f.invoice_id = i.invoice_id
        ORDER BY i.invoice_id DESC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def get_invoice_detail(connection: sqlite3.Connection, invoice_id: int) -> dict[str, object] | None:
    invoice = connection.execute(
        """
        SELECT
            i.invoice_id,
            i.invoice_number,
            i.issue_date,
            i.status,
            i.notes,
            i.subtotal,
            i.discount_amount,
            i.tax_amount,
            i.total_amount,
            COALESCE(c.full_name, 'Consumidor avulso') AS customer_name,
            c.phone AS customer_phone,
            c.email AS customer_email,
            f.paid_amount,
            f.balance_due
        FROM invoices i
        LEFT JOIN customers c ON c.customer_id = i.customer_id
        LEFT JOIN invoice_financials f ON f.invoice_id = i.invoice_id
        WHERE i.invoice_id = ?
        """,
        (invoice_id,),
    ).fetchone()

    if invoice is None:
        return None

    items = connection.execute(
        """
        SELECT
            ii.line_number,
            p.product_name,
            p.unit,
            ii.quantity,
            ii.unit_price,
            ii.discount_amount,
            ii.line_total
        FROM invoice_items ii
        JOIN products p ON p.product_id = ii.product_id
        WHERE ii.invoice_id = ?
        ORDER BY ii.line_number
        """,
        (invoice_id,),
    ).fetchall()

    payments = connection.execute(
        """
        SELECT
            payment_id,
            payment_date,
            payment_method,
            amount,
            reference_number,
            notes
        FROM payments
        WHERE invoice_id = ?
        ORDER BY payment_id DESC
        """,
        (invoice_id,),
    ).fetchall()

    invoice_data = dict(invoice)
    invoice_data["items"] = [dict(row) for row in items]
    invoice_data["payments"] = [dict(row) for row in payments]
    invoice_data["can_receive_payment"] = (
        invoice_data["status"] != "CANCELLED"
        and money_from_db(invoice_data["balance_due"]) > Decimal("0")
    )
    invoice_data["can_cancel"] = (
        invoice_data["status"] in {"OPEN", "PARTIAL"}
        and money_from_db(invoice_data["paid_amount"]) == Decimal("0")
    )
    return invoice_data


def get_invoice_header(connection: sqlite3.Connection, invoice_id: int) -> dict[str, object] | None:
    row = connection.execute(
        """
        SELECT
            i.invoice_id,
            i.invoice_number,
            i.customer_id,
            i.issue_date,
            i.status,
            i.notes,
            i.subtotal,
            i.discount_amount,
            i.tax_amount,
            i.total_amount,
            COALESCE(f.paid_amount, 0) AS paid_amount,
            COALESCE(f.balance_due, i.total_amount) AS balance_due
        FROM invoices i
        LEFT JOIN invoice_financials f ON f.invoice_id = i.invoice_id
        WHERE i.invoice_id = ?
        """,
        (invoice_id,),
    ).fetchone()
    return dict(row) if row else None


def update_invoice_header(connection: sqlite3.Connection, invoice_id: int, form: dict[str, str]) -> None:
    invoice = get_invoice_header(connection, invoice_id)
    if invoice is None:
        raise ValidationError("Fatura nao encontrada.")
    if invoice["status"] == "CANCELLED":
        raise ValidationError("Nao e permitido editar uma fatura cancelada.")

    discount_amount = parse_money(form.get("discount_amount"))
    tax_amount = parse_money(form.get("tax_amount"))
    subtotal = money_from_db(invoice["subtotal"])
    paid_amount = money_from_db(invoice["paid_amount"])
    total_amount = (subtotal - discount_amount + tax_amount).quantize(TWOPLACES)

    if total_amount < 0:
        raise ValidationError("O total da fatura nao pode ficar negativo.")
    if total_amount < paid_amount:
        raise ValidationError("O total nao pode ficar abaixo do valor ja pago.")

    connection.execute(
        """
        UPDATE invoices
        SET customer_id = ?,
            notes = ?,
            discount_amount = ?,
            tax_amount = ?,
            total_amount = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE invoice_id = ?
        """,
        (
            _parse_optional_int(form.get("customer_id")),
            form.get("notes", "").strip() or None,
            money_to_db(discount_amount),
            money_to_db(tax_amount),
            money_to_db(total_amount),
            invoice_id,
        ),
    )
    _sync_invoice_status(connection, invoice_id)


def list_stock_overview(connection: sqlite3.Connection) -> dict[str, object]:
    products = connection.execute(
        """
        SELECT
            product_id,
            product_name,
            unit,
            stock_quantity,
            minimum_stock,
            sale_price
        FROM products
        ORDER BY product_name
        """
    ).fetchall()

    movements = connection.execute(
        """
        SELECT
            sm.stock_movement_id,
            sm.created_at,
            p.product_name,
            sm.movement_type,
            sm.quantity_delta,
            sm.balance_after,
            i.invoice_number,
            sm.notes
        FROM stock_movements sm
        JOIN products p ON p.product_id = sm.product_id
        LEFT JOIN invoices i ON i.invoice_id = sm.invoice_id
        ORDER BY sm.stock_movement_id DESC
        LIMIT 20
        """
    ).fetchall()

    return {
        "products": [dict(row) for row in products],
        "movements": [dict(row) for row in movements],
    }


def create_invoice(
    connection: sqlite3.Connection,
    form: dict[str, str],
    raw_items: list[dict[str, str]],
) -> int:
    normalized_items = _normalize_invoice_items(connection, raw_items)
    discount_amount = parse_money(form.get("discount_amount"))
    tax_amount = parse_money(form.get("tax_amount"))
    initial_payment_amount = parse_money(form.get("initial_payment_amount"))

    subtotal = sum((item["line_total"] for item in normalized_items), start=Decimal("0.00"))
    total_amount = (subtotal - discount_amount + tax_amount).quantize(TWOPLACES)

    if total_amount < 0:
        raise ValidationError("O total da fatura nao pode ficar negativo.")

    try:
        invoice_number = _generate_invoice_number(connection)
        cursor = connection.execute(
            """
            INSERT INTO invoices (
                invoice_number,
                customer_id,
                notes,
                subtotal,
                discount_amount,
                tax_amount,
                total_amount
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                invoice_number,
                _parse_optional_int(form.get("customer_id")),
                form.get("notes", "").strip() or None,
                money_to_db(subtotal),
                money_to_db(discount_amount),
                money_to_db(tax_amount),
                money_to_db(total_amount),
            ),
        )
        invoice_id = int(cursor.lastrowid)

        for index, item in enumerate(normalized_items, start=1):
            connection.execute(
                """
                INSERT INTO invoice_items (
                    invoice_id,
                    product_id,
                    line_number,
                    quantity,
                    unit_price,
                    discount_amount,
                    line_total
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    invoice_id,
                    item["product_id"],
                    index,
                    quantity_to_db(item["quantity"]),
                    money_to_db(item["unit_price"]),
                    money_to_db(item["discount_amount"]),
                    money_to_db(item["line_total"]),
                ),
            )

            connection.execute(
                """
                UPDATE products
                SET stock_quantity = ?, updated_at = CURRENT_TIMESTAMP
                WHERE product_id = ?
                """,
                (quantity_to_db(item["new_stock"]), item["product_id"]),
            )

            connection.execute(
                """
                INSERT INTO stock_movements (
                    product_id,
                    invoice_id,
                    movement_type,
                    quantity_delta,
                    balance_after,
                    notes
                )
                VALUES (?, ?, 'SALE', ?, ?, ?)
                """,
                (
                    item["product_id"],
                    invoice_id,
                    quantity_to_db(item["quantity"] * Decimal("-1")),
                    quantity_to_db(item["new_stock"]),
                    f"Saida pela fatura {invoice_number}.",
                ),
            )

        if initial_payment_amount > 0:
            _record_payment_in_transaction(
                connection,
                invoice_id=invoice_id,
                amount=initial_payment_amount,
                payment_method=form.get("initial_payment_method", "CASH"),
                reference_number=form.get("payment_reference", ""),
                notes="Pagamento registrado na emissao da fatura.",
            )
        else:
            _sync_invoice_status(connection, invoice_id)

        connection.commit()
        return invoice_id
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise ValidationError("Nao foi possivel salvar a fatura com os dados informados.") from exc
    except Exception:
        connection.rollback()
        raise


def record_payment(connection: sqlite3.Connection, invoice_id: int, form: dict[str, str]) -> None:
    amount = parse_money(form.get("amount"))
    payment_method = form.get("payment_method", "").strip().upper()
    reference_number = form.get("reference_number", "").strip()
    notes = form.get("notes", "").strip()

    try:
        _record_payment_in_transaction(
            connection,
            invoice_id=invoice_id,
            amount=amount,
            payment_method=payment_method,
            reference_number=reference_number,
            notes=notes,
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def cancel_invoice(connection: sqlite3.Connection, invoice_id: int) -> None:
    invoice = connection.execute(
        """
        SELECT
            invoice_id,
            invoice_number,
            status
        FROM invoices
        WHERE invoice_id = ?
        """,
        (invoice_id,),
    ).fetchone()

    if invoice is None:
        raise ValidationError("Fatura nao encontrada.")

    if invoice["status"] == "CANCELLED":
        raise ValidationError("A fatura ja esta cancelada.")

    financial = connection.execute(
        """
        SELECT paid_amount
        FROM invoice_financials
        WHERE invoice_id = ?
        """,
        (invoice_id,),
    ).fetchone()

    paid_amount = money_from_db(financial["paid_amount"] if financial else 0)
    if paid_amount > 0:
        raise ValidationError("Nao e permitido cancelar uma fatura que ja recebeu pagamentos.")

    items = connection.execute(
        """
        SELECT product_id, quantity
        FROM invoice_items
        WHERE invoice_id = ?
        ORDER BY line_number
        """,
        (invoice_id,),
    ).fetchall()

    try:
        for item in items:
            product = connection.execute(
                """
                SELECT stock_quantity
                FROM products
                WHERE product_id = ?
                """,
                (item["product_id"],),
            ).fetchone()

            current_stock = quantity_from_db(product["stock_quantity"])
            quantity = quantity_from_db(item["quantity"])
            new_stock = current_stock + quantity

            connection.execute(
                """
                UPDATE products
                SET stock_quantity = ?, updated_at = CURRENT_TIMESTAMP
                WHERE product_id = ?
                """,
                (quantity_to_db(new_stock), item["product_id"]),
            )

            connection.execute(
                """
                INSERT INTO stock_movements (
                    product_id,
                    invoice_id,
                    movement_type,
                    quantity_delta,
                    balance_after,
                    notes
                )
                VALUES (?, ?, 'CANCEL_RETURN', ?, ?, ?)
                """,
                (
                    item["product_id"],
                    invoice_id,
                    quantity_to_db(quantity),
                    quantity_to_db(new_stock),
                    f"Reposicao do cancelamento {invoice['invoice_number']}.",
                ),
            )

        connection.execute(
            """
            UPDATE invoices
            SET status = 'CANCELLED', updated_at = CURRENT_TIMESTAMP
            WHERE invoice_id = ?
            """,
            (invoice_id,),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def _record_payment_in_transaction(
    connection: sqlite3.Connection,
    invoice_id: int,
    amount: Decimal,
    payment_method: str,
    reference_number: str,
    notes: str,
) -> None:
    if amount <= 0:
        raise ValidationError("O valor do pagamento precisa ser maior do que zero.")

    if payment_method not in {"CASH", "CARD", "TRANSFER", "MOBILE", "OTHER"}:
        raise ValidationError("Escolha um metodo de pagamento valido.")

    invoice = connection.execute(
        """
        SELECT
            i.invoice_id,
            i.status,
            i.total_amount,
            COALESCE(f.paid_amount, 0) AS paid_amount
        FROM invoices i
        LEFT JOIN invoice_financials f ON f.invoice_id = i.invoice_id
        WHERE i.invoice_id = ?
        """,
        (invoice_id,),
    ).fetchone()

    if invoice is None:
        raise ValidationError("Fatura nao encontrada.")

    if invoice["status"] == "CANCELLED":
        raise ValidationError("Nao e possivel registrar pagamento numa fatura cancelada.")

    total_amount = money_from_db(invoice["total_amount"])
    paid_amount = money_from_db(invoice["paid_amount"])
    balance_due = (total_amount - paid_amount).quantize(TWOPLACES)

    if amount > balance_due:
        raise ValidationError("O pagamento nao pode ser maior do que o saldo em aberto.")

    connection.execute(
        """
        INSERT INTO payments (
            invoice_id,
            payment_method,
            amount,
            reference_number,
            notes
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            invoice_id,
            payment_method,
            money_to_db(amount),
            reference_number or None,
            notes or None,
        ),
    )
    _sync_invoice_status(connection, invoice_id)


def _sync_invoice_status(connection: sqlite3.Connection, invoice_id: int) -> None:
    invoice = connection.execute(
        """
        SELECT
            i.total_amount,
            COALESCE(f.paid_amount, 0) AS paid_amount
        FROM invoices i
        LEFT JOIN invoice_financials f ON f.invoice_id = i.invoice_id
        WHERE i.invoice_id = ?
        """,
        (invoice_id,),
    ).fetchone()

    if invoice is None:
        raise ValidationError("Fatura nao encontrada.")

    total_amount = money_from_db(invoice["total_amount"])
    paid_amount = money_from_db(invoice["paid_amount"])

    if paid_amount <= Decimal("0"):
        status = "OPEN"
    elif paid_amount < total_amount:
        status = "PARTIAL"
    else:
        status = "PAID"

    connection.execute(
        """
        UPDATE invoices
        SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE invoice_id = ?
        """,
        (status, invoice_id),
    )


def _normalize_invoice_items(
    connection: sqlite3.Connection,
    raw_items: list[dict[str, str]],
) -> list[dict[str, Decimal | int | str]]:
    items: list[dict[str, Decimal | int | str]] = []
    quantity_by_product: dict[int, Decimal] = defaultdict(lambda: Decimal("0.000"))

    for raw_item in raw_items:
        product_id = _parse_optional_int(raw_item.get("product_id"))
        if product_id is None:
            continue

        quantity = parse_quantity(raw_item.get("quantity"))
        unit_price = parse_money(raw_item.get("unit_price"))
        discount_amount = parse_money(raw_item.get("discount_amount"))

        if quantity <= 0:
            raise ValidationError("A quantidade de cada item precisa ser maior do que zero.")

        gross_total = (quantity * unit_price).quantize(TWOPLACES)
        if discount_amount > gross_total:
            raise ValidationError("O desconto do item nao pode ser maior do que o valor bruto da linha.")

        product = connection.execute(
            """
            SELECT
                product_id,
                product_name,
                stock_quantity,
                is_active
            FROM products
            WHERE product_id = ?
            """,
            (product_id,),
        ).fetchone()

        if product is None or not product["is_active"]:
            raise ValidationError("Um dos produtos selecionados nao esta disponivel.")

        line_total = (gross_total - discount_amount).quantize(TWOPLACES)
        current_stock = quantity_from_db(product["stock_quantity"])
        quantity_by_product[product_id] += quantity

        items.append(
            {
                "product_id": product_id,
                "product_name": str(product["product_name"]),
                "quantity": quantity,
                "unit_price": unit_price,
                "discount_amount": discount_amount,
                "line_total": line_total,
                "current_stock": current_stock,
            }
        )

    if not items:
        raise ValidationError("Adicione pelo menos um item na fatura.")

    for product_id, total_quantity in quantity_by_product.items():
        current_stock = next(
            item["current_stock"] for item in items if item["product_id"] == product_id
        )
        if total_quantity > current_stock:
            product_name = next(
                str(item["product_name"]) for item in items if item["product_id"] == product_id
            )
            raise ValidationError(f"Estoque insuficiente para o produto {product_name}.")

    if len(quantity_by_product) != len(items):
        raise ValidationError("Cada produto deve aparecer apenas uma vez por fatura.")

    for item in items:
        item["new_stock"] = (item["current_stock"] - item["quantity"]).quantize(THREEPLACES)

    return items


def _generate_code(
    connection: sqlite3.Connection,
    table_name: str,
    field_name: str,
    prefix: str,
) -> str:
    sequence = connection.execute(
        f"SELECT COUNT(*) AS total FROM {table_name}"
    ).fetchone()["total"] + 1

    while True:
        code = f"{prefix}-{sequence:05d}"
        exists = connection.execute(
            f"SELECT 1 FROM {table_name} WHERE {field_name} = ?",
            (code,),
        ).fetchone()
        if exists is None:
            return code
        sequence += 1


def _generate_invoice_number(connection: sqlite3.Connection) -> str:
    prefix_row = connection.execute(
        """
        SELECT invoice_prefix
        FROM business_settings
        WHERE settings_id = 1
        """
    ).fetchone()
    invoice_prefix = str(prefix_row["invoice_prefix"]) if prefix_row else "INV"
    year_month = datetime.now().strftime("%Y%m")
    prefix = f"{invoice_prefix}-{year_month}-"
    last = connection.execute(
        """
        SELECT invoice_number
        FROM invoices
        WHERE invoice_number LIKE ?
        ORDER BY invoice_id DESC
        LIMIT 1
        """,
        (f"{prefix}%",),
    ).fetchone()

    if last is None:
        sequence = 1
    else:
        sequence = int(str(last["invoice_number"]).split("-")[-1]) + 1

    return f"{prefix}{sequence:04d}"


def _parse_optional_int(value: str | None) -> int | None:
    if value in (None, ""):
        return None
    return int(str(value))
