from __future__ import annotations

from html import escape

from .services import format_money, format_quantity


def page_layout(
    title: str,
    content: str,
    current_path: str,
    notice: str = "",
    error: str = "",
    current_user: dict[str, object] | None = None,
) -> str:
    user_block = ""
    if current_user is not None:
        user_block = f"""
            <div class="user-card">
                <strong>{escape(str(current_user['full_name']))}</strong>
                <span>{escape(str(current_user['role']))}</span>
                <a class="button button-ghost small-button" href="/account/password">Senha</a>
                <form method="post" action="/logout">
                    <button class="button button-ghost small-button" type="submit">Sair</button>
                </form>
            </div>
        """

    return f"""<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(title)} | Faturacao da Loja</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="shell">
        <aside class="sidebar">
            <div class="brand">
                <div class="brand-mark">FL</div>
                <div>
                    <strong>Faturacao da Loja</strong>
                    <span>Operacao, vendas e caixa</span>
                </div>
            </div>
            <nav class="nav">
                {nav_link("/", "Dashboard", current_path)}
                {nav_link("/customers", "Clientes", current_path)}
                {nav_link("/categories", "Categorias", current_path)}
                {nav_link("/products", "Produtos", current_path)}
                {nav_link("/invoices", "Faturas", current_path)}
                {nav_link("/suppliers", "Fornecedores", current_path)}
                {nav_link("/stock", "Estoque", current_path)}
                {nav_link("/stock/entries/new", "Entradas", current_path)}
                {nav_link("/cash", "Caixa", current_path)}
                {nav_link("/reports", "Relatorios", current_path)}
                {nav_link("/users", "Utilizadores", current_path)}
                {nav_link("/settings", "Configuracoes", current_path)}
                {nav_link("/audit", "Auditoria", current_path)}
            </nav>
            {user_block}
        </aside>
        <main class="content">
            <header class="topbar">
                <div>
                    <h1>{escape(title)}</h1>
                    <p>Base operacional da loja com foco em consistencia, faturacao e rastreabilidade.</p>
                </div>
                <a class="button button-ghost" href="/invoices/new">Nova fatura</a>
            </header>
            {message_block(notice, "notice")}
            {message_block(error, "error")}
            {content}
        </main>
    </div>
    <script src="/static/app.js"></script>
</body>
</html>"""


