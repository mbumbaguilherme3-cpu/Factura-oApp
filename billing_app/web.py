from __future__ import annotations

from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import parse_qs, urlencode
import mimetypes
import re
from wsgiref.simple_server import make_server

from .admin import (
    authenticate_user,
    change_user_password,
    create_user,
    destroy_session,
    get_business_settings,
    get_user_by_session,
    has_permission,
    list_audit_logs,
    list_users,
    update_business_settings,
    write_audit_log,
)
from .database import DEFAULT_DB_PATH, get_connection
from .maintenance import create_database_backup
from .operations import (
    add_manual_cash_movement,
    adjust_stock,
    close_cash_session,
    create_stock_entry,
    create_supplier,
    get_cash_overview,
    get_last_payment_for_invoice,
    list_stock_entries,
    list_suppliers,
    open_cash_session,
    register_cash_payment,
)
from .reporting import (
    export_receivables_csv,
    export_sales_csv,
    export_stock_csv,
    report_snapshot,
)
from .services import (
    ValidationError,
    cancel_invoice,
    create_category,
    create_customer,
    create_invoice,
    create_product,
    dashboard_snapshot,
    get_customer,
    get_invoice_header,
    get_invoice_detail,
    get_product,
    list_categories,
    list_customers,
    list_invoice_customers,
    list_invoice_products,
    list_invoices,
    list_products,
    list_stock_overview,
    record_payment,
    update_customer,
    update_invoice_header,
    update_product,
)
from .views import (
    render_customer_edit_page,
    page_layout,
    render_audit_page,
    render_cash_page,
    render_categories_page,
    render_customers_page,
    render_dashboard,
    render_invoice_detail,
    render_invoice_edit_page,
    render_invoice_form,
    render_invoice_print_page,
    render_invoices_page,
    render_login_page,
    render_password_page,
    render_product_edit_page,
    render_products_page,
    render_reports_page,
    render_settings_page,
    render_stock_entry_page,
    render_stock_page,
    render_suppliers_page,
    render_users_page,
)


