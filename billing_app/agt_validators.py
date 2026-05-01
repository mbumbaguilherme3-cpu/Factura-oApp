"""
AGT Validators - Angola Tax Compliance Validation
Implements validation rules for NIF, IVA regimes, and invoice compliance
"""

import re
from typing import Tuple, Optional
from decimal import Decimal
from datetime import datetime


class NIFValidator:
    """
    NIF (Número de Identificação Fiscal) validator for Angola
    Format: XXXXXXXXXXX or XXX-XXXX-XXXX (11 digits with or without hyphens)
    
    Validation rules:
    - 11 digits total
    - First digit: 1-9 (entity type indicator)
    - Valid checksum calculation (Luhn-like algorithm)
    """
    
    NIF_PATTERN = r'^(\d{3})-?(\d{4})-?(\d{4})$'
    
    @staticmethod
    def validate_format(nif: str) -> Tuple[bool, str]:
        """
        Validate NIF format and checksum
        
        Args:
            nif: NIF string (with or without hyphens)
            
        Returns:
            Tuple: (is_valid, error_message)
        """
        # Remove hyphens and spaces
        nif_clean = nif.strip().replace('-', '').replace(' ', '')
        
        # Check length
        if len(nif_clean) != 11:
            return False, f"NIF must have 11 digits, got {len(nif_clean)}"
        
        # Check if all are digits
        if not nif_clean.isdigit():
            return False, "NIF must contain only digits (and optional hyphens)"
        
        # Check first digit (entity type: 1-9)
        first_digit = int(nif_clean[0])
        if first_digit == 0:
            return False, "First digit must be between 1-9 (indicates entity type)"
        
        # Validate checksum
        if not NIFValidator._validate_checksum(nif_clean):
            return False, "NIF checksum validation failed"
        
        return True, ""
    
    @staticmethod
    def _validate_checksum(nif: str) -> bool:
        """
        Validate NIF using checksum algorithm
        Last digit is check digit calculated from first 10 digits
        """
        try:
            # Convert digits to integers
            digits = [int(d) for d in nif]
            
            # Calculate checksum (Luhn-like algorithm for Angola)
            # Weights: 9, 8, 7, 6, 5, 4, 3, 2, 9, 8
            weights = [9, 8, 7, 6, 5, 4, 3, 2, 9, 8]
            
            total = sum(digits[i] * weights[i] for i in range(10))
            check_digit = total % 11
            
            # If check_digit is 10, it becomes 0
            if check_digit == 10:
                check_digit = 0
            
            return check_digit == digits[10]
        except (IndexError, ValueError):
            return False
    
    @staticmethod
    def get_nif_type(nif: str) -> Optional[str]:
        """
        Determine NIF type from first digit
        
        1: Natural person
        2: Company/Legal entity
        3: Foreign entity
        4-9: Special entities
        """
        try:
            nif_clean = nif.replace('-', '').replace(' ', '')
            first_digit = nif_clean[0]
            
            type_map = {
                '1': 'NATURAL_PERSON',
                '2': 'COMPANY',
                '3': 'FOREIGN_ENTITY',
                '4': 'FOREIGN_COMPANY',
                '5': 'STATE_ENTITY',
                '6': 'MUNICIPAL_ENTITY',
                '7': 'CONSULATE',
                '8': 'INTERNATIONAL_ORG',
                '9': 'OTHER'
            }
            
            return type_map.get(first_digit)
        except (IndexError, AttributeError):
            return None
    
    @staticmethod
    def format_nif(nif: str, with_hyphens: bool = True) -> str:
        """Format NIF with standard formatting"""
        nif_clean = nif.replace('-', '').replace(' ', '')
        if with_hyphens:
            return f"{nif_clean[:3]}-{nif_clean[3:7]}-{nif_clean[7:]}"
        return nif_clean


