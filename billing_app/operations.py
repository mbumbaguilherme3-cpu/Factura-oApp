from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import sqlite3

from .services import (
    THREEPLACES,
    TWOPLACES,
    ValidationError,
    money_from_db,
    money_to_db,
    parse_money,
    parse_quantity,
    quantity_from_db,
    quantity_to_db,
)


def list_suppliers(connection: sqlite3.Connection) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT
            supplier_id,
            supplier_code,
            supplier_name,
            tax_number,
            phone,
            email,
            city,
            is_active
        FROM suppliers
        ORDER BY supplier_name
        """
    ).fetchall()
    return [dict(row) for row in rows]


def create_supplier(connection: sqlite3.Connection, form: dict[str, str]) -> int:
    supplier_name = form.get("supplier_name", "").strip()
    if not supplier_name:
        raise ValidationError("Informe o nome do fornecedor.")

    supplier_code = _generate_code(connection, "suppliers", "supplier_code", "SUP")
    cursor = connection.execute(
        """
        INSERT INTO suppliers (
            supplier_code,
            supplier_name,
            tax_number,
            phone,
            email,
            address_line,
            city
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            supplier_code,
            supplier_name,
            form.get("tax_number", "").strip() or None,
            form.get("phone", "").strip() or None,
            form.get("email", "").strip() or None,
            form.get("address_line", "").strip() or None,
            form.get("city", "").strip() or None,
        ),
    )
    return int(cursor.lastrowid)


def list_stock_entries(connection: sqlite3.Connection) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT
            se.stock_entry_id,
            se.entry_number,
            se.received_at,
            se.total_cost,
            COALESCE(s.supplier_name, 'Sem fornecedor') AS supplier_name,
            COALESCE(u.full_name, 'Sistema') AS created_by
        FROM stock_entries se
        LEFT JOIN suppliers s ON s.supplier_id = se.supplier_id
        LEFT JOIN app_users u ON u.user_id = se.created_by_user_id
        ORDER BY se.stock_entry_id DESC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def create_stock_entry(
    connection: sqlite3.Connection,
    form: dict[str, str],
    raw_items: list[dict[str, str]],
    user_id: int | None = None,
) -> int:
    items = _normalize_stock_entry_items(connection, raw_items)
    entry_number = _generate_period_code(connection, "stock_entries", "entry_number", "ENT")
    total_cost = sum((item["line_total"] for item in items), start=Decimal("0.00")).quantize(TWOPLACES)

    try:
        cursor = connection.execute(
            """
            INSERT INTO stock_entries (
                entry_number,
                supplier_id,
                notes,
                total_cost,
                created_by_user_id
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                entry_number,
                _parse_optional_int(form.get("supplier_id")),
                form.get("notes", "").strip() or None,
                money_to_db(total_cost),
                user_id,
            ),
        )
        stock_entry_id = int(cursor.lastrowid)

        for index, item in enumerate(items, start=1):
            connection.execute(
                """
                INSERT INTO stock_entry_items (
                    stock_entry_id,
                    product_id,
                    line_number,
                    quantity,
                    unit_cost,
                    line_total
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    stock_entry_id,
                    item["product_id"],
                    index,
                    quantity_to_db(item["quantity"]),
                    money_to_db(item["unit_cost"]),
                    money_to_db(item["line_total"]),
                ),
            )

            connection.execute(
                """
                UPDATE products
                SET cost_price = ?,
                    stock_quantity = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE product_id = ?
                """,
                (
                    money_to_db(item["unit_cost"]),
                    quantity_to_db(item["new_stock"]),
                    item["product_id"],
                ),
            )

            connection.execute(
                """
                INSERT INTO stock_movements (
                    product_id,
                    stock_entry_id,
                    movement_type,
                    quantity_delta,
                    balance_after,
                    notes
                )
                VALUES (?, ?, 'PURCHASE', ?, ?, ?)
                """,
                (
                    item["product_id"],
                    stock_entry_id,
                    quantity_to_db(item["quantity"]),
                    quantity_to_db(item["new_stock"]),
                    f"Entrada em estoque {entry_number}.",
                ),
            )

        connection.commit()
        return stock_entry_id
    except Exception:
        connection.rollback()
        raise