def render_login_page(error: str = "", notice: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Entrar | Faturacao da Loja</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body class="login-body">
    <main class="login-shell">
        <section class="login-panel">
            <div class="brand login-brand">
                <div class="brand-mark">FL</div>
                <div>
                    <strong>Faturacao da Loja</strong>
                    <span>Acesso ao sistema operacional</span>
                </div>
            </div>
            {message_block(notice, "notice")}
            {message_block(error, "error")}
            <form method="post" action="/login" class="form-grid single-column">
                <label>
                    <span>Utilizador</span>
                    <input type="text" name="username" value="admin" required>
                </label>
                <label>
                    <span>Senha</span>
                    <input type="password" name="password" value="admin123" required>
                </label>
                <div class="form-actions full-width">
                    <button class="button" type="submit">Entrar no sistema</button>
                </div>
            </form>
            <p class="muted small-text">Utilizador inicial: <strong>admin</strong> | Senha inicial: <strong>admin123</strong></p>
        </section>
    </main>
</body>
</html>"""


def render_dashboard(snapshot: dict[str, object]) -> str:
    metrics = snapshot["metrics"]
    cards = f"""
    <section class="stats-grid">
        {stat_card("Clientes ativos", str(metrics["customer_count"]))}
        {stat_card("Produtos ativos", str(metrics["product_count"]))}
        {stat_card("Faturas emitidas", str(metrics["invoice_count"]))}
        {stat_card("Vendas de hoje", f"Kz {format_money(metrics['today_sales'])}")}
        {stat_card("Contas a receber", f"Kz {format_money(metrics['receivables'])}")}
    </section>
    """

    low_stock_rows = "".join(
        f"""
        <tr>
            <td>{escape(item['product_name'])}</td>
            <td>{format_quantity(item['stock_quantity'])} {escape(item['unit'])}</td>
            <td>{format_quantity(item['minimum_stock'])} {escape(item['unit'])}</td>
        </tr>
        """
        for item in snapshot["low_stock"]
    ) or '<tr><td colspan="3">Nenhum alerta de estoque neste momento.</td></tr>'

    invoice_rows = "".join(
        f"""
        <tr>
            <td><a href="/invoices/{item['invoice_id']}">{escape(item['invoice_number'])}</a></td>
            <td>{escape(item['customer_name'])}</td>
            <td><span class="status status-{str(item['status']).lower()}">{escape(item['status'])}</span></td>
            <td>Kz {format_money(item['total_amount'])}</td>
            <td>Kz {format_money(item['balance_due'])}</td>
        </tr>
        """
        for item in snapshot["recent_invoices"]
    ) or '<tr><td colspan="5">Ainda nao existem faturas.</td></tr>'

    return f"""
    {cards}
    <section class="grid two-columns">
        <article class="panel">
            <div class="panel-header">
                <h2>Ultimas faturas</h2>
                <a href="/invoices">Ver todas</a>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Numero</th>
                        <th>Cliente</th>
                        <th>Status</th>
                        <th>Total</th>
                        <th>Saldo</th>
                    </tr>
                </thead>
                <tbody>{invoice_rows}</tbody>
            </table>
        </article>
        <article class="panel">
            <div class="panel-header">
                <h2>Alertas de estoque</h2>
                <a href="/stock">Abrir estoque</a>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Produto</th>
                        <th>Atual</th>
                        <th>Minimo</th>
                    </tr>
                </thead>
                <tbody>{low_stock_rows}</tbody>
            </table>
        </article>
    </section>
    """


def render_customers_page(customers: list[dict[str, object]], form: dict[str, str] | None = None) -> str:
    form = form or {}
    rows = "".join(
        f"""
        <tr>
            <td>{escape(item['customer_code'])}</td>
            <td>{escape(item['full_name'])}</td>
            <td>{escape(item['phone'] or '-')}</td>
            <td>{escape(item['email'] or '-')}</td>
            <td>{escape(item['city'] or '-')}</td>
            <td><a href="/customers/{item['customer_id']}/edit">Editar</a></td>
        </tr>
        """
        for item in customers
    ) or '<tr><td colspan="6">Nenhum cliente cadastrado.</td></tr>'

    return f"""
    <section class="grid two-columns">
        <article class="panel">
            <h2>Novo cliente</h2>
            <form method="post" action="/customers" class="form-grid">
                <label>
                    <span>Nome completo</span>
                    <input type="text" name="full_name" value="{escape(form.get('full_name', ''))}" required>
                </label>
                <label>
                    <span>NIF / Documento</span>
                    <input type="text" name="tax_number" value="{escape(form.get('tax_number', ''))}">
                </label>
                <label>
                    <span>Telefone</span>
                    <input type="text" name="phone" value="{escape(form.get('phone', ''))}">
                </label>
                <label>
                    <span>Email</span>
                    <input type="email" name="email" value="{escape(form.get('email', ''))}">
                </label>
                <label class="full-width">
                    <span>Endereco</span>
                    <input type="text" name="address_line" value="{escape(form.get('address_line', ''))}">
                </label>
                <label>
                    <span>Cidade</span>
                    <input type="text" name="city" value="{escape(form.get('city', ''))}">
                </label>
                <div class="form-actions full-width">
                    <button class="button" type="submit">Salvar cliente</button>
                </div>
            </form>
        </article>
        <article class="panel">
            <div class="panel-header">
                <h2>Clientes cadastrados</h2>
                <span>{len(customers)} registros</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Codigo</th>
                        <th>Nome</th>
                        <th>Telefone</th>
                        <th>Email</th>
                        <th>Cidade</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </article>
    </section>
    """


def render_categories_page(categories: list[dict[str, object]], form: dict[str, str] | None = None) -> str:
    form = form or {}
    rows = "".join(
        f"""
        <tr>
            <td>{escape(item['category_code'])}</td>
            <td>{escape(item['category_name'])}</td>
            <td>{escape(item['description'] or '-')}</td>
        </tr>
        """
        for item in categories
    ) or '<tr><td colspan="3">Nenhuma categoria cadastrada.</td></tr>'

    return f"""
    <section class="grid two-columns">
        <article class="panel">
            <h2>Nova categoria</h2>
            <form method="post" action="/categories" class="form-grid">
                <label>
                    <span>Nome da categoria</span>
                    <input type="text" name="category_name" value="{escape(form.get('category_name', ''))}" required>
                </label>
                <label class="full-width">
                    <span>Descricao</span>
                    <input type="text" name="description" value="{escape(form.get('description', ''))}">
                </label>
                <div class="form-actions full-width">
                    <button class="button" type="submit">Salvar categoria</button>
                </div>
            </form>
        </article>
        <article class="panel">
            <div class="panel-header">
                <h2>Categorias</h2>
                <span>{len(categories)} registros</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Codigo</th>
                        <th>Categoria</th>
                        <th>Descricao</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </article>
    </section>
    """


def render_products_page(
    products: list[dict[str, object]],
    categories: list[dict[str, object]],
    form: dict[str, str] | None = None,
) -> str:
    form = form or {}
    category_options = "".join(
        f'<option value="{item["category_id"]}" {"selected" if str(item["category_id"]) == form.get("category_id", "") else ""}>{escape(item["category_name"])}</option>'
        for item in categories
    )

    rows = "".join(
        f"""
        <tr class="{'row-alert' if item['stock_alert'] else ''}">
            <td>{escape(item['product_code'])}</td>
            <td>{escape(item['product_name'])}</td>
            <td>{escape(item['category_name'] or '-')}</td>
            <td>Kz {format_money(item['sale_price'])}</td>
            <td>{format_quantity(item['stock_quantity'])} {escape(item['unit'])}</td>
            <td>{format_quantity(item['minimum_stock'])} {escape(item['unit'])}</td>
            <td><a href="/products/{item['product_id']}/edit">Editar</a></td>
        </tr>
        """
        for item in products
    ) or '<tr><td colspan="7">Nenhum produto cadastrado.</td></tr>'

    return f"""
    <section class="grid two-columns">
        <article class="panel">
            <h2>Novo produto</h2>
            <form method="post" action="/products" class="form-grid">
                <label>
                    <span>Nome do produto</span>
                    <input type="text" name="product_name" value="{escape(form.get('product_name', ''))}" required>
                </label>
                <label>
                    <span>Codigo de barras</span>
                    <input type="text" name="barcode" value="{escape(form.get('barcode', ''))}">
                </label>
                <label>
                    <span>Categoria</span>
                    <select name="category_id">
                        <option value="">Sem categoria</option>
                        {category_options}
                    </select>
                </label>
                <label>
                    <span>Unidade</span>
                    <input type="text" name="unit" maxlength="20" value="{escape(form.get('unit', 'UN'))}">
                </label>
                <label>
                    <span>Preco de custo</span>
                    <input type="number" step="0.01" min="0" name="cost_price" value="{escape(form.get('cost_price', '0.00'))}" required>
                </label>
                <label>
                    <span>Preco de venda</span>
                    <input type="number" step="0.01" min="0" name="sale_price" value="{escape(form.get('sale_price', '0.00'))}" required>
                </label>
                <label>
                    <span>Estoque inicial</span>
                    <input type="number" step="0.001" min="0" name="stock_quantity" value="{escape(form.get('stock_quantity', '0'))}" required>
                </label>
                <label>
                    <span>Estoque minimo</span>
                    <input type="number" step="0.001" min="0" name="minimum_stock" value="{escape(form.get('minimum_stock', '0'))}" required>
                </label>
                <label class="full-width">
                    <span>Descricao</span>
                    <input type="text" name="description" value="{escape(form.get('description', ''))}">
                </label>
                <div class="form-actions full-width">
                    <button class="button" type="submit">Salvar produto</button>
                </div>
            </form>
        </article>
        <article class="panel">
            <div class="panel-header">
                <h2>Produtos</h2>
                <span>{len(products)} registros</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Codigo</th>
                        <th>Produto</th>
                        <th>Categoria</th>
                        <th>Preco</th>
                        <th>Estoque</th>
                        <th>Minimo</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </article>
    </section>
    """


def render_invoices_page(invoices: list[dict[str, object]]) -> str:
    rows = "".join(
        f"""
        <tr>
            <td><a href="/invoices/{item['invoice_id']}">{escape(item['invoice_number'])}</a></td>
            <td>{escape(item['customer_name'])}</td>
            <td>{escape(str(item['issue_date']))[:16]}</td>
            <td><span class="status status-{str(item['status']).lower()}">{escape(item['status'])}</span></td>
            <td>Kz {format_money(item['total_amount'])}</td>
            <td>Kz {format_money(item['paid_amount'])}</td>
            <td>Kz {format_money(item['balance_due'])}</td>
            <td><a href="/invoices/{item['invoice_id']}/edit">Editar</a> | <a href="/invoices/{item['invoice_id']}/print" target="_blank">Imprimir</a></td>
        </tr>
        """
        for item in invoices
    ) or '<tr><td colspan="8">Nenhuma fatura emitida.</td></tr>'

    return f"""
    <section class="panel">
        <div class="panel-header">
            <div>
                <h2>Faturas emitidas</h2>
                <p>Consulte rapidamente valores totais, saldo em aberto e status financeiro.</p>
            </div>
            <a class="button" href="/invoices/new">Emitir nova fatura</a>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Numero</th>
                    <th>Cliente</th>
                    <th>Data</th>
                    <th>Status</th>
                    <th>Total</th>
                    <th>Pago</th>
                    <th>Saldo</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </section>
    """


def render_invoice_form(
    customers: list[dict[str, object]],
    products: list[dict[str, object]],
    form: dict[str, str] | None = None,
    form_items: list[dict[str, str]] | None = None,
) -> str:
    form = form or {}
    form_items = form_items or [
        {"product_id": "", "quantity": "1", "unit_price": "", "discount_amount": "0.00"}
    ]

    customer_options = "".join(
        f'<option value="{item["customer_id"]}" {"selected" if str(item["customer_id"]) == form.get("customer_id", "") else ""}>{escape(item["full_name"])}</option>'
        for item in customers
    )

    product_options = "".join(
        f'<option value="{item["product_id"]}" data-price="{item["sale_price"]}" data-stock="{item["stock_quantity"]}" data-unit="{escape(item["unit"])}">{escape(item["product_name"])} ({format_quantity(item["stock_quantity"])} {escape(item["unit"])})</option>'
        for item in products
    )

    rows = "".join(
        invoice_item_row(item, index, product_options)
        for index, item in enumerate(form_items)
    )

    template_html = invoice_item_row(
        {"product_id": "", "quantity": "1", "unit_price": "", "discount_amount": "0.00"},
        "__INDEX__",
        product_options,
    )

    return f"""
    <section class="panel">
        <div class="panel-header">
            <div>
                <h2>Emissao de fatura</h2>
                <p>O sistema atualiza o estoque automaticamente e permite registrar o primeiro pagamento ja nesta tela.</p>
            </div>
            <a href="/invoices" class="button button-ghost">Voltar para faturas</a>
        </div>
        <form method="post" action="/invoices" class="form-grid invoice-form" data-invoice-form>
            <label>
                <span>Cliente</span>
                <select name="customer_id">
                    <option value="">Consumidor avulso</option>
                    {customer_options}
                </select>
            </label>
            <label class="full-width">
                <span>Observacoes</span>
                <input type="text" name="notes" value="{escape(form.get('notes', ''))}">
            </label>
            <section class="full-width invoice-lines">
                <div class="panel-header compact">
                    <h3>Itens da fatura</h3>
                    <button type="button" class="button button-ghost" data-add-line>Adicionar linha</button>
                </div>
                <div class="invoice-table-wrapper">
                    <table class="invoice-table">
                        <thead>
                            <tr>
                                <th>Produto</th>
                                <th>Qtd</th>
                                <th>Preco unitario</th>
                                <th>Desconto</th>
                                <th>Total</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody data-lines-container>
                            {rows}
                        </tbody>
                    </table>
                </div>
            </section>
            <section class="full-width grid three-columns invoice-financials">
                <label>
                    <span>Desconto geral</span>
                    <input type="number" step="0.01" min="0" name="discount_amount" value="{escape(form.get('discount_amount', '0.00'))}">
                </label>
                <label>
                    <span>Imposto</span>
                    <input type="number" step="0.01" min="0" name="tax_amount" value="{escape(form.get('tax_amount', '0.00'))}">
                </label>
                <div class="summary-card">
                    <strong>Resumo ao vivo</strong>
                    <span data-summary-subtotal>Subtotal: Kz 0,00</span>
                    <span data-summary-total>Total: Kz 0,00</span>
                </div>
            </section>
            <section class="full-width grid three-columns">
                <label>
                    <span>Pagamento inicial</span>
                    <input type="number" step="0.01" min="0" name="initial_payment_amount" value="{escape(form.get('initial_payment_amount', '0.00'))}">
                </label>
                <label>
                    <span>Metodo do pagamento</span>
                    <select name="initial_payment_method">
                        {payment_method_options(form.get('initial_payment_method', 'CASH'))}
                    </select>
                </label>
                <label>
                    <span>Referencia</span>
                    <input type="text" name="payment_reference" value="{escape(form.get('payment_reference', ''))}">
                </label>
            </section>
            <template id="invoice-line-template">{template_html}</template>
            <div class="form-actions full-width">
                <button class="button" type="submit">Emitir fatura</button>
            </div>
        </form>
    </section>
    """


def render_invoice_detail(invoice: dict[str, object]) -> str:
    item_rows = "".join(
        f"""
        <tr>
            <td>{item['line_number']}</td>
            <td>{escape(item['product_name'])}</td>
            <td>{format_quantity(item['quantity'])} {escape(item['unit'])}</td>
            <td>Kz {format_money(item['unit_price'])}</td>
            <td>Kz {format_money(item['discount_amount'])}</td>
            <td>Kz {format_money(item['line_total'])}</td>
        </tr>
        """
        for item in invoice["items"]
    )

    payment_rows = "".join(
        f"""
        <tr>
            <td>{escape(str(item['payment_date']))[:16]}</td>
            <td>{escape(str(item['payment_method']))}</td>
            <td>Kz {format_money(item['amount'])}</td>
            <td>{escape(item['reference_number'] or '-')}</td>
            <td>{escape(item['notes'] or '-')}</td>
        </tr>
        """
        for item in invoice["payments"]
    ) or '<tr><td colspan="5">Nenhum pagamento registrado.</td></tr>'

    payment_panel = ""
    if invoice["can_receive_payment"]:
        payment_panel = f"""
        <article class="panel">
            <h2>Registrar pagamento</h2>
            <form method="post" action="/invoices/{invoice['invoice_id']}/payments" class="form-grid">
                <label>
                    <span>Valor</span>
                    <input type="number" step="0.01" min="0.01" name="amount" required>
                </label>
                <label>
                    <span>Metodo</span>
                    <select name="payment_method">
                        {payment_method_options('CASH')}
                    </select>
                </label>
                <label>
                    <span>Referencia</span>
                    <input type="text" name="reference_number">
                </label>
                <label class="full-width">
                    <span>Notas</span>
                    <input type="text" name="notes">
                </label>
                <div class="form-actions full-width">
                    <button class="button" type="submit">Registrar pagamento</button>
                </div>
            </form>
        </article>
        """

    cancel_panel = ""
    if invoice["can_cancel"]:
        cancel_panel = f"""
        <article class="panel warning-panel">
            <h2>Cancelar fatura</h2>
            <p>O cancelamento devolve os itens ao estoque e marca a fatura como cancelada.</p>
            <form method="post" action="/invoices/{invoice['invoice_id']}/cancel">
                <button class="button button-danger" type="submit">Cancelar fatura</button>
            </form>
        </article>
        """

    return f"""
    <section class="grid two-columns">
        <article class="panel">
            <div class="panel-header">
                <div>
                    <h2>{escape(invoice['invoice_number'])}</h2>
                    <p>Emitida em {escape(str(invoice['issue_date']))[:16]}</p>
                </div>
                <div class="button-group">
                    <a class="button button-ghost" href="/invoices/{invoice['invoice_id']}/edit">Editar</a>
                    <a class="button button-ghost" href="/invoices/{invoice['invoice_id']}/print" target="_blank">Imprimir</a>
                    <span class="status status-{str(invoice['status']).lower()}">{escape(invoice['status'])}</span>
                </div>
            </div>
            <div class="summary-grid">
                {summary_metric("Cliente", invoice["customer_name"])}
                {summary_metric("Subtotal", f"Kz {format_money(invoice['subtotal'])}")}
                {summary_metric("Desconto", f"Kz {format_money(invoice['discount_amount'])}")}
                {summary_metric("Imposto", f"Kz {format_money(invoice['tax_amount'])}")}
                {summary_metric("Total", f"Kz {format_money(invoice['total_amount'])}")}
                {summary_metric("Pago", f"Kz {format_money(invoice['paid_amount'])}")}
                {summary_metric("Saldo", f"Kz {format_money(invoice['balance_due'])}")}
            </div>
            <p class="muted">{escape(invoice['notes'] or 'Sem observacoes adicionais.')}</p>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Produto</th>
                        <th>Quantidade</th>
                        <th>Preco</th>
                        <th>Desconto</th>
                        <th>Total</th>
                    </tr>
                </thead>
                <tbody>{item_rows}</tbody>
            </table>
        </article>
        <div class="stack">
            {payment_panel}
            {cancel_panel}
            <article class="panel">
                <h2>Pagamentos</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Data</th>
                            <th>Metodo</th>
                            <th>Valor</th>
                            <th>Referencia</th>
                            <th>Notas</th>
                        </tr>
                    </thead>
                    <tbody>{payment_rows}</tbody>
                </table>
            </article>
        </div>
    </section>
    """


def render_customer_edit_page(customer: dict[str, object]) -> str:
    checked = "checked" if customer.get("is_active") else ""
    return f"""
    <section class="panel">
        <div class="panel-header">
            <div>
                <h2>Editar cliente</h2>
                <p>{escape(customer['customer_code'])}</p>
            </div>
            <a href="/customers" class="button button-ghost">Voltar</a>
        </div>
        <form method="post" action="/customers/{customer['customer_id']}/edit" class="form-grid">
            <label>
                <span>Nome completo</span>
                <input type="text" name="full_name" value="{escape(str(customer.get('full_name', '')))}" required>
            </label>
            <label>
                <span>NIF / Documento</span>
                <input type="text" name="tax_number" value="{escape(str(customer.get('tax_number') or ''))}">
            </label>
            <label>
                <span>Telefone</span>
                <input type="text" name="phone" value="{escape(str(customer.get('phone') or ''))}">
            </label>
            <label>
                <span>Email</span>
                <input type="email" name="email" value="{escape(str(customer.get('email') or ''))}">
            </label>
            <label class="full-width">
                <span>Endereco</span>
                <input type="text" name="address_line" value="{escape(str(customer.get('address_line') or ''))}">
            </label>
            <label>
                <span>Cidade</span>
                <input type="text" name="city" value="{escape(str(customer.get('city') or ''))}">
            </label>
            <label class="checkbox-label">
                <input type="checkbox" name="is_active" value="1" {checked}>
                <span>Cliente ativo</span>
            </label>
            <div class="form-actions full-width">
                <button class="button" type="submit">Guardar alteracoes</button>
            </div>
        </form>
    </section>
    """


def render_product_edit_page(product: dict[str, object], categories: list[dict[str, object]]) -> str:
    checked = "checked" if product.get("is_active") else ""
    category_options = "".join(
        f'<option value="{item["category_id"]}" {"selected" if str(item["category_id"]) == str(product.get("category_id") or "") else ""}>{escape(item["category_name"])}</option>'
        for item in categories
    )
    return f"""
    <section class="panel">
        <div class="panel-header">
            <div>
                <h2>Editar produto</h2>
                <p>{escape(product['product_code'])}</p>
            </div>
            <a href="/products" class="button button-ghost">Voltar</a>
        </div>
        <form method="post" action="/products/{product['product_id']}/edit" class="form-grid">
            <label>
                <span>Nome do produto</span>
                <input type="text" name="product_name" value="{escape(str(product.get('product_name', '')))}" required>
            </label>
            <label>
                <span>Codigo de barras</span>
                <input type="text" name="barcode" value="{escape(str(product.get('barcode') or ''))}">
            </label>
            <label>
                <span>Categoria</span>
                <select name="category_id">
                    <option value="">Sem categoria</option>
                    {category_options}
                </select>
            </label>
            <label>
                <span>Unidade</span>
                <input type="text" name="unit" value="{escape(str(product.get('unit') or 'UN'))}">
            </label>
            <label>
                <span>Preco de custo</span>
                <input type="number" step="0.01" min="0" name="cost_price" value="{escape(str(product.get('cost_price', 0)))}" required>
            </label>
            <label>
                <span>Preco de venda</span>
                <input type="number" step="0.01" min="0" name="sale_price" value="{escape(str(product.get('sale_price', 0)))}" required>
            </label>
            <label>
                <span>Estoque atual</span>
                <input type="text" value="{escape(str(product.get('stock_quantity', '0')))}" disabled>
            </label>
            <label>
                <span>Estoque minimo</span>
                <input type="number" step="0.001" min="0" name="minimum_stock" value="{escape(str(product.get('minimum_stock', 0)))}" required>
            </label>
            <label class="full-width">
                <span>Descricao</span>
                <input type="text" name="description" value="{escape(str(product.get('description') or ''))}">
            </label>
            <label class="checkbox-label">
                <input type="checkbox" name="is_active" value="1" {checked}>
                <span>Produto ativo</span>
            </label>
            <div class="form-actions full-width">
                <button class="button" type="submit">Guardar alteracoes</button>
            </div>
        </form>
    </section>
    """


def render_invoice_edit_page(invoice: dict[str, object], customers: list[dict[str, object]]) -> str:
    customer_options = "".join(
        f'<option value="{item["customer_id"]}" {"selected" if str(item["customer_id"]) == str(invoice.get("customer_id") or "") else ""}>{escape(item["full_name"])}</option>'
        for item in customers
    )
    return f"""
    <section class="panel">
        <div class="panel-header">
            <div>
                <h2>Editar fatura</h2>
                <p>{escape(invoice['invoice_number'])}</p>
            </div>
            <a href="/invoices/{invoice['invoice_id']}" class="button button-ghost">Voltar</a>
        </div>
        <form method="post" action="/invoices/{invoice['invoice_id']}/edit" class="form-grid">
            <label>
                <span>Cliente</span>
                <select name="customer_id">
                    <option value="">Consumidor avulso</option>
                    {customer_options}
                </select>
            </label>
            <label>
                <span>Status atual</span>
                <input type="text" value="{escape(str(invoice.get('status', 'OPEN')))}" disabled>
            </label>
            <label>
                <span>Subtotal</span>
                <input type="text" value="Kz {escape(format_money(invoice.get('subtotal', 0)))}" disabled>
            </label>
            <label>
                <span>Pago</span>
                <input type="text" value="Kz {escape(format_money(invoice.get('paid_amount', 0)))}" disabled>
            </label>
            <label>
                <span>Desconto geral</span>
                <input type="number" step="0.01" min="0" name="discount_amount" value="{escape(str(invoice.get('discount_amount', 0)))}" required>
            </label>
            <label>
                <span>Imposto</span>
                <input type="number" step="0.01" min="0" name="tax_amount" value="{escape(str(invoice.get('tax_amount', 0)))}" required>
            </label>
            <label class="full-width">
                <span>Observacoes</span>
                <input type="text" name="notes" value="{escape(str(invoice.get('notes') or ''))}">
            </label>
            <div class="form-actions full-width">
                <button class="button" type="submit">Guardar alteracoes</button>
            </div>
        </form>
    </section>
    """


def render_password_page(current_user: dict[str, object]) -> str:
    return f"""
    <section class="panel narrow-panel">
        <div class="panel-header">
            <div>
                <h2>Trocar senha</h2>
                <p>{escape(str(current_user['username']))}</p>
            </div>
        </div>
        <form method="post" action="/account/password" class="form-grid single-column">
            <label>
                <span>Senha atual</span>
                <input type="password" name="current_password" required>
            </label>
            <label>
                <span>Nova senha</span>
                <input type="password" name="new_password" required>
            </label>
            <label>
                <span>Confirmar nova senha</span>
                <input type="password" name="confirm_password" required>
            </label>
            <div class="form-actions full-width">
                <button class="button" type="submit">Atualizar senha</button>
            </div>
        </form>
    </section>
    """


def render_invoice_print_page(invoice: dict[str, object], settings: dict[str, object]) -> str:
    item_rows = "".join(
        f"""
        <tr>
            <td>{item['line_number']}</td>
            <td>{escape(item['product_name'])}</td>
            <td>{format_quantity(item['quantity'])} {escape(item['unit'])}</td>
            <td>Kz {format_money(item['unit_price'])}</td>
            <td>Kz {format_money(item['line_total'])}</td>
        </tr>
        """
        for item in invoice["items"]
    )
    return f"""<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(invoice['invoice_number'])}</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body class="print-body">
    <main class="print-shell">
        <section class="print-toolbar no-print">
            <button class="button" onclick="window.print()">Imprimir agora</button>
            <a class="button button-ghost" href="/invoices/{invoice['invoice_id']}">Voltar</a>
        </section>
        <section class="print-card">
            <header class="print-header">
                <div>
                    <h1>{escape(str(settings.get('company_name', 'Minha Loja')))}</h1>
                    <p>{escape(str(settings.get('company_address') or ''))}</p>
                    <p>{escape(str(settings.get('company_phone') or ''))}</p>
                    <p>{escape(str(settings.get('company_email') or ''))}</p>
                </div>
                <div class="print-meta">
                    <strong>Fatura {escape(invoice['invoice_number'])}</strong>
                    <span>Data: {escape(str(invoice['issue_date']))[:16]}</span>
                    <span>Cliente: {escape(str(invoice['customer_name']))}</span>
                    <span>Status: {escape(str(invoice['status']))}</span>
                </div>
            </header>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Produto</th>
                        <th>Quantidade</th>
                        <th>Preco</th>
                        <th>Total</th>
                    </tr>
                </thead>
                <tbody>{item_rows}</tbody>
            </table>
            <section class="print-totals">
                <div>{summary_metric("Subtotal", f"Kz {format_money(invoice['subtotal'])}")}</div>
                <div>{summary_metric("Desconto", f"Kz {format_money(invoice['discount_amount'])}")}</div>
                <div>{summary_metric(str(settings.get('tax_label', 'IVA')), f"Kz {format_money(invoice['tax_amount'])}")}</div>
                <div>{summary_metric("Total", f"Kz {format_money(invoice['total_amount'])}")}</div>
                <div>{summary_metric("Pago", f"Kz {format_money(invoice['paid_amount'])}")}</div>
                <div>{summary_metric("Saldo", f"Kz {format_money(invoice['balance_due'])}")}</div>
            </section>
            <footer class="print-footer">
                <p>{escape(str(settings.get('receipt_footer') or 'Obrigado pela preferencia.'))}</p>
                <p>{escape(str(settings.get('legal_notice') or 'Documento emitido pelo sistema interno da loja.'))}</p>
            </footer>
        </section>
    </main>
