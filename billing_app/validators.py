"""
Input validators for business layer.
Validates data before processing by services.
"""

import re
from typing import Any, List, Optional
from decimal import Decimal
from datetime import datetime

from billing_app.exceptions import ValidationError


class Validator:
    """Base validator class."""
    
    @staticmethod
    def validate_required(value: Any, field_name: str) -> Any:
        """Validate that value is not None or empty."""
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValidationError(f"{field_name} is required")
        return value
    
    @staticmethod
    def validate_email(email: str) -> str:
        """Validate email format."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, email):
            raise ValidationError(f"Invalid email format: {email}")
        return email
    
    @staticmethod
    def validate_phone(phone: str) -> str:
        """Validate phone format (basic: +244 format or local)."""
        # Allow: +244XXXXXXXXX, (244) XXXXXXXXX, or 9XXXXXXXX
        pattern = r"^(\+244|0|9)\d{8,9}$|^\+\d{1,3}\d{8,}$"
        if not re.match(pattern, phone.replace(" ", "").replace("-", "")):
            raise ValidationError(f"Invalid phone format: {phone}")
        return phone
    
    @staticmethod
    def validate_positive_number(value: float | int, field_name: str, allow_zero: bool = False) -> float:
        """Validate positive number."""
        if not isinstance(value, (int, float, Decimal)):
            raise ValidationError(f"{field_name} must be a number")
        
        if value < 0 or (value == 0 and not allow_zero):
            raise ValidationError(f"{field_name} must be greater than 0")
        
        return float(value)
    
    @staticmethod
    def validate_percentage(value: float, field_name: str, max_value: float = 100) -> float:
        """Validate percentage value (0-100)."""
        if not isinstance(value, (int, float, Decimal)):
            raise ValidationError(f"{field_name} must be a number")
        
        if value < 0 or value > max_value:
            raise ValidationError(f"{field_name} must be between 0 and {max_value}")
        
        return float(value)
    
    @staticmethod
    def validate_string_length(value: str, field_name: str, min_len: int = 1, max_len: int = 255) -> str:
        """Validate string length."""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")
        
        if len(value) < min_len or len(value) > max_len:
            raise ValidationError(f"{field_name} length must be between {min_len} and {max_len}")
        
        return value
    
    @staticmethod
    def validate_choice(value: str, choices: List[str], field_name: str) -> str:
        """Validate value is in allowed choices."""
        if value not in choices:
            raise ValidationError(f"{field_name} must be one of: {', '.join(choices)}")
        return value
    
    @staticmethod
    def validate_date(date_str: str, format: str = "%Y-%m-%d") -> datetime:
        """Validate date string."""
        try:
            return datetime.strptime(date_str, format)
        except ValueError:
            raise ValidationError(f"Invalid date format. Expected {format}")


class InvoiceValidator:
    """Validators for invoice operations."""
    
    @staticmethod
    def validate_create_invoice(customer_id: int, items: List[dict], discount_amount: float = 0):
        """Validate invoice creation input."""
        # Validate customer_id
        Validator.validate_required(customer_id, "customer_id")
        if not isinstance(customer_id, int) or customer_id <= 0:
            raise ValidationError("customer_id must be a positive integer")
        
        # Validate items
        Validator.validate_required(items, "items")
        if not isinstance(items, list) or len(items) == 0:
            raise ValidationError("items must be a non-empty list")
        
        for i, item in enumerate(items):
            InvoiceValidator._validate_invoice_item(item, i)
        
        # Validate discount
        Validator.validate_percentage(discount_amount, "discount_amount", max_value=50)
        
        return True
    
    @staticmethod
    def _validate_invoice_item(item: dict, index: int):
        """Validate single invoice item."""
        try:
            product_id = item.get("product_id")
            quantity = item.get("quantity")
            unit_price = item.get("unit_price")
            
            if not product_id:
                raise ValidationError(f"Item {index}: product_id is required")
            if not isinstance(product_id, int) or product_id <= 0:
                raise ValidationError(f"Item {index}: product_id must be positive integer")
            
            Validator.validate_positive_number(quantity, f"Item {index}: quantity")
            Validator.validate_positive_number(unit_price, f"Item {index}: unit_price", allow_zero=False)
        
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Item {index}: Invalid format - {str(e)}")


class PaymentValidator:
    """Validators for payment operations."""
    
    @staticmethod
    def validate_apply_payment(invoice_id: int, amount: float, payment_method: str):
        """Validate payment application."""
        if not isinstance(invoice_id, int) or invoice_id <= 0:
            raise ValidationError("invoice_id must be a positive integer")
        
        Validator.validate_positive_number(amount, "amount", allow_zero=False)
        
        valid_methods = ["CASH", "CARD", "TRANSFER", "MOBILE", "OTHER"]
        Validator.validate_choice(payment_method, valid_methods, "payment_method")
        
        return True


class StockValidator:
    """Validators for stock operations."""
    
    @staticmethod
    def validate_stock_entry(supplier_id: Optional[int], items: List[dict]):
        """Validate stock entry."""
        if supplier_id is not None and (not isinstance(supplier_id, int) or supplier_id <= 0):
            raise ValidationError("supplier_id must be a positive integer")
        
        Validator.validate_required(items, "items")
        if not isinstance(items, list) or len(items) == 0:
            raise ValidationError("items must be a non-empty list")
        
        for i, item in enumerate(items):
            StockValidator._validate_stock_item(item, i)
        
        return True
    
    @staticmethod
    def _validate_stock_item(item: dict, index: int):
        """Validate single stock item."""
        try:
            product_id = item.get("product_id")
            quantity = item.get("quantity")
            unit_cost = item.get("unit_cost")
            
            if not product_id:
                raise ValidationError(f"Item {index}: product_id is required")
            if not isinstance(product_id, int) or product_id <= 0:
                raise ValidationError(f"Item {index}: product_id must be positive integer")
            
            Validator.validate_positive_number(quantity, f"Item {index}: quantity")
            Validator.validate_positive_number(unit_cost, f"Item {index}: unit_cost", allow_zero=False)
        
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Item {index}: Invalid format - {str(e)}")


class CustomerValidator:
    """Validators for customer operations."""
    
    @staticmethod
    def validate_create_customer(full_name: str, phone: str, email: Optional[str] = None):
        """Validate customer creation."""
        Validator.validate_string_length(full_name, "full_name", min_len=3, max_len=150)
        Validator.validate_phone(phone)
        
        if email:
            Validator.validate_email(email)
        
        return True