def adjust_stock(
    connection: sqlite3.Connection,
    form: dict[str, str],
    user_id: int | None = None,
) -> None:
    product_id = _parse_optional_int(form.get("product_id"))
    if product_id is None:
        raise ValidationError("Selecione o produto para ajuste.")

    quantity_delta = parse_quantity(form.get("quantity_delta"))
    reason = form.get("reason", "").strip()

    if quantity_delta == Decimal("0.000"):
        raise ValidationError("O ajuste precisa ser diferente de zero.")
    if not reason:
        raise ValidationError("Informe o motivo do ajuste.")

    product = connection.execute(
        """
        SELECT product_name, stock_quantity
        FROM products
        WHERE product_id = ?
        """,
        (product_id,),
    ).fetchone()
    if product is None:
        raise ValidationError("Produto nao encontrado.")

    current_stock = quantity_from_db(product["stock_quantity"])
    new_stock = (current_stock + quantity_delta).quantize(THREEPLACES)
    if new_stock < 0:
        raise ValidationError("O ajuste deixaria o estoque negativo.")

    try:
        connection.execute(
            """
            UPDATE products
            SET stock_quantity = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE product_id = ?
            """,
            (quantity_to_db(new_stock), product_id),
        )
        note = f"Ajuste manual por utilizador {user_id or 'sistema'}: {reason}"
        connection.execute(
            """
            INSERT INTO stock_movements (
                product_id,
                movement_type,
                quantity_delta,
                balance_after,
                notes
            )
            VALUES (?, 'ADJUSTMENT', ?, ?, ?)
            """,
            (
                product_id,
                quantity_to_db(quantity_delta),
                quantity_to_db(new_stock),
                note,
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def get_open_cash_session(connection: sqlite3.Connection) -> dict[str, object] | None:
    row = connection.execute(
        """
        SELECT
            cs.cash_session_id,
            cs.session_number,
            cs.status,
            cs.opening_amount,
            cs.expected_amount,
            cs.opened_at,
            cs.notes,
            u.full_name AS opened_by
        FROM cash_sessions cs
        JOIN app_users u ON u.user_id = cs.opened_by_user_id
        WHERE cs.status = 'OPEN'
        ORDER BY cs.cash_session_id DESC
        LIMIT 1
        """
    ).fetchone()
    return dict(row) if row else None


def get_cash_overview(connection: sqlite3.Connection) -> dict[str, object]:
    current_session = get_open_cash_session(connection)
    sessions = connection.execute(
        """
        SELECT
            cs.cash_session_id,
            cs.session_number,
            cs.status,
            cs.opened_at,
            cs.closed_at,
            cs.opening_amount,
            cs.expected_amount,
            cs.counted_amount,
            cs.difference_amount,
            ou.full_name AS opened_by,
            cu.full_name AS closed_by
        FROM cash_sessions cs
        JOIN app_users ou ON ou.user_id = cs.opened_by_user_id
        LEFT JOIN app_users cu ON cu.user_id = cs.closed_by_user_id
        ORDER BY cs.cash_session_id DESC
        LIMIT 12
        """
    ).fetchall()
    movements = connection.execute(
        """
        SELECT
            cm.cash_movement_id,
            cm.created_at,
            cm.movement_type,
            cm.amount_delta,
            cm.notes,
            i.invoice_number,
            COALESCE(u.full_name, 'Sistema') AS created_by
        FROM cash_movements cm
        LEFT JOIN invoices i ON i.invoice_id = cm.invoice_id
        LEFT JOIN app_users u ON u.user_id = cm.created_by_user_id
        ORDER BY cm.cash_movement_id DESC
        LIMIT 20
        """
    ).fetchall()
    return {
        "current_session": current_session,
        "sessions": [dict(row) for row in sessions],
        "movements": [dict(row) for row in movements],
    }


def open_cash_session(
    connection: sqlite3.Connection,
    opening_amount: str,
    notes: str,
    user_id: int,
) -> int:
    if get_open_cash_session(connection) is not None:
        raise ValidationError("Ja existe um caixa aberto.")

    opening_value = parse_money(opening_amount)
    session_number = _generate_period_code(connection, "cash_sessions", "session_number", "CX")

    try:
        cursor = connection.execute(
            """
            INSERT INTO cash_sessions (
                session_number,
                opening_amount,
                expected_amount,
                notes,
                opened_by_user_id
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_number,
                money_to_db(opening_value),
                money_to_db(opening_value),
                notes.strip() or None,
                user_id,
            ),
        )
        cash_session_id = int(cursor.lastrowid)
        connection.execute(
            """
            INSERT INTO cash_movements (
                cash_session_id,
                movement_type,
                amount_delta,
                notes,
                created_by_user_id
            )
            VALUES (?, 'OPENING', ?, ?, ?)
            """,
            (
                cash_session_id,
                money_to_db(opening_value),
                "Valor inicial de abertura.",
                user_id,
            ),
        )
        connection.commit()
        return cash_session_id
    except Exception:
        connection.rollback()
        raise


def add_manual_cash_movement(
    connection: sqlite3.Connection,
    movement_type: str,
    amount: str,
    notes: str,
    user_id: int,
) -> int:
    session = get_open_cash_session(connection)
    if session is None:
        raise ValidationError("Nao existe caixa aberto.")

    value = parse_money(amount)
    if value <= 0:
        raise ValidationError("O valor precisa ser maior do que zero.")

    if movement_type not in {"MANUAL_IN", "MANUAL_OUT"}:
        raise ValidationError("Tipo de movimento de caixa invalido.")

    delta = value if movement_type == "MANUAL_IN" else value * Decimal("-1")

    try:
        cursor = connection.execute(
            """
            INSERT INTO cash_movements (
                cash_session_id,
                movement_type,
                amount_delta,
                notes,
                created_by_user_id
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session["cash_session_id"],
                movement_type,
                money_to_db(delta),
                notes.strip() or None,
                user_id,
            ),
        )
        _sync_cash_session_expected_amount(connection, int(session["cash_session_id"]))
        connection.commit()
        return int(cursor.lastrowid)
    except Exception:
        connection.rollback()
        raise


def close_cash_session(
    connection: sqlite3.Connection,
    counted_amount: str,
    notes: str,
    user_id: int,
) -> int:
    session = get_open_cash_session(connection)
    if session is None:
        raise ValidationError("Nao existe caixa aberto para fechar.")

    cash_session_id = int(session["cash_session_id"])
    counted_value = parse_money(counted_amount)
    expected = _sync_cash_session_expected_amount(connection, cash_session_id)
    difference = (counted_value - expected).quantize(TWOPLACES)

    try:
        connection.execute(
            """
            INSERT INTO cash_movements (
                cash_session_id,
                movement_type,
                amount_delta,
                notes,
                created_by_user_id
            )
            VALUES (?, 'CLOSING', ?, ?, ?)
            """,
            (
                cash_session_id,
                "0.00",
                notes.strip() or "Fechamento do caixa.",
                user_id,
            ),
        )
        connection.execute(
            """
            UPDATE cash_sessions
            SET status = 'CLOSED',
                counted_amount = ?,
                difference_amount = ?,
                closed_by_user_id = ?,
                closed_at = CURRENT_TIMESTAMP,
                notes = COALESCE(?, notes)
            WHERE cash_session_id = ?
            """,
            (
                money_to_db(counted_value),
                money_to_db(difference),
                user_id,
                notes.strip() or None,
                cash_session_id,
            ),
        )
        connection.commit()
        return cash_session_id
    except Exception:
        connection.rollback()
        raise


def register_cash_payment(
    connection: sqlite3.Connection,
    invoice_id: int,
    payment_id: int,
    amount: object,
    user_id: int | None,
) -> None:
    session = get_open_cash_session(connection)
    if session is None:
        return

    try:
        connection.execute(
            """
            INSERT INTO cash_movements (
                cash_session_id,
                movement_type,
                amount_delta,
                payment_id,
                invoice_id,
                notes,
                created_by_user_id
            )
            VALUES (?, 'SALE_PAYMENT', ?, ?, ?, ?, ?)
            """,
            (
                session["cash_session_id"],
                money_to_db(money_from_db(amount)),
                payment_id,
                invoice_id,
                "Entrada em dinheiro referente a pagamento de fatura.",
                user_id,
            ),
        )
        _sync_cash_session_expected_amount(connection, int(session["cash_session_id"]))
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def get_last_payment_for_invoice(connection: sqlite3.Connection, invoice_id: int) -> dict[str, object] | None:
    row = connection.execute(
        """
        SELECT
            payment_id,
            payment_method,
            amount
        FROM payments
        WHERE invoice_id = ?
        ORDER BY payment_id DESC
        LIMIT 1
        """,
        (invoice_id,),
    ).fetchone()
    return dict(row) if row else None


def _sync_cash_session_expected_amount(connection: sqlite3.Connection, cash_session_id: int) -> Decimal:
    total = connection.execute(
        """
        SELECT COALESCE(SUM(amount_delta), 0) AS total
        FROM cash_movements
        WHERE cash_session_id = ?
        """,
        (cash_session_id,),
    ).fetchone()["total"]
    expected = money_from_db(total)
    connection.execute(
        """
        UPDATE cash_sessions
        SET expected_amount = ?
        WHERE cash_session_id = ?
        """,
        (money_to_db(expected), cash_session_id),
    )
    return expected


def _normalize_stock_entry_items(
    connection: sqlite3.Connection,
    raw_items: list[dict[str, str]],
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for raw_item in raw_items:
        product_id = _parse_optional_int(raw_item.get("product_id"))
        if product_id is None:
            continue

        quantity = parse_quantity(raw_item.get("quantity"))
        unit_cost = parse_money(raw_item.get("unit_cost"))
        if quantity <= 0:
            raise ValidationError("As quantidades da entrada precisam ser maiores do que zero.")

        product = connection.execute(
            """
            SELECT product_name, stock_quantity
            FROM products
            WHERE product_id = ?
            """,
            (product_id,),
        ).fetchone()
        if product is None:
            raise ValidationError("Um dos produtos informados nao existe.")

        current_stock = quantity_from_db(product["stock_quantity"])
        new_stock = (current_stock + quantity).quantize(THREEPLACES)
        items.append(
            {
                "product_id": product_id,
                "quantity": quantity,
                "unit_cost": unit_cost,
                "line_total": (quantity * unit_cost).quantize(TWOPLACES),
                "new_stock": new_stock,
            }
        )

    if not items:
        raise ValidationError("Adicione pelo menos um item na entrada de estoque.")
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


def _generate_period_code(
    connection: sqlite3.Connection,
    table_name: str,
    field_name: str,
    prefix: str,
) -> str:
    year_month = datetime.now().strftime("%Y%m")
    base = f"{prefix}-{year_month}-"
    row = connection.execute(
        f"""
        SELECT {field_name} AS value
        FROM {table_name}
        WHERE {field_name} LIKE ?
        ORDER BY rowid DESC
        LIMIT 1
        """,
        (f"{base}%",),
    ).fetchone()
    sequence = 1 if row is None else int(str(row["value"]).split("-")[-1]) + 1
    return f"{base}{sequence:04d}"


def _parse_optional_int(value: str | None) -> int | None:
    if value in (None, ""):
        return None
    return int(str(value))