class BillingApplication:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.static_dir = Path(__file__).resolve().parent / "static"
        self.backup_dir = self.db_path.parent / "backups"

    def __call__(self, environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/")
        query = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True)
        form = self._parse_form(environ) if method == "POST" else {}
        cookie_token = self._read_session_token(environ)
        current_user = self._load_current_user(cookie_token)
        client_ip = environ.get("REMOTE_ADDR", "")
        user_agent = environ.get("HTTP_USER_AGENT", "")

        try:
            if path.startswith("/static/"):
                return self._serve_static(path, start_response)

            if path == "/login":
                if method == "GET":
                    return self._html_response(
                        start_response,
                        render_login_page(
                            error=self._message(query, "error"),
                            notice=self._message(query, "message"),
                        ),
                    )
                if method == "POST":
                    return self._login(start_response, form, client_ip, user_agent)

            if path == "/logout" and method == "POST":
                return self._logout(start_response, cookie_token)

            if current_user is None:
                return self._redirect(start_response, "/login", error="Entre no sistema para continuar.")

            if method == "GET" and path == "/":
                return self._dashboard(start_response, query, current_user)

            if path == "/customers":
                if method == "GET":
                    return self._customers_page(start_response, query, current_user)
                if method == "POST":
                    return self._create_customer(start_response, form, current_user, client_ip)

            customer_edit_match = re.fullmatch(r"/customers/(\d+)/edit", path)
            if customer_edit_match:
                if method == "GET":
                    return self._customer_edit_page(
                        start_response,
                        int(customer_edit_match.group(1)),
                        query,
                        current_user,
                    )
                if method == "POST":
                    return self._update_customer(
                        start_response,
                        int(customer_edit_match.group(1)),
                        form,
                        current_user,
                        client_ip,
                    )

            if path == "/categories":
                if method == "GET":
                    return self._categories_page(start_response, query, current_user)
                if method == "POST":
                    return self._create_category(start_response, form, current_user, client_ip)

            if path == "/products":
                if method == "GET":
                    return self._products_page(start_response, query, current_user)
                if method == "POST":
                    return self._create_product(start_response, form, current_user, client_ip)

            product_edit_match = re.fullmatch(r"/products/(\d+)/edit", path)
            if product_edit_match:
                if method == "GET":
                    return self._product_edit_page(
                        start_response,
                        int(product_edit_match.group(1)),
                        query,
                        current_user,
                    )
                if method == "POST":
                    return self._update_product(
                        start_response,
                        int(product_edit_match.group(1)),
                        form,
                        current_user,
                        client_ip,
                    )

            if path == "/invoices":
                if method == "GET":
                    return self._invoices_page(start_response, query, current_user)
                if method == "POST":
                    return self._create_invoice(start_response, form, current_user, client_ip)

            if method == "GET" and path == "/invoices/new":
                return self._invoice_form(start_response, query, current_user)

            invoice_detail_match = re.fullmatch(r"/invoices/(\d+)", path)
            if method == "GET" and invoice_detail_match:
                return self._invoice_detail(
                    start_response,
                    int(invoice_detail_match.group(1)),
                    query,
                    current_user,
                )

            invoice_edit_match = re.fullmatch(r"/invoices/(\d+)/edit", path)
            if invoice_edit_match:
                if method == "GET":
                    return self._invoice_edit_page(
                        start_response,
                        int(invoice_edit_match.group(1)),
                        query,
                        current_user,
                    )
                if method == "POST":
                    return self._update_invoice(
                        start_response,
                        int(invoice_edit_match.group(1)),
                        form,
                        current_user,
                        client_ip,
                    )

            invoice_print_match = re.fullmatch(r"/invoices/(\d+)/print", path)
            if method == "GET" and invoice_print_match:
                return self._invoice_print_page(
                    start_response,
                    int(invoice_print_match.group(1)),
                    current_user,
                )

            payment_match = re.fullmatch(r"/invoices/(\d+)/payments", path)
            if method == "POST" and payment_match:
                return self._register_payment(
                    start_response,
                    int(payment_match.group(1)),
                    form,
                    current_user,
                    client_ip,
                )

            cancel_match = re.fullmatch(r"/invoices/(\d+)/cancel", path)
            if method == "POST" and cancel_match:
                return self._cancel_invoice(
                    start_response,
                    int(cancel_match.group(1)),
                    current_user,
                    client_ip,
                )

            if path == "/suppliers":
                if method == "GET":
                    return self._suppliers_page(start_response, query, current_user)
                if method == "POST":
                    return self._create_supplier(start_response, form, current_user, client_ip)

            if method == "GET" and path == "/stock":
                return self._stock_page(start_response, query, current_user)

            if method == "POST" and path == "/stock/adjust":
                return self._adjust_stock(start_response, form, current_user, client_ip)

            if method == "GET" and path == "/stock/entries/new":
                return self._stock_entry_page(start_response, query, current_user)

            if method == "POST" and path == "/stock/entries":
                return self._create_stock_entry(start_response, form, current_user, client_ip)

            if path == "/cash" and method == "GET":
                return self._cash_page(start_response, query, current_user)

            if method == "POST" and path == "/cash/open":
                return self._open_cash(start_response, form, current_user, client_ip)

            if method == "POST" and path == "/cash/movements":
                return self._cash_movement(start_response, form, current_user, client_ip)

            if method == "POST" and path == "/cash/close":
                return self._close_cash(start_response, form, current_user, client_ip)

            if path == "/reports" and method == "GET":
                return self._reports_page(start_response, query, current_user)

            if method == "GET" and path == "/reports/sales.csv":
                return self._sales_export(start_response, query, current_user)

            if method == "GET" and path == "/reports/stock.csv":
                return self._stock_export(start_response, current_user)

            if method == "GET" and path == "/reports/receivables.csv":
                return self._receivables_export(start_response, current_user)

            if path == "/users":
                if method == "GET":
                    return self._users_page(start_response, query, current_user)
                if method == "POST":
                    return self._create_user(start_response, form, current_user, client_ip)

            if path == "/settings":
                if method == "GET":
                    return self._settings_page(start_response, query, current_user)
                if method == "POST":
                    return self._update_settings(start_response, form, current_user, client_ip)

            if path == "/account/password":
                if method == "GET":
                    return self._password_page(start_response, query, current_user)
                if method == "POST":
                    return self._change_password(start_response, form, current_user, client_ip)

            if method == "GET" and path == "/audit":
                return self._audit_page(start_response, query, current_user)

            if method == "POST" and path == "/backup":
                return self._backup_database(start_response, current_user, client_ip)

            return self._not_found(start_response, current_user)
        except Exception as exc:
            return self._server_error(start_response, exc, current_user)

    def _login(self, start_response, form, client_ip: str, user_agent: str):
        data = self._single_value_dict(form)
        try:
            with get_connection(self.db_path) as connection:
                token, user = authenticate_user(
                    connection,
                    data.get("username", ""),
                    data.get("password", ""),
                    ip_address=client_ip,
                    user_agent=user_agent,
                )
                write_audit_log(
                    connection,
                    action="LOGIN",
                    entity_type="SESSION",
                    entity_id=token[:12],
                    user_id=int(user["user_id"]),
                    details={"username": user["username"]},
                    ip_address=client_ip,
                )
                connection.commit()
            return self._redirect(
                start_response,
                "/",
                message="Sessao iniciada com sucesso.",
                cookies=[self._session_cookie(token)],
            )
        except ValidationError as exc:
            return self._html_response(start_response, render_login_page(error=str(exc)))

    def _logout(self, start_response, cookie_token: str | None):
        with get_connection(self.db_path) as connection:
            destroy_session(connection, cookie_token)
            connection.commit()
        return self._redirect(
            start_response,
            "/login",
            message="Sessao terminada.",
            cookies=[self._clear_session_cookie()],
        )

    def _dashboard(self, start_response, query, current_user):
        if error := self._check_permission(start_response, current_user, "dashboard"):
            return error
        with get_connection(self.db_path) as connection:
            content = render_dashboard(dashboard_snapshot(connection))
        return self._page_response(start_response, "Dashboard", content, "/", current_user, query)

    def _customers_page(self, start_response, query, current_user, form=None, error=""):
        if permission_error := self._check_permission(start_response, current_user, "customers"):
            return permission_error
        with get_connection(self.db_path) as connection:
            customers = list_customers(connection)
        content = render_customers_page(customers, form)
        return self._page_response(
            start_response,
            "Clientes",
            content,
            "/customers",
            current_user,
            query,
            error=error,
        )

    def _create_customer(self, start_response, form, current_user, client_ip):
        if permission_error := self._check_permission(start_response, current_user, "customers"):
            return permission_error
        data = self._single_value_dict(form)
        try:
            with get_connection(self.db_path) as connection:
                customer_id = create_customer(connection, data)
                write_audit_log(
                    connection,
                    action="CREATE_CUSTOMER",
                    entity_type="CUSTOMER",
                    entity_id=customer_id,
                    user_id=int(current_user["user_id"]),
                    details={"full_name": data.get("full_name", "")},
                    ip_address=client_ip,
                )
                connection.commit()
            return self._redirect(start_response, "/customers", "Cliente cadastrado com sucesso.")
        except ValidationError as exc:
            return self._customers_page(start_response, {}, current_user, form=data, error=str(exc))

    def _customer_edit_page(self, start_response, customer_id, query, current_user, form=None, error=""):
        if permission_error := self._check_permission(start_response, current_user, "customers"):
            return permission_error
        with get_connection(self.db_path) as connection:
            customer = form or get_customer(connection, customer_id)
        if customer is None:
            return self._not_found(start_response, current_user)
        content = render_customer_edit_page(customer)
        return self._page_response(
            start_response,
            "Editar Cliente",
            content,
            "/customers",
            current_user,
            query,
            error=error,
        )

    def _update_customer(self, start_response, customer_id, form, current_user, client_ip):
        if permission_error := self._check_permission(start_response, current_user, "customers"):
            return permission_error
        data = self._single_value_dict(form)
        try:
            with get_connection(self.db_path) as connection:
                update_customer(connection, customer_id, data)
                write_audit_log(
                    connection,
                    action="UPDATE_CUSTOMER",
                    entity_type="CUSTOMER",
                    entity_id=customer_id,
                    user_id=int(current_user["user_id"]),
                    details={"full_name": data.get("full_name", "")},
                    ip_address=client_ip,
                )
                connection.commit()
            return self._redirect(start_response, "/customers", "Cliente atualizado com sucesso.")
        except ValidationError as exc:
            with get_connection(self.db_path) as connection:
                existing = get_customer(connection, customer_id) or {}
            existing.update(data)
            return self._customer_edit_page(
                start_response,
                customer_id,
                {},
                current_user,
                form=existing,
                error=str(exc),
            )

    def _categories_page(self, start_response, query, current_user, form=None, error=""):
        if permission_error := self._check_permission(start_response, current_user, "categories"):
            return permission_error
        with get_connection(self.db_path) as connection:
            categories = list_categories(connection)
        content = render_categories_page(categories, form)
        return self._page_response(
            start_response,
            "Categorias",
            content,
            "/categories",
            current_user,
            query,
            error=error,
        )

    def _create_category(self, start_response, form, current_user, client_ip):
        if permission_error := self._check_permission(start_response, current_user, "categories"):
            return permission_error
        data = self._single_value_dict(form)
        try:
            with get_connection(self.db_path) as connection:
                category_id = create_category(connection, data)
                write_audit_log(
                    connection,
                    action="CREATE_CATEGORY",
                    entity_type="CATEGORY",
                    entity_id=category_id,
                    user_id=int(current_user["user_id"]),
                    details={"category_name": data.get("category_name", "")},
                    ip_address=client_ip,
                )
                connection.commit()
            return self._redirect(start_response, "/categories", "Categoria criada com sucesso.")
        except ValidationError as exc:
            return self._categories_page(start_response, {}, current_user, form=data, error=str(exc))

    def _products_page(self, start_response, query, current_user, form=None, error=""):
        if permission_error := self._check_permission(start_response, current_user, "products"):
            return permission_error
        with get_connection(self.db_path) as connection:
            products = list_products(connection)
            categories = list_categories(connection)
        content = render_products_page(products, categories, form)
        return self._page_response(
            start_response,
            "Produtos",
            content,
            "/products",
            current_user,
            query,
            error=error,
        )

    def _create_product(self, start_response, form, current_user, client_ip):
        if permission_error := self._check_permission(start_response, current_user, "products"):
            return permission_error
        data = self._single_value_dict(form)
        try:
            with get_connection(self.db_path) as connection:
                product_id = create_product(connection, data)
                write_audit_log(
                    connection,
                    action="CREATE_PRODUCT",
                    entity_type="PRODUCT",
                    entity_id=product_id,
                    user_id=int(current_user["user_id"]),
                    details={"product_name": data.get("product_name", "")},
                    ip_address=client_ip,
                )
                connection.commit()
            return self._redirect(start_response, "/products", "Produto cadastrado com sucesso.")
        except ValidationError as exc:
            return self._products_page(start_response, {}, current_user, form=data, error=str(exc))

    def _product_edit_page(self, start_response, product_id, query, current_user, form=None, error=""):
        if permission_error := self._check_permission(start_response, current_user, "products"):
            return permission_error
        with get_connection(self.db_path) as connection:
            product = form or get_product(connection, product_id)
            categories = list_categories(connection)
        if product is None:
            return self._not_found(start_response, current_user)
        content = render_product_edit_page(product, categories)
        return self._page_response(
            start_response,
            "Editar Produto",
            content,
            "/products",
            current_user,
            query,
            error=error,
        )

    def _update_product(self, start_response, product_id, form, current_user, client_ip):
        if permission_error := self._check_permission(start_response, current_user, "products"):
            return permission_error
        data = self._single_value_dict(form)
        try:
            with get_connection(self.db_path) as connection:
                update_product(connection, product_id, data)
                write_audit_log(
                    connection,
                    action="UPDATE_PRODUCT",
                    entity_type="PRODUCT",
                    entity_id=product_id,
                    user_id=int(current_user["user_id"]),
                    details={"product_name": data.get("product_name", "")},
                    ip_address=client_ip,
                )
                connection.commit()
            return self._redirect(start_response, "/products", "Produto atualizado com sucesso.")
        except ValidationError as exc:
            with get_connection(self.db_path) as connection:
                existing = get_product(connection, product_id) or {}
            existing.update(data)
            return self._product_edit_page(
                start_response,
                product_id,
                {},
                current_user,
                form=existing,
                error=str(exc),
            )

    def _invoices_page(self, start_response, query, current_user):
        if permission_error := self._check_permission(start_response, current_user, "invoices"):
            return permission_error
        with get_connection(self.db_path) as connection:
            invoices = list_invoices(connection)
        content = render_invoices_page(invoices)
        return self._page_response(start_response, "Faturas", content, "/invoices", current_user, query)

    def _invoice_form(self, start_response, query, current_user, form=None, items=None, error=""):
        if permission_error := self._check_permission(start_response, current_user, "invoices"):
            return permission_error
        with get_connection(self.db_path) as connection:
            customers = list_invoice_customers(connection)
            products = list_invoice_products(connection)
        content = render_invoice_form(customers, products, form=form, form_items=items)
        return self._page_response(
            start_response,
            "Nova Fatura",
            content,
            "/invoices",
            current_user,
            query,
            error=error,
        )

    def _create_invoice(self, start_response, form, current_user, client_ip):
        if permission_error := self._check_permission(start_response, current_user, "invoices"):
            return permission_error
        items = self._extract_invoice_items(form)
        data = self._single_value_dict(form)
        try:
            with get_connection(self.db_path) as connection:
                invoice_id = create_invoice(connection, data, items)
                payment = get_last_payment_for_invoice(connection, invoice_id)
                if payment and payment["payment_method"] == "CASH":
                    register_cash_payment(
                        connection,
                        invoice_id,
                        int(payment["payment_id"]),
                        payment["amount"],
                        int(current_user["user_id"]),
                    )
                write_audit_log(
                    connection,
                    action="CREATE_INVOICE",
                    entity_type="INVOICE",
                    entity_id=invoice_id,
                    user_id=int(current_user["user_id"]),
                    details={"items": len([item for item in items if item.get("product_id")])},
                    ip_address=client_ip,
                )
                connection.commit()
            return self._redirect(start_response, f"/invoices/{invoice_id}", "Fatura emitida com sucesso.")
        except ValidationError as exc:
            return self._invoice_form(
                start_response,
                {},
                current_user,
                form=data,
                items=items,
                error=str(exc),
            )

    def _invoice_detail(self, start_response, invoice_id, query, current_user):
        if permission_error := self._check_permission(start_response, current_user, "invoices"):
            return permission_error
        with get_connection(self.db_path) as connection:
            invoice = get_invoice_detail(connection, invoice_id)
        if invoice is None:
            return self._not_found(start_response, current_user)
        content = render_invoice_detail(invoice)
        return self._page_response(
            start_response,
            f"Fatura {invoice['invoice_number']}",
            content,
            "/invoices",
            current_user,
            query,
        )

    def _invoice_edit_page(self, start_response, invoice_id, query, current_user, form=None, error=""):
        if permission_error := self._check_permission(start_response, current_user, "invoices"):
            return permission_error
        with get_connection(self.db_path) as connection:
            invoice = form or get_invoice_header(connection, invoice_id)
            customers = list_invoice_customers(connection)
        if invoice is None:
            return self._not_found(start_response, current_user)
        content = render_invoice_edit_page(invoice, customers)
        return self._page_response(
            start_response,
            "Editar Fatura",
            content,
            "/invoices",
            current_user,
            query,
            error=error,
        )

    def _update_invoice(self, start_response, invoice_id, form, current_user, client_ip):
        if permission_error := self._check_permission(start_response, current_user, "invoices"):
            return permission_error
        data = self._single_value_dict(form)
        try:
            with get_connection(self.db_path) as connection:
                update_invoice_header(connection, invoice_id, data)
                write_audit_log(
                    connection,
                    action="UPDATE_INVOICE",
                    entity_type="INVOICE",
                    entity_id=invoice_id,
                    user_id=int(current_user["user_id"]),
                    details={
                        "customer_id": data.get("customer_id", ""),
                        "discount_amount": data.get("discount_amount", ""),
                        "tax_amount": data.get("tax_amount", ""),
                    },
                    ip_address=client_ip,
                )
                connection.commit()
            return self._redirect(start_response, f"/invoices/{invoice_id}", "Fatura atualizada com sucesso.")
        except ValidationError as exc:
            with get_connection(self.db_path) as connection:
                existing = get_invoice_header(connection, invoice_id) or {}
            existing.update(data)
            return self._invoice_edit_page(
                start_response,
                invoice_id,
                {},
                current_user,
                form=existing,
                error=str(exc),
            )

    def _invoice_print_page(self, start_response, invoice_id, current_user):
        if permission_error := self._check_permission(start_response, current_user, "invoices"):
            return permission_error
        with get_connection(self.db_path) as connection:
            invoice = get_invoice_detail(connection, invoice_id)
            settings = get_business_settings(connection)
        if invoice is None:
            return self._not_found(start_response, current_user)
        return self._html_response(start_response, render_invoice_print_page(invoice, settings))

    def _register_payment(self, start_response, invoice_id, form, current_user, client_ip):
        if permission_error := self._check_permission(start_response, current_user, "payments"):
            return permission_error
        data = self._single_value_dict(form)
        try:
            with get_connection(self.db_path) as connection:
                record_payment(connection, invoice_id, data)
                payment = get_last_payment_for_invoice(connection, invoice_id)
                if payment and payment["payment_method"] == "CASH":
                    register_cash_payment(
                        connection,
                        invoice_id,
                        int(payment["payment_id"]),
                        payment["amount"],
                        int(current_user["user_id"]),
                    )
                write_audit_log(
                    connection,
                    action="REGISTER_PAYMENT",
                    entity_type="PAYMENT",
                    entity_id=payment["payment_id"] if payment else None,
                    user_id=int(current_user["user_id"]),
                    details={"invoice_id": invoice_id, "amount": data.get("amount", "")},
                    ip_address=client_ip,
                )
                connection.commit()
            return self._redirect(start_response, f"/invoices/{invoice_id}", "Pagamento registrado com sucesso.")
        except ValidationError as exc:
            return self._redirect(start_response, f"/invoices/{invoice_id}", error=str(exc))

    def _cancel_invoice(self, start_response, invoice_id, current_user, client_ip):
        if permission_error := self._check_permission(start_response, current_user, "invoices"):
            return permission_error
        try:
            with get_connection(self.db_path) as connection:
                cancel_invoice(connection, invoice_id)
                write_audit_log(
                    connection,
                    action="CANCEL_INVOICE",
                    entity_type="INVOICE",
                    entity_id=invoice_id,
                    user_id=int(current_user["user_id"]),
                    details={"invoice_id": invoice_id},
                    ip_address=client_ip,
                )
                connection.commit()
            return self._redirect(
                start_response,
                f"/invoices/{invoice_id}",
                "Fatura cancelada com sucesso e estoque reposto.",
            )
        except ValidationError as exc:
            return self._redirect(start_response, f"/invoices/{invoice_id}", error=str(exc))

    def _suppliers_page(self, start_response, query, current_user, form=None, error=""):
        if permission_error := self._check_permission(start_response, current_user, "suppliers"):
            return permission_error
        with get_connection(self.db_path) as connection:
            suppliers = list_suppliers(connection)
        content = render_suppliers_page(suppliers, form)
        return self._page_response(
            start_response,
            "Fornecedores",
            content,
            "/suppliers",
            current_user,
            query,
            error=error,
        )

    def _create_supplier(self, start_response, form, current_user, client_ip):
        if permission_error := self._check_permission(start_response, current_user, "suppliers"):
            return permission_error
        data = self._single_value_dict(form)
        try:
            with get_connection(self.db_path) as connection:
                supplier_id = create_supplier(connection, data)
                write_audit_log(
                    connection,
                    action="CREATE_SUPPLIER",
                    entity_type="SUPPLIER",
                    entity_id=supplier_id,
                    user_id=int(current_user["user_id"]),
                    details={"supplier_name": data.get("supplier_name", "")},
                    ip_address=client_ip,
                )
                connection.commit()
            return self._redirect(start_response, "/suppliers", "Fornecedor registado com sucesso.")
        except ValidationError as exc:
            return self._suppliers_page(start_response, {}, current_user, form=data, error=str(exc))

    def _stock_page(self, start_response, query, current_user):
        if permission_error := self._check_permission(start_response, current_user, "stock"):
            return permission_error
        with get_connection(self.db_path) as connection:
            stock = list_stock_overview(connection)
        content = render_stock_page(stock)
        return self._page_response(start_response, "Estoque", content, "/stock", current_user, query)

    def _adjust_stock(self, start_response, form, current_user, client_ip):
        if permission_error := self._check_permission(start_response, current_user, "stock"):
            return permission_error
        data = self._single_value_dict(form)
        try:
            with get_connection(self.db_path) as connection:
                adjust_stock(connection, data, int(current_user["user_id"]))
                write_audit_log(
                    connection,
                    action="ADJUST_STOCK",
                    entity_type="STOCK",
                    entity_id=data.get("product_id", ""),
                    user_id=int(current_user["user_id"]),
                    details=data,
                    ip_address=client_ip,
                )
                connection.commit()
            return self._redirect(start_response, "/stock", "Ajuste de estoque aplicado.")
        except ValidationError as exc:
            return self._redirect(start_response, "/stock", error=str(exc))

    def _stock_entry_page(self, start_response, query, current_user, form=None, items=None, error=""):
        if permission_error := self._check_permission(start_response, current_user, "stock_entries"):
            return permission_error
        with get_connection(self.db_path) as connection:
            suppliers = list_suppliers(connection)
            products = list_invoice_products(connection)
            entries = list_stock_entries(connection)
        content = render_stock_entry_page(suppliers, products, entries, form=form, form_items=items)
        return self._page_response(
            start_response,
            "Entradas de Estoque",
            content,
            "/stock/entries/new",
            current_user,
            query,
            error=error,
        )

    def _create_stock_entry(self, start_response, form, current_user, client_ip):
        if permission_error := self._check_permission(start_response, current_user, "stock_entries"):
            return permission_error
        data = self._single_value_dict(form)
        items = self._extract_stock_entry_items(form)
        try:
            with get_connection(self.db_path) as connection:
                entry_id = create_stock_entry(connection, data, items, int(current_user["user_id"]))
                write_audit_log(
                    connection,
                    action="CREATE_STOCK_ENTRY",
                    entity_type="STOCK_ENTRY",
                    entity_id=entry_id,
                    user_id=int(current_user["user_id"]),
                    details={"items": len([item for item in items if item.get("product_id")])},
                    ip_address=client_ip,
                )
                connection.commit()
            return self._redirect(start_response, "/stock/entries/new", "Entrada de estoque registada.")
        except ValidationError as exc:
            return self._stock_entry_page(
                start_response,
                {},
                current_user,
                form=data,
                items=items,
                error=str(exc),
            )

    def _cash_page(self, start_response, query, current_user):
        if permission_error := self._check_permission(start_response, current_user, "cash"):
            return permission_error
        with get_connection(self.db_path) as connection:
            cash = get_cash_overview(connection)
        content = render_cash_page(cash)
        return self._page_response(start_response, "Caixa", content, "/cash", current_user, query)

    def _open_cash(self, start_response, form, current_user, client_ip):
        if permission_error := self._check_permission(start_response, current_user, "cash"):
            return permission_error
        data = self._single_value_dict(form)
        try:
            with get_connection(self.db_path) as connection:
                cash_session_id = open_cash_session(
                    connection,
                    data.get("opening_amount", "0"),
                    data.get("notes", ""),
                    int(current_user["user_id"]),
                )
                write_audit_log(
                    connection,
                    action="OPEN_CASH_SESSION",
                    entity_type="CASH_SESSION",
                    entity_id=cash_session_id,
                    user_id=int(current_user["user_id"]),
                    details=data,
                    ip_address=client_ip,
                )
                connection.commit()
            return self._redirect(start_response, "/cash", "Caixa aberto com sucesso.")
        except ValidationError as exc:
            return self._redirect(start_response, "/cash", error=str(exc))

    def _cash_movement(self, start_response, form, current_user, client_ip):
        if permission_error := self._check_permission(start_response, current_user, "cash"):
            return permission_error
        data = self._single_value_dict(form)
        try:
            with get_connection(self.db_path) as connection:
                movement_id = add_manual_cash_movement(
                    connection,
                    data.get("movement_type", ""),
                    data.get("amount", "0"),
                    data.get("notes", ""),
                    int(current_user["user_id"]),
                )
                write_audit_log(
                    connection,
                    action="CASH_MOVEMENT",
                    entity_type="CASH_MOVEMENT",
                    entity_id=movement_id,
                    user_id=int(current_user["user_id"]),
                    details=data,
                    ip_address=client_ip,
                )
                connection.commit()
            return self._redirect(start_response, "/cash", "Movimento de caixa registado.")
        except ValidationError as exc:
            return self._redirect(start_response, "/cash", error=str(exc))

    def _close_cash(self, start_response, form, current_user, client_ip):
        if permission_error := self._check_permission(start_response, current_user, "cash"):
            return permission_error
        data = self._single_value_dict(form)
        try:
            with get_connection(self.db_path) as connection:
                cash_session_id = close_cash_session(
                    connection,
                    data.get("counted_amount", "0"),
                    data.get("notes", ""),
                    int(current_user["user_id"]),
                )
                write_audit_log(
                    connection,
                    action="CLOSE_CASH_SESSION",
                    entity_type="CASH_SESSION",
                    entity_id=cash_session_id,
                    user_id=int(current_user["user_id"]),
                    details=data,
                    ip_address=client_ip,
                )
                connection.commit()
            return self._redirect(start_response, "/cash", "Caixa fechado com sucesso.")
        except ValidationError as exc:
            return self._redirect(start_response, "/cash", error=str(exc))

    def _reports_page(self, start_response, query, current_user):
        if permission_error := self._check_permission(start_response, current_user, "reports"):
            return permission_error
        date_from = self._message(query, "date_from")
        date_to = self._message(query, "date_to")
        with get_connection(self.db_path) as connection:
            report = report_snapshot(connection, date_from=date_from, date_to=date_to)
        content = render_reports_page(report)
        return self._page_response(start_response, "Relatorios", content, "/reports", current_user, query)

    def _sales_export(self, start_response, query, current_user):
        if permission_error := self._check_permission(start_response, current_user, "reports"):
            return permission_error
        with get_connection(self.db_path) as connection:
            payload = export_sales_csv(
                connection,
                date_from=self._message(query, "date_from"),
                date_to=self._message(query, "date_to"),
            )
        return self._file_response(start_response, payload, "vendas.csv", "text/csv; charset=utf-8")

    def _stock_export(self, start_response, current_user):
        if permission_error := self._check_permission(start_response, current_user, "reports"):
            return permission_error
        with get_connection(self.db_path) as connection:
            payload = export_stock_csv(connection)
        return self._file_response(start_response, payload, "estoque.csv", "text/csv; charset=utf-8")

    def _receivables_export(self, start_response, current_user):
        if permission_error := self._check_permission(start_response, current_user, "reports"):
            return permission_error
        with get_connection(self.db_path) as connection:
            payload = export_receivables_csv(connection)
        return self._file_response(start_response, payload, "recebiveis.csv", "text/csv; charset=utf-8")

    def _users_page(self, start_response, query, current_user, form=None, error=""):
        if permission_error := self._check_permission(start_response, current_user, "users"):
            return permission_error
        with get_connection(self.db_path) as connection:
            users = list_users(connection)
        content = render_users_page(users, form)
        return self._page_response(
            start_response,
            "Utilizadores",
            content,
            "/users",
            current_user,
            query,
            error=error,
        )

    def _create_user(self, start_response, form, current_user, client_ip):
        if permission_error := self._check_permission(start_response, current_user, "users"):
            return permission_error
        data = self._single_value_dict(form)
        try:
            with get_connection(self.db_path) as connection:
                user_id = create_user(connection, data)
                write_audit_log(
                    connection,
                    action="CREATE_USER",
                    entity_type="USER",
                    entity_id=user_id,
                    user_id=int(current_user["user_id"]),
                    details={"username": data.get("username", ""), "role": data.get("role", "")},
                    ip_address=client_ip,
                )
                connection.commit()
            return self._redirect(start_response, "/users", "Utilizador criado com sucesso.")
        except ValidationError as exc:
            return self._users_page(start_response, {}, current_user, form=data, error=str(exc))

    def _settings_page(self, start_response, query, current_user, form=None, error=""):
        if permission_error := self._check_permission(start_response, current_user, "settings"):
            return permission_error
        with get_connection(self.db_path) as connection:
            settings = get_business_settings(connection)
        content = render_settings_page(form or settings)
        return self._page_response(
            start_response,
            "Configuracoes",
            content,
            "/settings",
            current_user,
            query,
            error=error,
        )

    def _update_settings(self, start_response, form, current_user, client_ip):
        if permission_error := self._check_permission(start_response, current_user, "settings"):
            return permission_error
        data = self._single_value_dict(form)
        try:
            with get_connection(self.db_path) as connection:
                update_business_settings(connection, data)
                write_audit_log(
                    connection,
                    action="UPDATE_SETTINGS",
                    entity_type="BUSINESS_SETTINGS",
                    entity_id=1,
                    user_id=int(current_user["user_id"]),
                    details=data,
                    ip_address=client_ip,
                )
                connection.commit()
            return self._redirect(start_response, "/settings", "Configuracoes actualizadas.")
        except ValidationError as exc:
            return self._settings_page(start_response, {}, current_user, form=data, error=str(exc))

    def _password_page(self, start_response, query, current_user, error=""):
        content = render_password_page(current_user)
        return self._page_response(
            start_response,
            "Seguranca",
            content,
            "/account/password",
            current_user,
            query,
            error=error,
        )

    def _change_password(self, start_response, form, current_user, client_ip):
        data = self._single_value_dict(form)
        try:
            with get_connection(self.db_path) as connection:
                change_user_password(
                    connection,
                    int(current_user["user_id"]),
                    data.get("current_password", ""),
                    data.get("new_password", ""),
                    data.get("confirm_password", ""),
                )
                write_audit_log(
                    connection,
                    action="CHANGE_PASSWORD",
                    entity_type="USER",
                    entity_id=current_user["user_id"],
                    user_id=int(current_user["user_id"]),
                    details={"username": current_user["username"]},
                    ip_address=client_ip,
                )
                connection.commit()
            return self._redirect(start_response, "/account/password", "Senha atualizada com sucesso.")
        except ValidationError as exc:
            return self._password_page(start_response, {}, current_user, error=str(exc))

    def _audit_page(self, start_response, query, current_user):
        if permission_error := self._check_permission(start_response, current_user, "audit"):
            return permission_error
        with get_connection(self.db_path) as connection:
            logs = list_audit_logs(connection)
        content = render_audit_page(logs)
        return self._page_response(start_response, "Auditoria", content, "/audit", current_user, query)

    def _backup_database(self, start_response, current_user, client_ip):
        if permission_error := self._check_permission(start_response, current_user, "backup"):
            return permission_error
        backup_path = create_database_backup(self.db_path, self.backup_dir)
        with get_connection(self.db_path) as connection:
            write_audit_log(
                connection,
                action="BACKUP_DATABASE",
                entity_type="BACKUP",
                entity_id=backup_path.name,
                user_id=int(current_user["user_id"]),
                details={"backup_path": str(backup_path)},
                ip_address=client_ip,
            )
            connection.commit()
        return self._redirect(start_response, "/audit", f"Backup criado: {backup_path.name}")

    def _serve_static(self, path, start_response):
        relative_path = path.removeprefix("/static/")
        file_path = (self.static_dir / relative_path).resolve()
        if self.static_dir not in file_path.parents and file_path != self.static_dir:
            return self._not_found(start_response)
        if not file_path.exists() or not file_path.is_file():
            return self._not_found(start_response)
        mime_type, _ = mimetypes.guess_type(file_path.name)
        data = file_path.read_bytes()
        start_response(
            "200 OK",
            [
                ("Content-Type", mime_type or "application/octet-stream"),
                ("Content-Length", str(len(data))),
            ],
        )
        return [data]

    def _read_session_token(self, environ) -> str | None:
        cookie_header = environ.get("HTTP_COOKIE", "")
        if not cookie_header:
            return None
        cookie = SimpleCookie()
        cookie.load(cookie_header)
        morsel = cookie.get("session_token")
        return morsel.value if morsel else None

    def _load_current_user(self, session_token: str | None):
        with get_connection(self.db_path) as connection:
            return get_user_by_session(connection, session_token)

    def _extract_invoice_items(self, form):
        rows = self._extract_repeated_rows(form, ["product_id", "quantity", "unit_price", "item_discount_amount"])
        for row in rows:
            row["discount_amount"] = row.pop("item_discount_amount", "0.00") or "0.00"
        return rows

    def _extract_stock_entry_items(self, form):
        return self._extract_repeated_rows(form, ["product_id", "quantity", "unit_cost"])

    def _extract_repeated_rows(self, form, fields: list[str]):
        buckets = {field: form.get(field, []) for field in fields}
        max_length = max([len(values) for values in buckets.values()] + [1])
        rows = []
        for index in range(max_length):
            row = {}
            for field in fields:
                values = buckets[field]
                row[field] = values[index] if index < len(values) else ""
            if "discount_amount" in fields and not row.get("discount_amount"):
                row["discount_amount"] = "0.00"
            rows.append(row)
        return rows

    def _parse_form(self, environ):
        try:
            content_length = int(environ.get("CONTENT_LENGTH") or "0")
        except ValueError:
            content_length = 0
        raw_body = environ["wsgi.input"].read(content_length).decode("utf-8")
        return parse_qs(raw_body, keep_blank_values=True)

    def _single_value_dict(self, form):
        return {key: values[0] if values else "" for key, values in form.items()}

    def _page_response(self, start_response, title, content, path, current_user, query, error=""):
        return self._html_response(
            start_response,
            page_layout(
                title,
                content,
                path,
                notice=self._message(query, "message"),
                error=error or self._message(query, "error"),
                current_user=current_user,
            ),
        )

    def _html_response(self, start_response, html: str, status: str = "200 OK", headers=None):
        data = html.encode("utf-8")
        response_headers = [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Content-Length", str(len(data))),
        ]
        if headers:
            response_headers.extend(headers)
        start_response(status, response_headers)
        return [data]

    def _file_response(self, start_response, payload: bytes, filename: str, content_type: str):
        start_response(
            "200 OK",
            [
                ("Content-Type", content_type),
                ("Content-Disposition", f'attachment; filename="{filename}"'),
                ("Content-Length", str(len(payload))),
            ],
        )
        return [payload]

    def _redirect(self, start_response, location: str, message: str = "", error: str = "", cookies=None):
        query = {}
        if message:
            query["message"] = message
        if error:
            query["error"] = error
        final_location = location
        if query:
            separator = "&" if "?" in location else "?"
            final_location = f"{location}{separator}{urlencode(query)}"
        headers = [("Location", final_location)]
        if cookies:
            for cookie in cookies:
                headers.append(("Set-Cookie", cookie))
        start_response("303 See Other", headers)
        return [b""]

    def _session_cookie(self, token: str) -> str:
        return f"session_token={token}; HttpOnly; Path=/; Max-Age=43200; SameSite=Lax"

    def _clear_session_cookie(self) -> str:
        return "session_token=; HttpOnly; Path=/; Max-Age=0; SameSite=Lax"

    def _check_permission(self, start_response, current_user, permission: str):
        if not has_permission(current_user, permission):
            return self._forbidden(start_response, current_user)
        return None

    def _not_found(self, start_response, current_user=None):
        return self._html_response(
            start_response,
            page_layout(
                "Pagina nao encontrada",
                '<section class="panel"><h2>404</h2><p>A pagina solicitada nao existe.</p></section>',
                "",
                current_user=current_user,
            ),
            status="404 Not Found",
        )

    def _forbidden(self, start_response, current_user=None):
        return self._html_response(
            start_response,
            page_layout(
                "Acesso negado",
                '<section class="panel"><h2>403</h2><p>O teu perfil nao tem permissao para esta area.</p></section>',
                "",
                error="Permissao insuficiente.",
                current_user=current_user,
            ),
            status="403 Forbidden",
        )

    def _server_error(self, start_response, error: Exception, current_user=None):
        return self._html_response(
            start_response,
            page_layout(
                "Erro interno",
                f'<section class="panel"><h2>Erro interno</h2><p>{str(error)}</p></section>',
                "",
                error="Ocorreu um erro ao processar a solicitacao.",
                current_user=current_user,
            ),
            status="500 Internal Server Error",
        )

    def _message(self, query, key):
        values = query.get(key, [])
        return values[0] if values else ""


def serve(application: BillingApplication, host: str = "127.0.0.1", port: int = 8000) -> None:
    with make_server(host, port, application) as server:
        print(f"Sistema de faturacao disponivel em http://{host}:{port}")
        print("Acesso inicial: utilizador admin | senha admin123")
        server.serve_forever()


if __name__ == "__main__":
    serve(BillingApplication(DEFAULT_DB_PATH))