</body>
</html>"""


def render_stock_page(stock: dict[str, object]) -> str:
    product_rows = "".join(
        f"""
        <tr class="{'row-alert' if float(item['stock_quantity']) <= float(item['minimum_stock']) else ''}">
            <td>{escape(item['product_name'])}</td>
            <td>{format_quantity(item['stock_quantity'])} {escape(item['unit'])}</td>
            <td>{format_quantity(item['minimum_stock'])} {escape(item['unit'])}</td>
            <td>Kz {format_money(item['sale_price'])}</td>
        </tr>
        """
        for item in stock["products"]
    ) or '<tr><td colspan="4">Nenhum produto cadastrado.</td></tr>'

    movement_rows = "".join(
        f"""
        <tr>
            <td>{escape(str(item['created_at']))[:16]}</td>
            <td>{escape(item['product_name'])}</td>
            <td>{escape(item['movement_type'])}</td>
            <td>{format_quantity(item['quantity_delta'])}</td>
            <td>{format_quantity(item['balance_after'])}</td>
            <td>{escape(item['invoice_number'] or '-')}</td>
        </tr>
        """
        for item in stock["movements"]
    ) or '<tr><td colspan="6">Nenhum movimento registrado.</td></tr>'

    return f"""
    <section class="grid two-columns">
        <article class="panel">
            <div class="panel-header">
                <h2>Posicao de estoque</h2>
                <span>{len(stock['products'])} produtos</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Produto</th>
                        <th>Atual</th>
                        <th>Minimo</th>
                        <th>Preco</th>
                    </tr>
                </thead>
                <tbody>{product_rows}</tbody>
            </table>
        </article>
        <article class="panel">
            <div class="panel-header">
                <h2>Ajuste manual</h2>
                <span>Correcao controlada de saldo</span>
            </div>
            <form method="post" action="/stock/adjust" class="form-grid">
                <label>
                    <span>Produto</span>
                    <select name="product_id" required>
                        {''.join(f'<option value="{item["product_id"]}">{escape(item["product_name"])}</option>' for item in stock["products"])}
                    </select>
                </label>
                <label>
                    <span>Delta do estoque</span>
                    <input type="number" step="0.001" name="quantity_delta" placeholder="Ex.: 5 ou -2" required>
                </label>
                <label class="full-width">
                    <span>Motivo</span>
                    <input type="text" name="reason" required>
                </label>
                <div class="form-actions full-width">
                    <button class="button" type="submit">Aplicar ajuste</button>
                </div>
            </form>
        </article>
        <article class="panel full-width">
            <div class="panel-header">
                <h2>Movimentos recentes</h2>
                <span>Ultimas 20 operacoes</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Data</th>
                        <th>Produto</th>
                        <th>Tipo</th>
                        <th>Delta</th>
                        <th>Saldo</th>
                        <th>Fatura</th>
                    </tr>
                </thead>
                <tbody>{movement_rows}</tbody>
            </table>
        </article>
    </section>
    """


def render_users_page(users: list[dict[str, object]], form: dict[str, str] | None = None) -> str:
    form = form or {}
    rows = "".join(
        f"""
        <tr>
            <td>{escape(item['full_name'])}</td>
            <td>{escape(item['username'])}</td>
            <td>{escape(item['role'])}</td>
            <td>{'Ativo' if item['is_active'] else 'Inativo'}</td>
            <td>{escape(str(item['last_login_at'] or '-'))[:16]}</td>
        </tr>
        """
        for item in users
    ) or '<tr><td colspan="5">Nenhum utilizador registado.</td></tr>'

    return f"""
    <section class="grid two-columns">
        <article class="panel">
            <h2>Novo utilizador</h2>
            <form method="post" action="/users" class="form-grid">
                <label>
                    <span>Nome completo</span>
                    <input type="text" name="full_name" value="{escape(form.get('full_name', ''))}" required>
                </label>
                <label>
                    <span>Utilizador</span>
                    <input type="text" name="username" value="{escape(form.get('username', ''))}" required>
                </label>
                <label>
                    <span>Senha</span>
                    <input type="password" name="password" required>
                </label>
                <label>
                    <span>Papel</span>
                    <select name="role" required>
                        <option value="ADMIN">ADMIN</option>
                        <option value="MANAGER">MANAGER</option>
                        <option value="CASHIER">CASHIER</option>
                        <option value="STOCK">STOCK</option>
                    </select>
                </label>
                <div class="form-actions full-width">
                    <button class="button" type="submit">Criar utilizador</button>
                </div>
            </form>
        </article>
        <article class="panel">
            <div class="panel-header">
                <h2>Utilizadores</h2>
                <span>{len(users)} registos</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Nome</th>
                        <th>Utilizador</th>
                        <th>Papel</th>
                        <th>Status</th>
                        <th>Ultimo acesso</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </article>
    </section>
    """


def render_suppliers_page(suppliers: list[dict[str, object]], form: dict[str, str] | None = None) -> str:
    form = form or {}
    rows = "".join(
        f"""
        <tr>
            <td>{escape(item['supplier_code'])}</td>
            <td>{escape(item['supplier_name'])}</td>
            <td>{escape(item['phone'] or '-')}</td>
            <td>{escape(item['email'] or '-')}</td>
            <td>{escape(item['city'] or '-')}</td>
        </tr>
        """
        for item in suppliers
    ) or '<tr><td colspan="5">Nenhum fornecedor registado.</td></tr>'

    return f"""
    <section class="grid two-columns">
        <article class="panel">
            <h2>Novo fornecedor</h2>
            <form method="post" action="/suppliers" class="form-grid">
                <label>
                    <span>Nome do fornecedor</span>
                    <input type="text" name="supplier_name" value="{escape(form.get('supplier_name', ''))}" required>
                </label>
                <label>
                    <span>NIF / Documento</span>
                    <input type="text" name="tax_number" value="{escape(form.get('tax_number', ''))}">
                </label>
                <label>
                    <span>Telefone</span>
                    <input type="text" name="phone" value="{escape(form.get('phone', ''))}">
                </label>
                <label>
                    <span>Email</span>
                    <input type="email" name="email" value="{escape(form.get('email', ''))}">
                </label>
                <label class="full-width">
                    <span>Endereco</span>
                    <input type="text" name="address_line" value="{escape(form.get('address_line', ''))}">
                </label>
                <label>
                    <span>Cidade</span>
                    <input type="text" name="city" value="{escape(form.get('city', ''))}">
                </label>
                <div class="form-actions full-width">
                    <button class="button" type="submit">Salvar fornecedor</button>
                </div>
            </form>
        </article>
        <article class="panel">
            <div class="panel-header">
                <h2>Fornecedores</h2>
                <span>{len(suppliers)} registos</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Codigo</th>
                        <th>Fornecedor</th>
                        <th>Telefone</th>
                        <th>Email</th>
                        <th>Cidade</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </article>
    </section>
    """


def render_stock_entry_page(
    suppliers: list[dict[str, object]],
    products: list[dict[str, object]],
    entries: list[dict[str, object]],
    form: dict[str, str] | None = None,
    form_items: list[dict[str, str]] | None = None,
) -> str:
    form = form or {}
    form_items = form_items or [{"product_id": "", "quantity": "1", "unit_cost": "0.00"}]

    supplier_options = "".join(
        f'<option value="{item["supplier_id"]}" {"selected" if str(item["supplier_id"]) == form.get("supplier_id", "") else ""}>{escape(item["supplier_name"])}</option>'
        for item in suppliers
    )
    product_options = "".join(
        f'<option value="{item["product_id"]}">{escape(item["product_name"])} ({format_quantity(item["stock_quantity"])} {escape(item["unit"])})</option>'
        for item in products
    )
    line_rows = "".join(stock_entry_item_row(item, product_options) for item in form_items)
    entry_rows = "".join(
        f"""
        <tr>
            <td>{escape(item['entry_number'])}</td>
            <td>{escape(item['supplier_name'])}</td>
            <td>{escape(str(item['received_at']))[:16]}</td>
            <td>Kz {format_money(item['total_cost'])}</td>
            <td>{escape(item['created_by'])}</td>
        </tr>
        """
        for item in entries
    ) or '<tr><td colspan="5">Nenhuma entrada registada.</td></tr>'

    return f"""
    <section class="grid two-columns">
        <article class="panel">
            <div class="panel-header">
                <h2>Nova entrada de estoque</h2>
                <span>Compra ou recepcao de mercadoria</span>
            </div>
            <form method="post" action="/stock/entries" class="form-grid" data-stock-entry-form>
                <label>
                    <span>Fornecedor</span>
                    <select name="supplier_id">
                        <option value="">Sem fornecedor</option>
                        {supplier_options}
                    </select>
                </label>
                <label class="full-width">
                    <span>Observacoes</span>
                    <input type="text" name="notes" value="{escape(form.get('notes', ''))}">
                </label>
                <section class="full-width">
                    <div class="panel-header compact">
                        <h3>Itens</h3>
                        <button type="button" class="button button-ghost" data-add-entry-line>Adicionar linha</button>
                    </div>
                    <div class="invoice-table-wrapper">
                        <table class="invoice-table">
                            <thead>
                                <tr>
                                    <th>Produto</th>
                                    <th>Qtd</th>
                                    <th>Custo unitario</th>
                                    <th>Total</th>
                                    <th></th>
                                </tr>
                            </thead>
                            <tbody data-entry-lines>
                                {line_rows}
                            </tbody>
                        </table>
                    </div>
                </section>
                <template id="stock-entry-line-template">{stock_entry_item_row({"product_id": "", "quantity": "1", "unit_cost": "0.00"}, product_options)}</template>
                <div class="form-actions full-width">
                    <button class="button" type="submit">Registrar entrada</button>
                </div>
            </form>
        </article>
        <article class="panel">
            <div class="panel-header">
                <h2>Entradas recentes</h2>
                <span>{len(entries)} registos</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Numero</th>
                        <th>Fornecedor</th>
                        <th>Recebida em</th>
                        <th>Total</th>
                        <th>Por</th>
                    </tr>
                </thead>
                <tbody>{entry_rows}</tbody>
            </table>
        </article>
    </section>
    """


def render_cash_page(cash: dict[str, object]) -> str:
    current = cash["current_session"]
    current_panel = ""
    if current:
        current_panel = f"""
        <article class="panel">
            <div class="panel-header">
                <h2>Caixa aberto</h2>
                <span>{escape(current['session_number'])}</span>
            </div>
            <div class="summary-grid">
                {summary_metric("Abertura", f"Kz {format_money(current['opening_amount'])}")}
                {summary_metric("Esperado", f"Kz {format_money(current['expected_amount'])}")}
                {summary_metric("Aberto em", escape(str(current['opened_at'])[:16]))}
            </div>
            <form method="post" action="/cash/movements" class="form-grid">
                <label>
                    <span>Tipo</span>
                    <select name="movement_type">
                        <option value="MANUAL_IN">Entrada manual</option>
                        <option value="MANUAL_OUT">Saida manual</option>
                    </select>
                </label>
                <label>
                    <span>Valor</span>
                    <input type="number" step="0.01" min="0.01" name="amount" required>
                </label>
                <label class="full-width">
                    <span>Motivo</span>
                    <input type="text" name="notes" required>
                </label>
                <div class="form-actions full-width">
                    <button class="button" type="submit">Registar movimento</button>
                </div>
            </form>
            <form method="post" action="/cash/close" class="form-grid top-gap">
                <label>
                    <span>Valor contado</span>
                    <input type="number" step="0.01" min="0" name="counted_amount" required>
                </label>
                <label>
                    <span>Notas de fecho</span>
                    <input type="text" name="notes">
                </label>
                <div class="form-actions full-width">
                    <button class="button button-danger" type="submit">Fechar caixa</button>
                </div>
            </form>
        </article>
        """
    else:
        current_panel = """
        <article class="panel">
            <div class="panel-header">
                <h2>Abertura de caixa</h2>
                <span>Nenhum caixa aberto</span>
            </div>
            <form method="post" action="/cash/open" class="form-grid">
                <label>
                    <span>Valor inicial</span>
                    <input type="number" step="0.01" min="0" name="opening_amount" required>
                </label>
                <label>
                    <span>Notas</span>
                    <input type="text" name="notes">
                </label>
                <div class="form-actions full-width">
                    <button class="button" type="submit">Abrir caixa</button>
                </div>
            </form>
        </article>
        """

    session_rows = "".join(
        f"""
        <tr>
            <td>{escape(item['session_number'])}</td>
            <td>{escape(item['status'])}</td>
            <td>Kz {format_money(item['opening_amount'])}</td>
            <td>Kz {format_money(item['expected_amount'])}</td>
            <td>Kz {format_money(item['counted_amount'] or 0)}</td>
            <td>Kz {format_money(item['difference_amount'] or 0)}</td>
        </tr>
        """
        for item in cash["sessions"]
    ) or '<tr><td colspan="6">Nenhum historico de caixa.</td></tr>'

    movement_rows = "".join(
        f"""
        <tr>
            <td>{escape(str(item['created_at']))[:16]}</td>
            <td>{escape(item['movement_type'])}</td>
            <td>Kz {format_money(item['amount_delta'])}</td>
            <td>{escape(item['invoice_number'] or '-')}</td>
            <td>{escape(item['created_by'])}</td>
            <td>{escape(item['notes'] or '-')}</td>
        </tr>
        """
        for item in cash["movements"]
    ) or '<tr><td colspan="6">Nenhum movimento de caixa.</td></tr>'

    return f"""
    <section class="grid two-columns">
        {current_panel}
        <article class="panel">
            <div class="panel-header">
                <h2>Historico de caixas</h2>
                <span>{len(cash['sessions'])} sessoes</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Numero</th>
                        <th>Status</th>
                        <th>Abertura</th>
                        <th>Esperado</th>
                        <th>Contado</th>
                        <th>Diferenca</th>
                    </tr>
                </thead>
                <tbody>{session_rows}</tbody>
            </table>
        </article>
        <article class="panel full-width">
            <div class="panel-header">
                <h2>Movimentos de caixa</h2>
                <span>Ultimos 20 movimentos</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Data</th>
                        <th>Tipo</th>
                        <th>Valor</th>
                        <th>Fatura</th>
                        <th>Por</th>
                        <th>Notas</th>
                    </tr>
                </thead>
                <tbody>{movement_rows}</tbody>
            </table>
        </article>
    </section>
    """


def render_reports_page(report: dict[str, object]) -> str:
    summary = report["summary"]
    top_rows = "".join(
        f"""
        <tr>
            <td>{escape(item['product_name'])}</td>
            <td>{format_quantity(item['total_quantity'])}</td>
            <td>Kz {format_money(item['total_sales'])}</td>
        </tr>
        """
        for item in report["top_products"]
    ) or '<tr><td colspan="3">Sem dados no periodo.</td></tr>'

    receivable_rows = "".join(
        f"""
        <tr>
            <td>{escape(item['invoice_number'])}</td>
            <td>{escape(item['customer_name'])}</td>
            <td>{escape(str(item['issue_date']))[:10]}</td>
            <td>Kz {format_money(item['balance_due'])}</td>
        </tr>
        """
        for item in report["receivables"]
    ) or '<tr><td colspan="4">Sem saldos em aberto.</td></tr>'

    return f"""
    <section class="panel">
        <div class="panel-header">
            <div>
                <h2>Filtros do relatorio</h2>
                <p>Consulte um periodo especifico e exporte os dados da operacao.</p>
            </div>
            <div class="button-group">
                <a class="button button-ghost" href="/reports/sales.csv?date_from={escape(report['date_from'])}&date_to={escape(report['date_to'])}">Exportar vendas CSV</a>
                <a class="button button-ghost" href="/reports/stock.csv">Exportar estoque CSV</a>
                <a class="button button-ghost" href="/reports/receivables.csv">Exportar recebiveis CSV</a>
            </div>
        </div>
        <form method="get" action="/reports" class="form-grid three-columns">
            <label>
                <span>Data inicial</span>
                <input type="date" name="date_from" value="{escape(report['date_from'])}">
            </label>
            <label>
                <span>Data final</span>
                <input type="date" name="date_to" value="{escape(report['date_to'])}">
            </label>
            <div class="form-actions align-end">
                <button class="button" type="submit">Aplicar filtro</button>
            </div>
        </form>
    </section>
    <section class="stats-grid">
        {stat_card("Faturas no periodo", str(summary['invoice_count']))}
        {stat_card("Vendas brutas", f"Kz {format_money(summary['gross_sales'])}")}
        {stat_card("Vendas pagas", f"Kz {format_money(summary['paid_sales'])}")}
        {stat_card("Vendas pendentes", f"Kz {format_money(summary['pending_sales'])}")}
    </section>
    <section class="grid two-columns">
        <article class="panel">
            <div class="panel-header">
                <h2>Produtos mais vendidos</h2>
                <span>Top 10</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Produto</th>
                        <th>Quantidade</th>
                        <th>Total</th>
                    </tr>
                </thead>
                <tbody>{top_rows}</tbody>
            </table>
        </article>
        <article class="panel">
            <div class="panel-header">
                <h2>Contas a receber</h2>
                <span>Ultimos 20 titulos</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Fatura</th>
                        <th>Cliente</th>
                        <th>Data</th>
                        <th>Saldo</th>
                    </tr>
                </thead>
                <tbody>{receivable_rows}</tbody>
            </table>
        </article>
    </section>
    """


def render_settings_page(settings: dict[str, object]) -> str:
    checked = "checked" if settings.get("require_customer_tax_number") else ""
    return f"""
    <section class="panel">
        <div class="panel-header">
            <div>
                <h2>Configuracoes da empresa</h2>
                <p>Base configuravel para moeda, sequencia de faturas e campos fiscais internos.</p>
            </div>
            <span>Compliance local ainda precisa de validacao juridico-fiscal</span>
        </div>
        <form method="post" action="/settings" class="form-grid">
            <label>
                <span>Nome da empresa</span>
                <input type="text" name="company_name" value="{escape(str(settings.get('company_name', '')))}" required>
            </label>
            <label>
                <span>NIF</span>
                <input type="text" name="tax_id" value="{escape(str(settings.get('tax_id') or ''))}">
            </label>
            <label>
                <span>Telefone</span>
                <input type="text" name="company_phone" value="{escape(str(settings.get('company_phone') or ''))}">
            </label>
            <label>
                <span>Email</span>
                <input type="email" name="company_email" value="{escape(str(settings.get('company_email') or ''))}">
            </label>
            <label class="full-width">
                <span>Endereco</span>
                <input type="text" name="company_address" value="{escape(str(settings.get('company_address') or ''))}">
            </label>
            <label>
                <span>Codigo da moeda</span>
                <input type="text" name="currency_code" value="{escape(str(settings.get('currency_code', 'AOA')))}">
            </label>
            <label>
                <span>Simbolo da moeda</span>
                <input type="text" name="currency_symbol" value="{escape(str(settings.get('currency_symbol', 'Kz')))}">
            </label>
            <label>
                <span>Rotulo do imposto</span>
                <input type="text" name="tax_label" value="{escape(str(settings.get('tax_label', 'IVA')))}">
            </label>
            <label>
                <span>Taxa padrao (%)</span>
                <input type="number" step="0.01" min="0" name="default_tax_rate" value="{escape(str(settings.get('default_tax_rate', 0)))}">
            </label>
            <label>
                <span>Prefixo da fatura</span>
                <input type="text" name="invoice_prefix" value="{escape(str(settings.get('invoice_prefix', 'INV')))}">
            </label>
            <label class="full-width checkbox-label">
                <input type="checkbox" name="require_customer_tax_number" value="1" {checked}>
                <span>Exigir NIF do cliente na operacao</span>
            </label>
            <label class="full-width">
                <span>Rodape do documento</span>
                <input type="text" name="receipt_footer" value="{escape(str(settings.get('receipt_footer') or ''))}">
            </label>
            <label class="full-width">
                <span>Observacao legal interna</span>
                <input type="text" name="legal_notice" value="{escape(str(settings.get('legal_notice') or ''))}">
            </label>
            <div class="form-actions full-width">
                <button class="button" type="submit">Guardar configuracoes</button>
            </div>
        </form>
    </section>
    """


def render_audit_page(logs: list[dict[str, object]]) -> str:
    rows = "".join(
        f"""
        <tr>
            <td>{escape(str(item['created_at']))[:16]}</td>
            <td>{escape(item['actor_name'])}</td>
            <td>{escape(item['action'])}</td>
            <td>{escape(item['entity_type'])}</td>
            <td>{escape(item['entity_id'] or '-')}</td>
            <td>{escape(item['details'] or '-')}</td>
        </tr>
        """
        for item in logs
    ) or '<tr><td colspan="6">Nenhum log de auditoria.</td></tr>'

    return f"""
    <section class="panel">
        <div class="panel-header">
            <div>
                <h2>Auditoria</h2>
                <p>Rastreio de accoes criticas executadas dentro do sistema.</p>
            </div>
            <form method="post" action="/backup">
                <button class="button button-ghost" type="submit">Gerar backup</button>
            </form>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Data</th>
                    <th>Actor</th>
                    <th>Acao</th>
                    <th>Entidade</th>
                    <th>ID</th>
                    <th>Detalhes</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </section>
    """


def nav_link(path: str, label: str, current_path: str) -> str:
    is_active = current_path == path or (path != "/" and current_path.startswith(path))
    active_class = "active" if is_active else ""
    return f'<a class="{active_class}" href="{path}">{escape(label)}</a>'


def message_block(message: str, tone: str) -> str:
    if not message:
        return ""
    return f'<div class="flash flash-{tone}">{escape(message)}</div>'


def stat_card(label: str, value: str) -> str:
    return f"""
    <article class="stat-card">
        <span>{escape(label)}</span>
        <strong>{escape(value)}</strong>
    </article>
    """


def invoice_item_row(item: dict[str, str], index: int | str, product_options: str) -> str:
    selected_product = item.get("product_id", "")
    options = ['<option value="">Selecione um produto</option>']
    for option in product_options.split("</option>"):
        option = option.strip()
        if not option:
            continue
        option = option + "</option>"
        if selected_product and f'value="{selected_product}"' in option:
            option = option.replace(f'value="{selected_product}"', f'value="{selected_product}" selected', 1)
        options.append(option)
    option_markup = "".join(options)

    return f"""
    <tr data-line-item data-line-index="{index}">
        <td>
            <select name="product_id" data-product-select required>
                {option_markup}
            </select>
        </td>
        <td><input type="number" min="0.001" step="0.001" name="quantity" value="{escape(item.get('quantity', '1'))}" data-line-quantity required></td>
        <td><input type="number" min="0" step="0.01" name="unit_price" value="{escape(item.get('unit_price', ''))}" data-line-price required></td>
        <td><input type="number" min="0" step="0.01" name="item_discount_amount" value="{escape(item.get('discount_amount', '0.00'))}" data-line-discount required></td>
        <td><span data-line-total>Kz 0,00</span></td>
        <td><button type="button" class="icon-button" data-remove-line aria-label="Remover linha">x</button></td>
    </tr>
    """


def stock_entry_item_row(item: dict[str, str], product_options: str) -> str:
    selected_product = item.get("product_id", "")
    options = ['<option value="">Selecione um produto</option>']
    for option in product_options.split("</option>"):
        option = option.strip()
        if not option:
            continue
        option = option + "</option>"
        if selected_product and f'value="{selected_product}"' in option:
            option = option.replace(f'value="{selected_product}"', f'value="{selected_product}" selected', 1)
        options.append(option)

    return f"""
    <tr data-entry-item>
        <td>
            <select name="product_id" required>
                {''.join(options)}
            </select>
        </td>
        <td><input type="number" step="0.001" min="0.001" name="quantity" value="{escape(item.get('quantity', '1'))}" required></td>
        <td><input type="number" step="0.01" min="0" name="unit_cost" value="{escape(item.get('unit_cost', '0.00'))}" required></td>
        <td><span data-entry-line-total>Kz 0,00</span></td>
        <td><button type="button" class="icon-button" data-remove-entry-line aria-label="Remover linha">x</button></td>
    </tr>
    """


def payment_method_options(selected: str) -> str:
    methods = [
        ("CASH", "Dinheiro"),
        ("CARD", "Cartao"),
        ("TRANSFER", "Transferencia"),
        ("MOBILE", "Pagamento movel"),
        ("OTHER", "Outro"),
    ]
    return "".join(
        f'<option value="{value}" {"selected" if value == selected else ""}>{label}</option>'
        for value, label in methods
    )


def summary_metric(label: str, value: str) -> str:
    return f"""
    <div class="summary-metric">
        <span>{escape(label)}</span>
        <strong>{escape(value)}</strong>
    </div>
    """