class IVAValidator:
    """
    IVA (Imposto sobre o Valor Acrescentado) validator for Angola
    Implements AGT compliance rules for tax regimes and exemption codes
    """
    
    # Valid IVA rates for Angola (2026)
    VALID_RATES = {
        Decimal('14.00'): 'GENERAL',          # Standard rate
        Decimal('0.00'):  'EXEMPT',           # Exempted (requires code)
        Decimal('0.00'):  'NOT_SUBJECT',      # Not subject (requires code)
    }
    
    # Exemption codes per SAF-T (AO) specification
    EXEMPTION_CODES = {
        'M01': {'description': 'Artigo 14 do CIVA', 'regime': 'EXEMPT'},
        'M02': {'description': 'Artigo 14.a CIVA', 'regime': 'EXEMPT'},
        'M03': {'description': 'Artigo 15 CIVA', 'regime': 'EXEMPT'},
        'M04': {'description': 'Artigo 40 CIVA', 'regime': 'EXEMPT'},
        'M05': {'description': 'Documentos do Estado', 'regime': 'NOT_SUBJECT'},
        'M06': {'description': 'Negócios sobre ouro', 'regime': 'EXEMPT'},
        'M07': {'description': 'Importação de bens', 'regime': 'NOT_SUBJECT'},
        'M08': {'description': 'Intracomunutário', 'regime': 'EXEMPT'},
        'M09': {'description': 'Exportação', 'regime': 'EXEMPT'},
    }
    
    @staticmethod
    def validate_iva_rate(rate: Decimal, regime: str, exemption_code: Optional[str] = None) -> Tuple[bool, str]:
        """
        Validate IVA rate according to regime and exemption rules
        
        Args:
            rate: IVA rate (e.g., Decimal('14.00'))
            regime: IVA regime (GENERAL, EXEMPT, NOT_SUBJECT, etc.)
            exemption_code: Exemption code (required if rate is 0)
            
        Returns:
            Tuple: (is_valid, error_message)
        """
        rate = Decimal(str(rate))
        
        # Validate rate value range
        if rate < 0 or rate > 100:
            return False, f"IVA rate must be between 0 and 100, got {rate}"
        
        # General regime must be 14% (or specific rates)
        if regime == 'GENERAL' and rate != Decimal('14.00'):
            return False, f"General regime (Regime Geral) must have 14% rate, got {rate}%"
        
        # Zero rate requires exemption code
        if rate == Decimal('0.00'):
            if not exemption_code:
                return False, "Exemption code (M01-M09) required when IVA rate is 0%"
            if exemption_code not in IVAValidator.EXEMPTION_CODES:
                return False, f"Invalid exemption code '{exemption_code}'. Valid codes: {', '.join(IVAValidator.EXEMPTION_CODES.keys())}"
        else:
            # Non-zero rates should not have exemption code
            if exemption_code:
                return False, f"Exemption code only valid for 0% rate, not {rate}%"
        
        return True, ""
    
    @staticmethod
    def get_exemption_description(code: str) -> Optional[str]:
        """Get description for exemption code"""
        return IVAValidator.EXEMPTION_CODES.get(code, {}).get('description')


