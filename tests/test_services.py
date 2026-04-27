from pathlib import Path
import tempfile
import unittest

from billing_app.database import get_connection, initialize_database
from billing_app.operations import (
    add_manual_cash_movement,
    close_cash_session,
    create_stock_entry,
    get_cash_overview,
    open_cash_session,
)
from billing_app.services import (
    ValidationError,
    cancel_invoice,
    create_invoice,
    get_invoice_detail,
    list_stock_overview,
    record_payment,
)


class BillingServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_store.db"
        initialize_database(self.db_path, with_seed=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_invoice_updates_stock_and_status(self):
        with get_connection(self.db_path) as connection:
            invoice_id = create_invoice(
                connection,
                {
                    "customer_id": "1",
                    "notes": "Venda de teste",
                    "discount_amount": "50.00",
                    "tax_amount": "0.00",
                    "initial_payment_amount": "200.00",
                    "initial_payment_method": "CASH",
                    "payment_reference": "",
                },
                [
                    {
                        "product_id": "1",
                        "quantity": "2",
                        "unit_price": "250.00",
                        "discount_amount": "0.00",
                    }
                ],
            )

            detail = get_invoice_detail(connection, invoice_id)
            stock = list_stock_overview(connection)

        self.assertIsNotNone(detail)
        self.assertEqual(detail["status"], "PARTIAL")
        self.assertEqual(str(detail["balance_due"]), "250")
        product = next(item for item in stock["products"] if item["product_name"] == "Agua Mineral 1.5L")
        self.assertEqual(str(product["stock_quantity"]), "46")

    def test_payment_cannot_exceed_balance(self):
        with get_connection(self.db_path) as connection:
            invoice_id = create_invoice(
                connection,
                {
                    "customer_id": "1",
                    "notes": "",
                    "discount_amount": "0.00",
                    "tax_amount": "0.00",
                    "initial_payment_amount": "0.00",
                    "initial_payment_method": "CASH",
                    "payment_reference": "",
                },
                [
                    {
                        "product_id": "2",
                        "quantity": "1",
                        "unit_price": "600.00",
                        "discount_amount": "0.00",
                    }
                ],
            )

            with self.assertRaises(ValidationError):
                record_payment(
                    connection,
                    invoice_id,
                    {
                        "amount": "700.00",
                        "payment_method": "CASH",
                        "reference_number": "",
                        "notes": "",
                    },
                )

    def test_cancel_invoice_restock_items(self):
        with get_connection(self.db_path) as connection:
            invoice_id = create_invoice(
                connection,
                {
                    "customer_id": "",
                    "notes": "",
                    "discount_amount": "0.00",
                    "tax_amount": "0.00",
                    "initial_payment_amount": "0.00",
                    "initial_payment_method": "CASH",
                    "payment_reference": "",
                },
                [
                    {
                        "product_id": "4",
                        "quantity": "3",
                        "unit_price": "550.00",
                        "discount_amount": "0.00",
                    }
                ],
            )

            cancel_invoice(connection, invoice_id)
            detail = get_invoice_detail(connection, invoice_id)
            stock = list_stock_overview(connection)

        self.assertEqual(detail["status"], "CANCELLED")
        product = next(item for item in stock["products"] if item["product_name"] == "Detergente 500ml")
        self.assertEqual(str(product["stock_quantity"]), "20")

    def test_stock_entry_increases_inventory(self):
        with get_connection(self.db_path) as connection:
            create_stock_entry(
                connection,
                {
                    "supplier_id": "",
                    "notes": "Reposicao semanal",
                },
                [
                    {
                        "product_id": "1",
                        "quantity": "10",
                        "unit_cost": "180.00",
                    }
                ],
                user_id=1,
            )
            stock = list_stock_overview(connection)

        product = next(item for item in stock["products"] if item["product_name"] == "Agua Mineral 1.5L")
        self.assertEqual(str(product["stock_quantity"]), "58")

    def test_cash_open_movement_and_close(self):
        with get_connection(self.db_path) as connection:
            cash_session_id = open_cash_session(connection, "1000.00", "Abertura do dia", 1)
            add_manual_cash_movement(connection, "MANUAL_IN", "500.00", "Troco recebido", 1)
            close_cash_session(connection, "1500.00", "Fecho sem diferenca", 1)
            cash = get_cash_overview(connection)

        self.assertEqual(cash_session_id, 1)
        self.assertIsNone(cash["current_session"])
        self.assertEqual(cash["sessions"][0]["status"], "CLOSED")
        self.assertEqual(str(cash["sessions"][0]["difference_amount"]), "0")


if __name__ == "__main__":
    unittest.main()
