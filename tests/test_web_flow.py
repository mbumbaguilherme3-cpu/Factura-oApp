from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from urllib.parse import urlencode, urlparse
from wsgiref.util import setup_testing_defaults

from billing_app.database import initialize_database
from billing_app.web import BillingApplication


class BillingWebFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "web_test_store.db"
        initialize_database(self.db_path, with_seed=True)
        self.app = BillingApplication(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_full_operational_flow_with_print_and_password_change(self):
        status, headers, _ = self.request("/login")
        self.assertEqual(status, "200 OK")

        status, headers, _ = self.request(
            "/login",
            method="POST",
            form_data={"username": "admin", "password": "admin123"},
        )
        self.assertEqual(status, "303 See Other")
        cookie = self.extract_cookie(headers, "session_token")
        self.assertTrue(cookie.startswith("session_token="))

        status, _, body = self.request(
            "/cash/open",
            method="POST",
            form_data={"opening_amount": "1000.00", "notes": "Abertura teste"},
            cookie=cookie,
        )
        self.assertEqual(status, "303 See Other", body.decode("utf-8", "ignore"))

        status, _, _ = self.request(
            "/customers",
            method="POST",
            form_data={
                "full_name": "Cliente Fluxo",
                "tax_number": "123",
                "phone": "900000001",
                "email": "cliente@fluxo.test",
                "address_line": "Rua Principal",
                "city": "Luanda",
            },
            cookie=cookie,
        )
        self.assertEqual(status, "303 See Other")

        status, _, _ = self.request(
            "/products/1/edit",
            method="POST",
            form_data={
                "product_name": "Agua Mineral 1.5L",
                "barcode": "",
                "category_id": "1",
                "description": "",
                "unit": "UN",
                "cost_price": "180.00",
                "sale_price": "255.00",
                "minimum_stock": "8.000",
                "is_active": "1",
            },
            cookie=cookie,
        )
        self.assertEqual(status, "303 See Other")

        status, _, _ = self.request(
            "/stock/entries",
            method="POST",
            form_data={
                "supplier_id": "",
                "notes": "Reposicao fluxo",
                "product_id": ["1"],
                "quantity": ["5"],
                "unit_cost": ["180.00"],
            },
            cookie=cookie,
        )
        self.assertEqual(status, "303 See Other")

        status, headers, _ = self.request(
            "/invoices",
            method="POST",
            form_data={
                "customer_id": "1",
                "notes": "Venda do fluxo completo",
                "discount_amount": "0.00",
                "tax_amount": "0.00",
                "initial_payment_amount": "255.00",
                "initial_payment_method": "CASH",
                "payment_reference": "",
                "product_id": ["1"],
                "quantity": ["1"],
                "unit_price": ["255.00"],
                "item_discount_amount": ["0.00"],
            },
            cookie=cookie,
        )
        self.assertEqual(status, "303 See Other")
        invoice_location = headers.get("Location", [""])[0]
        invoice_path = urlparse(invoice_location).path
        invoice_id = int(invoice_path.rstrip("/").split("/")[-1])

        status, _, body = self.request(invoice_path, cookie=cookie)
        self.assertEqual(status, "200 OK")
        self.assertIn("Venda do fluxo completo", body.decode("utf-8", "ignore"))

        status, _, body = self.request(f"/invoices/{invoice_id}/edit", cookie=cookie)
        self.assertEqual(status, "200 OK")
        self.assertIn("Editar fatura", body.decode("utf-8", "ignore"))

        status, _, _ = self.request(
            f"/invoices/{invoice_id}/edit",
            method="POST",
            form_data={
                "customer_id": "1",
                "notes": "Venda atualizada",
                "discount_amount": "0.00",
                "tax_amount": "0.00",
            },
            cookie=cookie,
        )
        self.assertEqual(status, "303 See Other")

        status, _, body = self.request(invoice_path, cookie=cookie)
        self.assertEqual(status, "200 OK")
        self.assertIn("Venda atualizada", body.decode("utf-8", "ignore"))

        status, _, body = self.request(f"/invoices/{invoice_id}/print", cookie=cookie)
        self.assertEqual(status, "200 OK")
        self.assertIn("Imprimir agora", body.decode("utf-8", "ignore"))

        status, _, _ = self.request(
            "/account/password",
            method="POST",
            form_data={
                "current_password": "admin123",
                "new_password": "novaSenha123",
                "confirm_password": "novaSenha123",
            },
            cookie=cookie,
        )
        self.assertEqual(status, "303 See Other")

        status, _, _ = self.request(
            "/cash/close",
            method="POST",
            form_data={"counted_amount": "1255.00", "notes": "Fecho teste"},
            cookie=cookie,
        )
        self.assertEqual(status, "303 See Other")

        status, headers, _ = self.request("/logout", method="POST", cookie=cookie)
        self.assertEqual(status, "303 See Other")

        status, headers, _ = self.request(
            "/login",
            method="POST",
            form_data={"username": "admin", "password": "novaSenha123"},
        )
        self.assertEqual(status, "303 See Other")

    def request(self, path, method="GET", form_data=None, cookie=""):
        body = b""
        if form_data is not None:
            body = urlencode(form_data, doseq=True).encode("utf-8")

        environ = {}
        setup_testing_defaults(environ)
        environ["REQUEST_METHOD"] = method
        environ["PATH_INFO"] = path
        environ["CONTENT_LENGTH"] = str(len(body))
        environ["wsgi.input"] = BytesIO(body)
        if body:
            environ["CONTENT_TYPE"] = "application/x-www-form-urlencoded"
        if cookie:
            environ["HTTP_COOKIE"] = cookie

        captured = {}

        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = headers

        response = b"".join(self.app(environ, start_response))
        headers = {}
        for key, value in captured["headers"]:
            headers.setdefault(key, []).append(value)
        return captured["status"], headers, response

    def extract_cookie(self, headers, name):
        for value in headers.get("Set-Cookie", []):
            if value.startswith(f"{name}="):
                return value.split(";", 1)[0]
        return ""


if __name__ == "__main__":
    unittest.main()