class InvoiceValidator:
    """
    Invoice validation rules for AGT compliance
    Ensures immutability and regulatory requirements
    """
    
    @staticmethod
    def validate_invoice_number_format(
        invoice_number: str,
        series_prefix: str,
        series_sequence: int,
        series_year: int
    ) -> Tuple[bool, str]:
        """
        Validate invoice numbering format: PREFIX SEQUENCE/YEAR
        Example: "FT SEGUNDO2026/001"
        
        Rules:
        - Prefix: 2-3 letters (FT=Fatura, NC=Nota de Crédito, ND=Nota de Débito)
        - Sequence: 1-6 digits, leading zeros
        - Year: 4 digits, current or recent year
        """
        
        # Validate prefix
        valid_prefixes = ['FT', 'NC', 'ND', 'FA', 'FR']  # Fatura, Nota Crédito, Nota Débito, Fatura Anterior, Fatura Rascunho
        if series_prefix.upper() not in valid_prefixes:
            return False, f"Invalid invoice prefix '{series_prefix}'. Valid: {', '.join(valid_prefixes)}"
        
        # Validate sequence
        if not (1 <= series_sequence <= 999999):
            return False, f"Sequence must be 1-999999, got {series_sequence}"
        
        # Validate year (must be current or within last 5 years - for retification)
        current_year = datetime.now().year
        if not (current_year - 5 <= series_year <= current_year):
            return False, f"Year must be between {current_year - 5} and {current_year}, got {series_year}"
        
        # Format and compare with provided invoice_number
        formatted_number = f"{series_prefix} {series_sequence:06d}/{series_year}"
        if invoice_number != formatted_number:
            return False, f"Invoice number format mismatch. Expected '{formatted_number}', got '{invoice_number}'"
        
        return True, ""
    
    @staticmethod
    def validate_invoice_line_total(
        lines: list,
        expected_gross: Decimal,
        expected_iva: Decimal,
        expected_net: Decimal,
        tolerance: Decimal = Decimal('0.01')
    ) -> Tuple[bool, str]:
        """
        Validate invoice line totals match header totals
        
        Args:
            lines: List of line items with gross, iva_amount, net
            expected_gross: Expected gross total
            expected_iva: Expected IVA total
            expected_net: Expected net total
            tolerance: Decimal tolerance for rounding errors
            
        Returns:
            Tuple: (is_valid, error_message)
        """
        
        calculated_gross = sum(Decimal(str(line.get('line_gross', 0))) for line in lines)
        calculated_iva = sum(Decimal(str(line.get('iva_amount', 0))) for line in lines)
        calculated_net = sum(Decimal(str(line.get('line_net', 0))) for line in lines)
        
        expected_gross = Decimal(str(expected_gross))
        expected_iva = Decimal(str(expected_iva))
        expected_net = Decimal(str(expected_net))
        
        # Check gross total
        if abs(calculated_gross - expected_gross) > tolerance:
            return False, f"Gross total mismatch: calculated {calculated_gross}, expected {expected_gross}"
        
        # Check IVA total
        if abs(calculated_iva - expected_iva) > tolerance:
            return False, f"IVA total mismatch: calculated {calculated_iva}, expected {expected_iva}"
        
        # Check net total (gross - iva)
        calculated_net_check = calculated_gross - calculated_iva
        if abs(calculated_net_check - expected_net) > tolerance:
            return False, f"Net total mismatch: calculated {calculated_net_check}, expected {expected_net}"
        
        return True, ""
    
    @staticmethod
    def validate_invoice_immutability(
        invoice_data: dict,
        is_issued: bool,
        is_editable: bool
    ) -> Tuple[bool, str]:
        """
        Validate invoice immutability rules
        
        Rules:
        - After issue, invoice cannot be edited (must be cancelled and corrected)
        - Invoice number cannot change after issue
        - Dates cannot change after issue
        - Lines cannot be modified after issue
        """
        
        if is_issued and is_editable:
            return False, "Invoice marked as issued but still editable. State inconsistency."
        
        if is_issued and not is_editable:
            return True, ""  # Valid - issued and locked
        
        if not is_issued and is_editable:
            return True, ""  # Valid - draft state
        
        return False, "Invalid invoice state combination"
    
    @staticmethod
    def validate_invoice_for_issue(invoice_data: dict) -> Tuple[bool, str]:
        """
        Validate invoice before issuing (locking for immutability)
        
        Requirements:
        - Has customer
        - Has at least one line
        - All lines have valid IVA configuration
        - Totals are calculated
        - No draft state requirements
        """
        
        checks = [
            ('customer_id', "Invoice must have a customer"),
            ('supplier_id', "Invoice must have a supplier"),
            ('lines', "Invoice must have at least one line"),
            ('invoice_number', "Invoice number must be assigned"),
            ('gross_total', "Invoice totals must be calculated"),
        ]
        
        for field, error_msg in checks:
            if not invoice_data.get(field):
                return False, error_msg
        
        # Validate lines
        lines = invoice_data.get('lines', [])
        if not lines:
            return False, "Invoice must have at least one line"
        
        for i, line in enumerate(lines, 1):
            if not line.get('iva_regime'):
                return False, f"Line {i} missing IVA regime"
            if line.get('iva_rate') == 0 and not line.get('iva_exemption_code'):
                return False, f"Line {i} has 0% IVA but no exemption code"
        
        return True, ""


class ComplianceRuleEngine:
    """
    AGT compliance rule engine
    Enforces regulatory constraints at application level
    """
    
    @staticmethod
    def can_edit_invoice(invoice_status: str, is_issued: bool) -> bool:
        """Determine if invoice can be edited based on status"""
        # Can only edit if not issued
        return not is_issued
    
    @staticmethod
    def can_delete_invoice(invoice_status: str, is_issued: bool) -> bool:
        """
        Can only delete invoices that are still in draft (not issued)
        Once issued, must be cancelled instead
        """
        return not is_issued
    
    @staticmethod
    def can_cancel_invoice(invoice_status: str, is_issued: bool) -> bool:
        """Can cancel any issued invoice"""
        return is_issued
    
    @staticmethod
    def require_signature_before_submit(signature_status: str) -> bool:
        """Invoice must be signed before submitting to AGT"""
        return signature_status == 'S'  # SIGNED
    
    @staticmethod
    def validate_business_rule_invoice_sequence(
        previous_invoice_date: Optional[datetime],
        current_invoice_date: datetime
    ) -> Tuple[bool, str]:
        """
        Invoices must be issued in chronological order (per AGT requirement)
        This ensures audit trail integrity
        """
        if previous_invoice_date and current_invoice_date < previous_invoice_date:
            return False, "Invoice date must be after previous invoice date (chronological order required)"
        return True, ""


__all__ = [
    'NIFValidator',
    'IVAValidator',
    'InvoiceValidator',
    'ComplianceRuleEngine',
]
