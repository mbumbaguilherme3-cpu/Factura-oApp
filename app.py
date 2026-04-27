from billing_app.database import DEFAULT_DB_PATH, initialize_database
from billing_app.web import BillingApplication, serve


if __name__ == "__main__":
    initialize_database(DEFAULT_DB_PATH)
    serve(BillingApplication(DEFAULT_DB_PATH))
