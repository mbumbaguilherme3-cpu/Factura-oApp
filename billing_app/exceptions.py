"""
Custom exceptions for business logic layer.
Provides structured error handling across services.
"""


class BillingException(Exception):
    """Base exception for billing application."""
    
    def __init__(self, message: str, code: str = "UNKNOWN_ERROR", status_code: int = 500, details: dict = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self):
        return {
            "error": self.code,
            "message": self.message,
            "status_code": self.status_code,
            "details": self.details,
        }


class ValidationError(BillingException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="VALIDATION_ERROR", status_code=400, details=details)


class ResourceNotFoundError(BillingException):
    """Raised when a resource is not found."""
    
    def __init__(self, resource_type: str, resource_id: str | int):
        message = f"{resource_type} with ID {resource_id} not found"
        super().__init__(
            message,
            code="RESOURCE_NOT_FOUND",
            status_code=404,
            details={"resource_type": resource_type, "resource_id": str(resource_id)},
        )


class BusinessLogicError(BillingException):
    """Raised when business rule is violated."""
    
    def __init__(self, message: str, code: str = "BUSINESS_LOGIC_ERROR", details: dict = None):
        super().__init__(message, code=code, status_code=422, details=details)


class InsufficientStockError(BusinessLogicError):
    """Raised when stock is insufficient."""
    
    def __init__(self, product_id: int, requested: float, available: float):
        message = f"Insufficient stock for product {product_id}: requested {requested}, available {available}"
        super().__init__(
            message,
            code="INSUFFICIENT_STOCK",
            details={
                "product_id": product_id,
                "requested": requested,
                "available": available,
            },
        )


class InvoiceAlreadyPaidError(BusinessLogicError):
    """Raised when trying to modify a paid invoice."""
    
    def __init__(self, invoice_id: int):
        message = f"Invoice {invoice_id} is already paid and cannot be modified"
        super().__init__(
            message,
            code="INVOICE_ALREADY_PAID",
            details={"invoice_id": invoice_id},
        )


class InvalidDiscountError(BusinessLogicError):
    """Raised when discount exceeds allowed limit."""
    
    def __init__(self, discount: float, max_allowed: float):
        message = f"Discount {discount}% exceeds maximum allowed {max_allowed}%"
        super().__init__(
            message,
            code="INVALID_DISCOUNT",
            details={"discount": discount, "max_allowed": max_allowed},
        )


class PaymentExceedsBalanceError(BusinessLogicError):
    """Raised when payment exceeds invoice balance."""
    
    def __init__(self, payment_amount: float, balance_due: float):
        message = f"Payment {payment_amount} exceeds balance due {balance_due}"
        super().__init__(
            message,
            code="PAYMENT_EXCEEDS_BALANCE",
            details={"payment_amount": payment_amount, "balance_due": balance_due},
        )


class DatabaseError(BillingException):
    """Raised when database operation fails."""
    
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(
            message,
            code="DATABASE_ERROR",
            status_code=500,
            details={"original_error": str(original_error)} if original_error else {},
        )


class OperationNotAllowedError(BillingException):
    """Raised when operation is not allowed in current state."""
    
    def __init__(self, message: str, code: str = "OPERATION_NOT_ALLOWED"):
        super().__init__(message, code=code, status_code=409)
