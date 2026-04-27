from __future__ import annotations

from datetime import datetime
import csv
import io
import sqlite3


def report_snapshot(
    connection: sqlite3.Connection,
    date_from: str = "",
    date_to: str = "",
) -> dict[str, object]:
    filters, params = _date_filter(date_from, date_to, "issue_date")

    summary = connection.execute(
        f"""
        SELECT
            COUNT(*) AS invoice_count,
            COALESCE(SUM(total_amount), 0) AS gross_sales,
            COALESCE(SUM(CASE WHEN status = 'PAID' THEN total_amount ELSE 0 END), 0) AS paid_sales,
            COALESCE(SUM(CASE WHEN status IN ('OPEN', 'PARTIAL') THEN total_amount ELSE 0 END), 0) AS pending_sales
        FROM invoices
        WHERE status <> 'CANCELLED'
          {filters}
        """,
        params,
    ).fetchone()

    top_products = connection.execute(
        f"""
        SELECT
            p.product_name,
            SUM(ii.quantity) AS total_quantity,
            SUM(ii.line_total) AS total_sales
        FROM invoice_items ii
        JOIN invoices i ON i.invoice_id = ii.invoice_id
        JOIN products p ON p.product_id = ii.product_id
        WHERE i.status <> 'CANCELLED'
          {_date_filter(date_from, date_to, "i.issue_date")[0]}
        GROUP BY p.product_id, p.product_name
        ORDER BY total_sales DESC
        LIMIT 10
        """,
        _date_filter(date_from, date_to, "i.issue_date")[1],
    ).fetchall()

    receivables = connection.execute(
        """
        SELECT
            i.invoice_number,
            COALESCE(c.full_name, 'Consumidor avulso') AS customer_name,
            i.issue_date,
            i.total_amount,
            f.paid_amount,
            f.balance_due
        FROM invoices i
        LEFT JOIN customers c ON c.customer_id = i.customer_id
        JOIN invoice_financials f ON f.invoice_id = i.invoice_id
        WHERE i.status IN ('OPEN', 'PARTIAL')
        ORDER BY i.issue_date ASC
        LIMIT 20
        """
    ).fetchall()

    return {
        "summary": dict(summary),
        "top_products": [dict(row) for row in top_products],
        "receivables": [dict(row) for row in receivables],
        "date_from": date_from,
        "date_to": date_to,
    }


def export_sales_csv(connection: sqlite3.Connection, date_from: str = "", date_to: str = "") -> bytes:
    filters, params = _date_filter(date_from, date_to, "i.issue_date")
    rows = connection.execute(
        f"""
        SELECT
            i.invoice_number,
            i.issue_date,
            COALESCE(c.full_name, 'Consumidor avulso') AS customer_name,
            i.status,
            i.total_amount,
            COALESCE(f.paid_amount, 0) AS paid_amount,
            COALESCE(f.balance_due, 0) AS balance_due
        FROM invoices i
        LEFT JOIN customers c ON c.customer_id = i.customer_id
        LEFT JOIN invoice_financials f ON f.invoice_id = i.invoice_id
        WHERE 1 = 1
          {filters}
        ORDER BY i.issue_date DESC
        """,
        params,
    ).fetchall()
    return _rows_to_csv(
        ["invoice_number", "issue_date", "customer_name", "status", "total_amount", "paid_amount", "balance_due"],
        [dict(row) for row in rows],
    )


def export_stock_csv(connection: sqlite3.Connection) -> bytes:
    rows = connection.execute(
        """
        SELECT
            product_code,
            product_name,
            unit,
            cost_price,
            sale_price,
            stock_quantity,
            minimum_stock
        FROM products
        ORDER BY product_name
        """
    ).fetchall()
    return _rows_to_csv(
        ["product_code", "product_name", "unit", "cost_price", "sale_price", "stock_quantity", "minimum_stock"],
        [dict(row) for row in rows],
    )


def export_receivables_csv(connection: sqlite3.Connection) -> bytes:
    rows = connection.execute(
        """
        SELECT
            i.invoice_number,
            COALESCE(c.full_name, 'Consumidor avulso') AS customer_name,
            i.issue_date,
            i.total_amount,
            f.paid_amount,
            f.balance_due
        FROM invoices i
        LEFT JOIN customers c ON c.customer_id = i.customer_id
        JOIN invoice_financials f ON f.invoice_id = i.invoice_id
        WHERE i.status IN ('OPEN', 'PARTIAL')
        ORDER BY i.issue_date ASC
        """
    ).fetchall()
    return _rows_to_csv(
        ["invoice_number", "customer_name", "issue_date", "total_amount", "paid_amount", "balance_due"],
        [dict(row) for row in rows],
    )


def _rows_to_csv(columns: list[str], rows: list[dict[str, object]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow({column: row.get(column, "") for column in columns})
    return buffer.getvalue().encode("utf-8-sig")


def _date_filter(date_from: str, date_to: str, field_name: str) -> tuple[str, list[str]]:
    clauses: list[str] = []
    params: list[str] = []

    if date_from:
        clauses.append(f"date({field_name}) >= date(?)")
        params.append(date_from)
    if date_to:
        clauses.append(f"date({field_name}) <= date(?)")
        params.append(date_to)

    sql = ""
    if clauses:
        sql = " AND " + " AND ".join(clauses)
    return sql, params
