"""
Invoice Immutability Engine - AGT Compliance
Enforces mandatory immutability of invoices after issue
Implements audit trail and integrity checking
"""

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, Tuple, Optional, Any
from enum import Enum


class ImmutabilityViolation(Exception):
    """Raised when attempting to modify an immutable invoice"""
    pass


class InvoiceImmutabilityEngine:
    """
    Implements immutability enforcement for AGT-compliant invoices
    
    Key Principles:
    1. Once invoice number is assigned (e.g., FT SEGUNDO2026/001), invoice is locked
    2. No fields can be modified after lock
    3. Corrections require issuing a credit note (Nota de Crédito)
    4. All operations are logged for audit trail
    """
    
    @staticmethod
    def calculate_invoice_hash(invoice_data: Dict[str, Any]) -> str:
        """
        Calculate SHA256 hash of invoice data for integrity verification
        
        Includes:
        - Basic invoice info (numbers, dates, totals)
        - All line items
        - Customer/Supplier IDs
        
        Excludes:
        - Signature fields
        - Timestamps
        - Audit log references
        """
        
        # Create canonical representation for hashing
        canonical_data = {
            'invoice_number': invoice_data.get('invoice_number'),
            'supplier_id': invoice_data.get('supplier_id'),
            'customer_id': invoice_data.get('customer_id'),
            'invoice_date': str(invoice_data.get('invoice_date')),
            'gross_total': str(invoice_data.get('gross_total')),
            'iva_total': str(invoice_data.get('iva_total')),
            'net_total': str(invoice_data.get('net_total')),
            'lines': []
        }
        
        # Include all line items in deterministic order
        for line in sorted(invoice_data.get('lines', []), key=lambda x: x.get('line_number', 0)):
            canonical_data['lines'].append({
                'line_number': line.get('line_number'),
                'product_id': line.get('product_id'),
                'description': line.get('description'),
                'unit_price': str(line.get('unit_price')),
                'quantity': str(line.get('quantity')),
                'line_gross': str(line.get('line_gross')),
                'iva_rate': str(line.get('iva_rate')),
                'iva_amount': str(line.get('iva_amount')),
                'line_net': str(line.get('line_net')),
            })
        
        # Create JSON string and hash
        json_str = json.dumps(canonical_data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    @staticmethod
    def lock_invoice(
        invoice_data: Dict[str, Any],
        operator_id: str
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Lock invoice after issue - make it immutable
        
        Args:
            invoice_data: Invoice data dictionary
            operator_id: ID of operator performing the lock
            
        Returns:
            Tuple: (hash, updated_invoice_data)
            
        Raises:
            ImmutabilityViolation: If invoice cannot be locked
        """
        
        # Verify invoice can be locked (in issued state)
        if invoice_data.get('is_issued'):
            if invoice_data.get('is_editable'):
                # Need to transition from issued to locked
                pass
            else:
                raise ImmutabilityViolation("Invoice is already locked")
        else:
            raise ImmutabilityViolation("Cannot lock invoice that is not yet issued")
        
        # Calculate hash before locking
        data_hash = InvoiceImmutabilityEngine.calculate_invoice_hash(invoice_data)
        
        # Update invoice state
        locked_invoice = invoice_data.copy()
        locked_invoice.update({
            'is_editable': False,
            'locked_at': datetime.utcnow().isoformat(),
            'data_hash_before_issue': data_hash,
        })
        
        return data_hash, locked_invoice
    
    @staticmethod
    def verify_invoice_integrity(
        invoice_data: Dict[str, Any],
        stored_hash: str
    ) -> bool:
        """
        Verify invoice has not been tampered with
        
        Args:
            invoice_data: Current invoice data
            stored_hash: Previously calculated hash
            
        Returns:
            bool: True if hash matches (data is intact)
        """
        
        calculated_hash = InvoiceImmutabilityEngine.calculate_invoice_hash(invoice_data)
        return calculated_hash == stored_hash
    
    @staticmethod
    def prevent_modification(
        invoice_data: Dict[str, Any],
        operation: str,
        allowed_statuses: list = None
    ) -> Tuple[bool, str]:
        """
        Check if modification is allowed based on invoice state
        
        Args:
            invoice_data: Invoice to check
            operation: Type of operation (CREATE, EDIT, DELETE, CANCEL)
            allowed_statuses: Statuses that permit operation
            
        Returns:
            Tuple: (is_allowed, reason)
        """
        
        is_editable = invoice_data.get('is_editable', True)
        is_issued = invoice_data.get('is_issued', False)
        status = invoice_data.get('status', 'D')
        
        # Default allowed statuses per operation
        default_allowed = {
            'CREATE': True,  # Always allowed for new invoices
            'EDIT': not is_issued,  # Only before issue
            'DELETE': not is_issued,  # Only before issue (soft delete)
            'CANCEL': is_issued,  # Only after issue
            'SUBMIT': is_issued,  # Only issued invoices
            'SIGN': is_issued,  # Only issued invoices
        }
        
        if allowed_statuses is None:
            is_allowed = default_allowed.get(operation, False)
        else:
            is_allowed = status in allowed_statuses
        
        if not is_allowed:
            reason = f"Operation '{operation}' not allowed for invoice in status '{status}' (is_issued={is_issued}, is_editable={is_editable})"
            return False, reason
        
        return True, ""
    
    @staticmethod
    def enforce_chronological_order(
        invoice_date: datetime,
        last_invoice_date: Optional[datetime],
        invoice_series: str
    ) -> Tuple[bool, str]:
        """
        Enforce chronological ordering of invoices per AGT requirement
        
        Rule: Invoices must be issued in chronological order within same series
        This prevents backdating and ensures audit trail integrity
        
        Args:
            invoice_date: Date of current invoice
            last_invoice_date: Date of previous invoice in series
            invoice_series: Invoice series identifier
            
        Returns:
            Tuple: (is_valid, reason)
        """
        
        if last_invoice_date and invoice_date < last_invoice_date:
            return False, (
                f"Invoice date ({invoice_date.date()}) must be >= previous invoice date "
                f"({last_invoice_date.date()}) in series '{invoice_series}'"
            )
        
        return True, ""


class InvoiceCorrectionStrategy:
    """
    Implements correction strategies for invoices after issue
    Per AGT rules, modifications are done via credit/debit notes
    """
    
    @staticmethod
    def create_credit_note(
        original_invoice: Dict[str, Any],
        reason: str,
        operator_id: str
    ) -> Dict[str, Any]:
        """
        Create credit note (Nota de Crédito) to correct original invoice
        
        Args:
            original_invoice: Original invoice to correct
            reason: Reason for correction
            operator_id: Operator performing correction
            
        Returns:
            Credit note invoice structure
        """
        
        if not original_invoice.get('is_issued'):
            raise ImmutabilityViolation("Can only create credit note for issued invoices")
        
        credit_note = {
            'series_prefix': 'NC',  # Nota de Crédito
            'series_sequence': None,  # Will be auto-assigned
            'series_year': datetime.utcnow().year,
            'supplier_id': original_invoice.get('supplier_id'),
            'customer_id': original_invoice.get('customer_id'),
            'invoice_date': datetime.utcnow(),
            'due_date': None,
            'gross_total': -abs(Decimal(str(original_invoice.get('gross_total', 0)))),
            'iva_total': -abs(Decimal(str(original_invoice.get('iva_total', 0)))),
            'net_total': -abs(Decimal(str(original_invoice.get('net_total', 0)))),
            'description': f"Credit note for {original_invoice.get('invoice_number')}: {reason}",
            'lines': [],
            'reference_invoice_id': original_invoice.get('invoice_id'),
            'reference_invoice_number': original_invoice.get('invoice_number'),
            'correction_reason': reason,
            'operator_id': operator_id,
            'status': 'D',  # Draft
            'is_issued': False,
            'is_editable': True,
        }
        
        # Create inverse line items
        for original_line in original_invoice.get('lines', []):
            credit_line = {
                'description': original_line.get('description'),
                'unit_price': original_line.get('unit_price'),
                'quantity': -abs(Decimal(str(original_line.get('quantity', 0)))),
                'line_gross': -abs(Decimal(str(original_line.get('line_gross', 0)))),
                'iva_rate': original_line.get('iva_rate'),
                'iva_amount': -abs(Decimal(str(original_line.get('iva_amount', 0)))),
                'line_net': -abs(Decimal(str(original_line.get('line_net', 0)))),
                'iva_regime': original_line.get('iva_regime'),
                'iva_exemption_code': original_line.get('iva_exemption_code'),
            }
            credit_note['lines'].append(credit_line)
        
        return credit_note
    
    @staticmethod
    def create_debit_note(
        original_invoice: Dict[str, Any],
        reason: str,
        correction_amount: Decimal,
        operator_id: str
    ) -> Dict[str, Any]:
        """
        Create debit note (Nota de Débito) for additional charges
        
        Args:
            original_invoice: Original invoice
            reason: Reason for additional charge
            correction_amount: Amount of correction
            operator_id: Operator performing correction
            
        Returns:
            Debit note invoice structure
        """
        
        if not original_invoice.get('is_issued'):
            raise ImmutabilityViolation("Can only create debit note for issued invoices")
        
        correction_amount = Decimal(str(correction_amount))
        
        # Calculate IVA on correction amount (assume general regime 14%)
        iva_rate = Decimal('0.14')
        iva_amount = correction_amount * iva_rate
        net_amount = correction_amount - iva_amount
        
        debit_note = {
            'series_prefix': 'ND',  # Nota de Débito
            'series_sequence': None,  # Will be auto-assigned
            'series_year': datetime.utcnow().year,
            'supplier_id': original_invoice.get('supplier_id'),
            'customer_id': original_invoice.get('customer_id'),
            'invoice_date': datetime.utcnow(),
            'due_date': None,
            'gross_total': correction_amount,
            'iva_total': iva_amount,
            'net_total': net_amount,
            'description': f"Debit note for {original_invoice.get('invoice_number')}: {reason}",
            'lines': [{
                'description': reason,
                'unit_price': correction_amount,
                'quantity': Decimal('1'),
                'line_gross': correction_amount,
                'iva_rate': iva_rate * 100,
                'iva_amount': iva_amount,
                'line_net': net_amount,
                'iva_regime': 'GENERAL',
                'iva_exemption_code': None,
            }],
            'reference_invoice_id': original_invoice.get('invoice_id'),
            'reference_invoice_number': original_invoice.get('invoice_number'),
            'correction_reason': reason,
            'operator_id': operator_id,
            'status': 'D',  # Draft
            'is_issued': False,
            'is_editable': True,
        }
        
        return debit_note


class InvoiceStateTransition:
    """State machine for invoice lifecycle"""
    
    # Valid state transitions
    TRANSITIONS = {
        'D': ['I', 'X'],  # Draft -> Issued or Cancelled
        'I': ['C', 'S', 'T', 'X'],  # Issued -> Cancelled, Submitted, Retified, or Cancelled
        'C': [],  # Cancelled - terminal state
        'S': ['A', 'R', 'X'],  # Submitted -> Acknowledged, Rejected, or Cancelled
        'A': ['X'],  # Acknowledged -> Cancelled
        'R': ['S', 'X'],  # Rejected -> Resubmit or Cancel
        'T': ['S', 'X'],  # Retified -> Resubmit or Cancel
        'X': [],  # Cancelled - terminal state
    }
    
    @staticmethod
    def is_valid_transition(from_status: str, to_status: str) -> bool:
        """Check if transition is allowed"""
        allowed = InvoiceStateTransition.TRANSITIONS.get(from_status, [])
        return to_status in allowed
    
    @staticmethod
    def get_allowed_transitions(current_status: str) -> list:
        """Get list of allowed next states"""
        return InvoiceStateTransition.TRANSITIONS.get(current_status, [])


__all__ = [
    'ImmutabilityViolation',
    'InvoiceImmutabilityEngine',
    'InvoiceCorrectionStrategy',
    'InvoiceStateTransition',
]
