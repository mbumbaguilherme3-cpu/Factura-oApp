"""
AGT Validators Tests
Testa validação de NIF, IVA, Faturas e Conformidade
"""

import pytest
from decimal import Decimal

from billing_app.agt_validators import (
    NIFValidator, IVAValidator, InvoiceValidator, ComplianceRuleEngine
)


class TestNIFValidator:
    """Test NIF validation"""
    
    def test_valid_nif_format(self):
        """Test valid NIF format"""
        is_valid, error = NIFValidator.validate_format("123-4567-8901")
        assert is_valid
        assert error is None
    
    def test_invalid_nif_too_short(self):
        """Test NIF with too few digits"""
        is_valid, error = NIFValidator.validate_format("123-4567-890")
        assert not is_valid
        assert error is not None
    
    def test_invalid_nif_bad_checksum(self):
        """Test NIF with invalid checksum"""
        is_valid, error = NIFValidator.validate_format("123-4567-8902")
        assert not is_valid
    
    def test_nif_type_detection_person(self):
        """Test NIF type detection for natural person"""
        nif_type = NIFValidator.get_nif_type("123-4567-8901")
        assert nif_type == "PERSON"
    
    def test_nif_type_detection_company(self):
        """Test NIF type detection for company"""
        nif_type = NIFValidator.get_nif_type("234-5678-9012")
        assert nif_type == "COMPANY"
    
    def test_nif_format_with_hyphens(self):
        """Test NIF formatting with hyphens"""
        formatted = NIFValidator.format_nif("12345678901", with_hyphens=True)
        assert formatted == "123-4567-8901"
    
    def test_nif_format_without_hyphens(self):
        """Test NIF formatting without hyphens"""
        formatted = NIFValidator.format_nif("12345678901", with_hyphens=False)
        assert formatted == "12345678901"


class TestIVAValidator:
    """Test IVA validation"""
    
    def test_general_regime_valid_rate(self):
        """Test general regime with 14% rate"""
        is_valid, error = IVAValidator.validate_iva_rate(
            rate=Decimal('14.00'),
            regime='GENERAL'
        )
        assert is_valid
    
    def test_general_regime_invalid_rate(self):
        """Test general regime with wrong rate"""
        is_valid, error = IVAValidator.validate_iva_rate(
            rate=Decimal('10.00'),
            regime='GENERAL'
        )
        assert not is_valid
    
    def test_exempt_regime_requires_code(self):
        """Test exempt regime requires exemption code"""
        is_valid, error = IVAValidator.validate_iva_rate(
            rate=Decimal('0.00'),
            regime='EXEMPT',
            exemption_code=None
        )
        assert not is_valid
    
    def test_exempt_regime_with_valid_code(self):
        """Test exempt regime with valid code"""
        is_valid, error = IVAValidator.validate_iva_rate(
            rate=Decimal('0.00'),
            regime='EXEMPT',
            exemption_code='M01'
        )
        assert is_valid
    
    def test_exemption_code_description(self):
        """Test getting exemption code description"""
        desc = IVAValidator.get_exemption_description('M01')
        assert 'Artigo 14' in desc or desc == 'Artigo 14 do CIVA'
    
    def test_invalid_exemption_code(self):
        """Test invalid exemption code"""
        desc = IVAValidator.get_exemption_description('INVALID')
        assert desc is None


class TestInvoiceValidator:
    """Test invoice validation"""
    
    def test_valid_invoice_number_format(self):
        """Test valid invoice number format"""
        is_valid, error = InvoiceValidator.validate_invoice_number_format(
            invoice_number="FT SEGUNDO2026/0001",
            series_prefix="FT",
            series_sequence=1,
            series_year=2026
        )
        assert is_valid
    
    def test_invalid_invoice_prefix(self):
        """Test invalid invoice prefix"""
        is_valid, error = InvoiceValidator.validate_invoice_number_format(
            invoice_number="XX SEGUNDO2026/0001",
            series_prefix="XX",
            series_sequence=1,
            series_year=2026
        )
        assert not is_valid
    
    def test_valid_nc_prefix(self):
        """Test valid NC (credit note) prefix"""
        is_valid, error = InvoiceValidator.validate_invoice_number_format(
            invoice_number="NC SEGUNDO2026/0001",
            series_prefix="NC",
            series_sequence=1,
            series_year=2026
        )
        assert is_valid
    
    def test_valid_nd_prefix(self):
        """Test valid ND (debit note) prefix"""
        is_valid, error = InvoiceValidator.validate_invoice_number_format(
            invoice_number="ND SEGUNDO2026/0001",
            series_prefix="ND",
            series_sequence=1,
            series_year=2026
        )
        assert is_valid
    
    def test_invoice_sequence_range(self):
        """Test invoice sequence within valid range"""
        is_valid, error = InvoiceValidator.validate_invoice_number_format(
            invoice_number="FT SEGUNDO2026/999999",
            series_prefix="FT",
            series_sequence=999999,
            series_year=2026
        )
        assert is_valid
    
    def test_invoice_sequence_out_of_range(self):
        """Test invoice sequence out of range"""
        is_valid, error = InvoiceValidator.validate_invoice_number_format(
            invoice_number="FT SEGUNDO2026/1000000",
            series_prefix="FT",
            series_sequence=1000000,
            series_year=2026
        )
        assert not is_valid
    
    def test_invoice_line_total_validation_valid(self):
        """Test invoice line totals validation with valid amounts"""
        lines = [
            {'line_gross': Decimal('100.00'), 'iva_amount': Decimal('14.00')},
            {'line_gross': Decimal('200.00'), 'iva_amount': Decimal('28.00')}
        ]
        is_valid, error = InvoiceValidator.validate_invoice_line_total(
            lines,
            expected_gross=Decimal('300.00'),
            expected_iva=Decimal('42.00'),
            expected_net=Decimal('258.00')
        )
        assert is_valid
    
    def test_invoice_line_total_validation_invalid(self):
        """Test invoice line totals validation with invalid amounts"""
        lines = [
            {'line_gross': Decimal('100.00'), 'iva_amount': Decimal('14.00')}
        ]
        is_valid, error = InvoiceValidator.validate_invoice_line_total(
            lines,
            expected_gross=Decimal('500.00'),  # Wrong amount
            expected_iva=Decimal('70.00'),
            expected_net=Decimal('430.00')
        )
        assert not is_valid


class TestComplianceRuleEngine:
    """Test compliance rule enforcement"""
    
    def test_can_edit_draft_invoice(self):
        """Test editing DRAFT invoice is allowed"""
        can_edit, reason = ComplianceRuleEngine.can_edit_invoice(
            status='D',
            is_issued=False
        )
        assert can_edit
    
    def test_cannot_edit_issued_invoice(self):
        """Test editing ISSUED invoice is not allowed"""
        can_edit, reason = ComplianceRuleEngine.can_edit_invoice(
            status='I',
            is_issued=True
        )
        assert not can_edit
        assert reason is not None
    
    def test_can_delete_draft_invoice(self):
        """Test deleting DRAFT invoice is allowed"""
        can_delete, reason = ComplianceRuleEngine.can_delete_invoice(
            status='D',
            is_issued=False
        )
        assert can_delete
    
    def test_cannot_delete_issued_invoice(self):
        """Test deleting ISSUED invoice is not allowed"""
        can_delete, reason = ComplianceRuleEngine.can_delete_invoice(
            status='I',
            is_issued=True
        )
        assert not can_delete
        assert reason is not None
    
    def test_chronological_ordering_valid(self):
        """Test chronological ordering validation - valid"""
        from datetime import datetime, timedelta
        
        invoice_date = datetime(2026, 5, 3, 10, 0)
        last_invoice_date = datetime(2026, 5, 3, 9, 0)
        
        is_valid, error = ComplianceRuleEngine.enforce_chronological_order(
            invoice_date,
            last_invoice_date,
            'FT'
        )
        assert is_valid
    
    def test_chronological_ordering_invalid_backdate(self):
        """Test chronological ordering validation - invalid backdate"""
        from datetime import datetime
        
        invoice_date = datetime(2026, 5, 2, 10, 0)  # Earlier
        last_invoice_date = datetime(2026, 5, 3, 9, 0)  # Later
        
        is_valid, error = ComplianceRuleEngine.enforce_chronological_order(
            invoice_date,
            last_invoice_date,
            'FT'
        )
        assert not is_valid
