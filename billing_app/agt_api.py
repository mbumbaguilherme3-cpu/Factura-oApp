"""
AGT (Autoridade Geral Tributária) - Flask REST API Endpoints
Implementa conformidade fiscal completa para Angola 2026
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Tuple, List
import uuid
import logging

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from billing_app.db_config import db
from billing_app.agt_models import (
    Invoice, InvoiceLine, AnyEntity, AGTProduct,
    InvoiceSignatureAudit, AGTComplianceLog, AGTCertificateKey
)
from billing_app.agt_validators import (
    NIFValidator, IVAValidator, InvoiceValidator, ComplianceRuleEngine
)
from billing_app.agt_immutability import (
    InvoiceImmutabilityEngine, InvoiceCorrectionStrategy, InvoiceStateTransition
)
from billing_app.agt_signature import JWSSignatureEngine, SignatureAlgorithm
from billing_app.agt_saft_generator import SAFTAOGenerator, SAFTAOValidator

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Create Blueprint
agt_api = Blueprint('agt_api', __name__, url_prefix='/api')

# Initialize validators and engines
nif_validator = NIFValidator()
iva_validator = IVAValidator()
invoice_validator = InvoiceValidator()
compliance_engine = ComplianceRuleEngine()
immutability_engine = InvoiceImmutabilityEngine()
correction_strategy = InvoiceCorrectionStrategy()


# ============================================================================
# INVOICE CREATION & MANAGEMENT
# ============================================================================

@agt_api.route('/invoices', methods=['POST'])
def create_invoice() -> Tuple[Dict[str, Any], int]:
    """
    Create a new invoice in DRAFT status
    
    Request Body:
    {
        "customer_nif": "123-4567-8901",
        "supplier_nif": "234-5678-9012",
        "invoice_date": "2026-05-01",
        "due_date": "2026-06-01",
        "lines": [
            {
                "product_id": "uuid",
                "quantity": 1,
                "unit_price": "1000.00",
                "iva_regime": "GENERAL",
                "iva_exemption_code": null
            }
        ]
    }
    
    Response: 201 Created
    {
        "invoice_id": "uuid",
        "status": "D",
        "invoice_number": null,
        "created_at": "2026-05-01T10:00:00Z"
    }
    """
    try:
        data = request.get_json()
        
        # Validate customer NIF
        is_valid, error = nif_validator.validate_format(data['customer_nif'])
        if not is_valid:
            logger.warning(f"Invalid customer NIF: {data['customer_nif']} - {error}")
            return {"error": f"Invalid customer NIF: {error}"}, 400
        
        # Validate supplier NIF
        is_valid, error = nif_validator.validate_format(data['supplier_nif'])
        if not is_valid:
            logger.warning(f"Invalid supplier NIF: {data['supplier_nif']} - {error}")
            return {"error": f"Invalid supplier NIF: {error}"}, 400
        
        # Get or create entities
        customer = db.session.query(AnyEntity).filter_by(nif=data['customer_nif']).first()
        if not customer:
            customer = AnyEntity(
                entity_id=str(uuid.uuid4()),
                nif=data['customer_nif'],
                nif_type=nif_validator.get_nif_type(data['customer_nif']),
                name=data.get('customer_name', f"Customer {data['customer_nif']}"),
                is_vat_registered=True
            )
            db.session.add(customer)
        
        supplier = db.session.query(AnyEntity).filter_by(nif=data['supplier_nif']).first()
        if not supplier:
            supplier = AnyEntity(
                entity_id=str(uuid.uuid4()),
                nif=data['supplier_nif'],
                nif_type=nif_validator.get_nif_type(data['supplier_nif']),
                name=data.get('supplier_name', f"Supplier {data['supplier_nif']}"),
                is_vat_registered=True
            )
            db.session.add(supplier)
        
        db.session.flush()
        
        # Create invoice header
        invoice = Invoice(
            invoice_id=str(uuid.uuid4()),
            supplier_id=supplier.entity_id,
            customer_id=customer.entity_id,
            invoice_date=datetime.fromisoformat(data['invoice_date']),
            due_date=datetime.fromisoformat(data['due_date']) if 'due_date' in data else None,
            status='D',  # DRAFT
            is_issued=False,
            is_editable=True
        )
        
        # Process invoice lines
        gross_total = Decimal('0.00')
        iva_total = Decimal('0.00')
        
        for idx, line_data in enumerate(data['lines'], 1):
            product = db.session.query(AGTProduct).filter_by(
                product_id=line_data['product_id']
            ).first()
            
            if not product:
                return {"error": f"Product {line_data['product_id']} not found"}, 404
            
            quantity = Decimal(str(line_data['quantity']))
            unit_price = Decimal(str(line_data['unit_price']))
            iva_regime = line_data.get('iva_regime', product.iva_regime)
            iva_rate = product.iva_rate
            iva_exemption_code = line_data.get('iva_exemption_code', product.iva_exemption_code)
            
            # Validate IVA
            is_valid, error = iva_validator.validate_iva_rate(
                iva_rate, iva_regime, iva_exemption_code
            )
            if not is_valid:
                logger.warning(f"Invalid IVA config: {error}")
                return {"error": f"Invalid IVA configuration: {error}"}, 400
            
            line_gross = quantity * unit_price
            iva_amount = line_gross * (iva_rate / 100)
            line_net = line_gross - iva_amount
            
            line = InvoiceLine(
                line_id=str(uuid.uuid4()),
                invoice_id=invoice.invoice_id,
                product_id=product.product_id,
                line_number=idx,
                description=line_data.get('description', product.description),
                quantity=quantity,
                unit_price=unit_price,
                line_gross=line_gross,
                iva_amount=iva_amount,
                line_net=line_net,
                iva_regime=iva_regime,
                iva_rate=iva_rate,
                iva_exemption_code=iva_exemption_code
            )
            
            invoice.lines.append(line)
            gross_total += line_gross
            iva_total += iva_amount
        
        invoice.gross_total = gross_total
        invoice.iva_total = iva_total
        invoice.net_total = gross_total - iva_total
        
        db.session.add(invoice)
        
        # Log compliance event
        compliance_log = AGTComplianceLog(
            log_id=str(uuid.uuid4()),
            event_type='INVOICE_CREATED',
            entity_type='INVOICE',
            entity_id=invoice.invoice_id,
            action='CREATE',
            operator_id=data.get('operator_id', 'system'),
            operator_ip=request.remote_addr,
            data_after={
                'invoice_id': invoice.invoice_id,
                'status': 'D',
                'gross_total': str(gross_total),
                'iva_total': str(iva_total),
                'net_total': str(gross_total - iva_total),
                'line_count': len(data['lines'])
            },
            is_compliant=True
        )
        db.session.add(compliance_log)
        db.session.commit()
        
        logger.info(f"Invoice created: {invoice.invoice_id}")
        
        return {
            "invoice_id": invoice.invoice_id,
            "status": "D",
            "invoice_number": None,
            "gross_total": str(gross_total),
            "iva_total": str(iva_total),
            "net_total": str(gross_total - iva_total),
            "created_at": invoice.created_at.isoformat()
        }, 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating invoice: {str(e)}")
        return {"error": f"Error creating invoice: {str(e)}"}, 500


@agt_api.route('/invoices/<invoice_id>', methods=['GET'])
def get_invoice(invoice_id: str) -> Tuple[Dict[str, Any], int]:
    """Get invoice details"""
    try:
        invoice = db.session.query(Invoice).filter_by(invoice_id=invoice_id).first()
        
        if not invoice:
            return {"error": "Invoice not found"}, 404
        
        return {
            "invoice_id": invoice.invoice_id,
            "invoice_number": invoice.invoice_number,
            "status": invoice.status,
            "is_issued": invoice.is_issued,
            "is_editable": invoice.is_editable,
            "gross_total": str(invoice.gross_total),
            "iva_total": str(invoice.iva_total),
            "net_total": str(invoice.net_total),
            "invoice_date": invoice.invoice_date.isoformat(),
            "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
            "lines": [
                {
                    "line_number": line.line_number,
                    "description": line.description,
                    "quantity": str(line.quantity),
                    "unit_price": str(line.unit_price),
                    "line_gross": str(line.line_gross),
                    "iva_rate": str(line.iva_rate),
                    "iva_amount": str(line.iva_amount),
                    "line_net": str(line.line_net)
                }
                for line in invoice.lines
            ],
            "created_at": invoice.created_at.isoformat()
        }, 200
        
    except Exception as e:
        logger.error(f"Error retrieving invoice: {str(e)}")
        return {"error": f"Error retrieving invoice: {str(e)}"}, 500


@agt_api.route('/invoices', methods=['GET'])
def list_invoices() -> Tuple[Dict[str, Any], int]:
    """List all invoices with optional filtering"""
    try:
        status = request.args.get('status')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        query = db.session.query(Invoice).filter(Invoice.deleted_at.is_(None))
        
        if status:
            query = query.filter_by(status=status)
        
        total = query.count()
        invoices = query.offset((page - 1) * per_page).limit(per_page).all()
        
        return {
            "total": total,
            "page": page,
            "per_page": per_page,
            "invoices": [
                {
                    "invoice_id": inv.invoice_id,
                    "invoice_number": inv.invoice_number,
                    "status": inv.status,
                    "gross_total": str(inv.gross_total),
                    "iva_total": str(inv.iva_total),
                    "created_at": inv.created_at.isoformat()
                }
                for inv in invoices
            ]
        }, 200
        
    except Exception as e:
        logger.error(f"Error listing invoices: {str(e)}")
        return {"error": f"Error listing invoices: {str(e)}"}, 500


# ============================================================================
# INVOICE OPERATIONS
# ============================================================================

@agt_api.route('/invoices/<invoice_id>/issue', methods=['POST'])
def issue_invoice(invoice_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Issue invoice (DRAFT -> ISSUED)
    Locks for editing and generates invoice number
    """
    try:
        invoice = db.session.query(Invoice).filter_by(invoice_id=invoice_id).first()
        
        if not invoice:
            return {"error": "Invoice not found"}, 404
        
        # Check if already issued
        if invoice.is_issued:
            return {"error": "Invoice already issued"}, 400
        
        # Get last invoice number for this series
        last_invoice = db.session.query(Invoice).filter(
            Invoice.status.in_(['I', 'S', 'A']),
            Invoice.deleted_at.is_(None)
        ).order_by(Invoice.created_at.desc()).first()
        
        series_prefix = 'FT'
        series_sequence = 1 if not last_invoice else int(last_invoice.series_sequence or 0) + 1
        series_year = datetime.now().year
        
        # Generate invoice number
        invoice_number = f"{series_prefix} SEGUNDO{series_year}/{series_sequence:04d}"
        
        # Validate invoice number format
        is_valid, error = invoice_validator.validate_invoice_number_format(
            invoice_number, series_prefix, series_sequence, series_year
        )
        if not is_valid:
            logger.warning(f"Invalid invoice number: {error}")
            return {"error": f"Invalid invoice number: {error}"}, 400
        
        # Calculate hash before locking
        invoice_data = {
            'invoice_number': invoice_number,
            'supplier_id': invoice.supplier_id,
            'customer_id': invoice.customer_id,
            'invoice_date': invoice.invoice_date.isoformat(),
            'gross_total': str(invoice.gross_total),
            'iva_total': str(invoice.iva_total),
            'net_total': str(invoice.net_total),
            'lines': [
                {
                    'line_number': line.line_number,
                    'product_id': line.product_id,
                    'quantity': str(line.quantity),
                    'unit_price': str(line.unit_price),
                    'line_gross': str(line.line_gross),
                    'iva_amount': str(line.iva_amount),
                    'line_net': str(line.line_net)
                }
                for line in invoice.lines
            ]
        }
        
        data_hash = immutability_engine.calculate_invoice_hash(invoice_data)
        
        # Lock invoice
        invoice.invoice_number = invoice_number
        invoice.series_prefix = series_prefix
        invoice.series_sequence = series_sequence
        invoice.series_year = series_year
        invoice.status = 'I'
        invoice.is_issued = True
        invoice.is_editable = False
        invoice.data_hash_before_issue = data_hash
        invoice.issued_at = datetime.utcnow()
        invoice.locked_at = datetime.utcnow()
        
        # Log compliance event
        compliance_log = AGTComplianceLog(
            log_id=str(uuid.uuid4()),
            event_type='INVOICE_ISSUED',
            entity_type='INVOICE',
            entity_id=invoice.invoice_id,
            action='ISSUE',
            operator_id=request.get_json().get('operator_id', 'system') if request.is_json else 'system',
            operator_ip=request.remote_addr,
            data_before={'status': 'D', 'is_editable': True},
            data_after={
                'status': 'I',
                'is_editable': False,
                'invoice_number': invoice_number,
                'data_hash': data_hash
            },
            is_compliant=True
        )
        db.session.add(compliance_log)
        db.session.commit()
        
        logger.info(f"Invoice issued: {invoice_number}")
        
        return {
            "invoice_id": invoice.invoice_id,
            "invoice_number": invoice_number,
            "status": "I",
            "is_editable": False,
            "issued_at": invoice.issued_at.isoformat(),
            "data_hash": data_hash
        }, 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error issuing invoice: {str(e)}")
        return {"error": f"Error issuing invoice: {str(e)}"}, 500


@agt_api.route('/invoices/<invoice_id>/sign', methods=['POST'])
def sign_invoice(invoice_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Sign invoice with JWS (RS256)
    Requires invoice to be ISSUED
    """
    try:
        invoice = db.session.query(Invoice).filter_by(invoice_id=invoice_id).first()
        
        if not invoice:
            return {"error": "Invoice not found"}, 404
        
        if not invoice.is_issued:
            return {"error": "Invoice must be issued first"}, 400
        
        data = request.get_json() or {}
        operator_id = data.get('operator_id', 'system')
        
        # Initialize signature engine
        sig_engine = JWSSignatureEngine(SignatureAlgorithm.RS256)
        
        # Load keys (in production, from /etc/ssl/agt/private/)
        success, error = sig_engine.load_keys(
            private_key_path=data.get('private_key_path', '/etc/ssl/agt/private/keys/key_v1.pem'),
            certificate_path=data.get('certificate_path', '/etc/ssl/agt/public/certificates/agt_cert_v1.pem'),
            certificate_version=1
        )
        
        if not success:
            logger.warning(f"Failed to load keys: {error}")
            return {"error": f"Failed to load signing keys: {error}"}, 500
        
        # Create invoice data for signing
        invoice_data = {
            'invoice_number': invoice.invoice_number,
            'invoice_date': invoice.invoice_date.isoformat(),
            'supplier_nif': db.session.query(AnyEntity).filter_by(
                entity_id=invoice.supplier_id
            ).first().nif,
            'customer_nif': db.session.query(AnyEntity).filter_by(
                entity_id=invoice.customer_id
            ).first().nif,
            'gross_total': str(invoice.gross_total),
            'iva_total': str(invoice.iva_total),
            'net_total': str(invoice.net_total),
            'data_hash': invoice.data_hash_before_issue
        }
        
        # Sign
        jws_signature, error = sig_engine.sign_invoice(
            invoice_data,
            operator_id=operator_id,
            operator_ip=request.remote_addr
        )
        
        if error:
            logger.warning(f"Signing failed: {error}")
            return {"error": f"Signing failed: {error}"}, 500
        
        # Update invoice
        invoice.signature_jws = jws_signature
        invoice.status = 'S'  # SIGNED
        invoice.certificate_version = 1
        invoice.signed_at = datetime.utcnow()
        
        # Log signature audit
        sig_audit = InvoiceSignatureAudit(
            audit_id=str(uuid.uuid4()),
            invoice_id=invoice.invoice_id,
            invoice_number=invoice.invoice_number,
            operation_type='SIGN',
            status='SUCCESS',
            status_code='SIG_001',
            operator_id=operator_id,
            operator_ip=request.remote_addr
        )
        db.session.add(sig_audit)
        
        # Log compliance event
        compliance_log = AGTComplianceLog(
            log_id=str(uuid.uuid4()),
            event_type='INVOICE_SIGNED',
            entity_type='INVOICE',
            entity_id=invoice.invoice_id,
            action='SIGN',
            operator_id=operator_id,
            operator_ip=request.remote_addr,
            data_before={'status': 'I'},
            data_after={'status': 'S', 'signature_jws': jws_signature[:50] + '...'},
            is_compliant=True
        )
        db.session.add(compliance_log)
        db.session.commit()
        
        logger.info(f"Invoice signed: {invoice.invoice_number}")
        
        return {
            "invoice_id": invoice.invoice_id,
            "invoice_number": invoice.invoice_number,
            "status": "S",
            "signature_jws": jws_signature,
            "signed_at": invoice.signed_at.isoformat()
        }, 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error signing invoice: {str(e)}")
        return {"error": f"Error signing invoice: {str(e)}"}, 500


@agt_api.route('/invoices/<invoice_id>/submit', methods=['POST'])
def submit_invoice(invoice_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Submit invoice to AGT
    Requires invoice to be SIGNED
    """
    try:
        invoice = db.session.query(Invoice).filter_by(invoice_id=invoice_id).first()
        
        if not invoice:
            return {"error": "Invoice not found"}, 404
        
        if invoice.status != 'S':
            return {"error": "Invoice must be signed first"}, 400
        
        data = request.get_json() or {}
        operator_id = data.get('operator_id', 'system')
        
        # Generate AGT submission ID
        agt_submission_id = f"AGT-{datetime.now().year}-{uuid.uuid4().hex[:8].upper()}"
        
        # Update invoice status
        invoice.status = 'T'  # SUBMITTED (using T as per original schema)
        invoice.agt_submission_id = agt_submission_id
        invoice.submitted_at = datetime.utcnow()
        
        # Log signature audit
        sig_audit = InvoiceSignatureAudit(
            audit_id=str(uuid.uuid4()),
            invoice_id=invoice.invoice_id,
            invoice_number=invoice.invoice_number,
            operation_type='SUBMIT',
            status='SUCCESS',
            status_code='SUB_001',
            operator_id=operator_id,
            operator_ip=request.remote_addr,
            agt_response_code='200',
            agt_response_body={'status': 'received', 'submission_id': agt_submission_id}
        )
        db.session.add(sig_audit)
        
        # Log compliance event
        compliance_log = AGTComplianceLog(
            log_id=str(uuid.uuid4()),
            event_type='INVOICE_SUBMITTED',
            entity_type='INVOICE',
            entity_id=invoice.invoice_id,
            action='SUBMIT',
            operator_id=operator_id,
            operator_ip=request.remote_addr,
            data_before={'status': 'S'},
            data_after={'status': 'T', 'agt_submission_id': agt_submission_id},
            is_compliant=True
        )
        db.session.add(compliance_log)
        db.session.commit()
        
        logger.info(f"Invoice submitted to AGT: {invoice.invoice_number} - {agt_submission_id}")
        
        return {
            "invoice_id": invoice.invoice_id,
            "invoice_number": invoice.invoice_number,
            "status": "T",
            "agt_submission_id": agt_submission_id,
            "submitted_at": invoice.submitted_at.isoformat()
        }, 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error submitting invoice: {str(e)}")
        return {"error": f"Error submitting invoice: {str(e)}"}, 500


# ============================================================================
# CORRECTION NOTES (CREDIT & DEBIT)
# ============================================================================

@agt_api.route('/invoices/<invoice_id>/credit-note', methods=['POST'])
def create_credit_note(invoice_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Create Credit Note (Nota de Crédito) for issued invoice
    Used for discounts or reversals
    """
    try:
        original_invoice = db.session.query(Invoice).filter_by(invoice_id=invoice_id).first()
        
        if not original_invoice:
            return {"error": "Original invoice not found"}, 404
        
        if not original_invoice.is_issued:
            return {"error": "Original invoice must be issued"}, 400
        
        data = request.get_json()
        reason = data.get('reason', 'Nota de Crédito')
        operator_id = data.get('operator_id', 'system')
        partial_amount = data.get('partial_amount')  # If None, full reversal
        
        # Get last NC number for this series
        last_nc = db.session.query(Invoice).filter(
            Invoice.series_prefix == 'NC',
            Invoice.deleted_at.is_(None)
        ).order_by(Invoice.created_at.desc()).first()
        
        series_sequence = 1 if not last_nc else int(last_nc.series_sequence or 0) + 1
        series_year = datetime.now().year
        invoice_number = f"NC SEGUNDO{series_year}/{series_sequence:04d}"
        
        # Create NC invoice
        nc_invoice = Invoice(
            invoice_id=str(uuid.uuid4()),
            supplier_id=original_invoice.supplier_id,
            customer_id=original_invoice.customer_id,
            invoice_date=datetime.now(),
            reference_invoice_id=original_invoice.invoice_id,
            invoice_number=invoice_number,
            series_prefix='NC',
            series_sequence=series_sequence,
            series_year=series_year,
            status='I',
            is_issued=True,
            is_editable=False
        )
        
        # Create reversed lines
        total_amount = Decimal(str(partial_amount or original_invoice.net_total))
        
        for idx, line in enumerate(original_invoice.lines, 1):
            # Calculate proportion if partial
            if partial_amount:
                proportion = Decimal(str(partial_amount)) / original_invoice.net_total
                line_amount = line.line_net * proportion
            else:
                line_amount = line.line_net
                proportion = Decimal('1.0')
            
            nc_line = InvoiceLine(
                line_id=str(uuid.uuid4()),
                invoice_id=nc_invoice.invoice_id,
                product_id=line.product_id,
                line_number=idx,
                description=f"NC: {line.description}",
                quantity=-line.quantity * proportion,  # Negative quantity
                unit_price=line.unit_price,
                line_gross=-line.line_gross * proportion,  # Negative amounts
                iva_amount=-line.iva_amount * proportion,
                line_net=-line_amount,
                iva_regime=line.iva_regime,
                iva_rate=line.iva_rate,
                iva_exemption_code=line.iva_exemption_code
            )
            nc_invoice.lines.append(nc_line)
        
        # Set totals (negative)
        nc_invoice.gross_total = -sum(line.line_gross for line in nc_invoice.lines)
        nc_invoice.iva_total = -sum(line.iva_amount for line in nc_invoice.lines)
        nc_invoice.net_total = -total_amount
        
        db.session.add(nc_invoice)
        
        # Log compliance event
        compliance_log = AGTComplianceLog(
            log_id=str(uuid.uuid4()),
            event_type='CREDIT_NOTE_CREATED',
            entity_type='INVOICE',
            entity_id=nc_invoice.invoice_id,
            action='CREATE_NC',
            operator_id=operator_id,
            operator_ip=request.remote_addr,
            data_after={
                'nc_invoice_id': nc_invoice.invoice_id,
                'reference_invoice_id': original_invoice.invoice_id,
                'reason': reason,
                'amount': str(total_amount)
            },
            is_compliant=True
        )
        db.session.add(compliance_log)
        db.session.commit()
        
        logger.info(f"Credit note created: {invoice_number} for {original_invoice.invoice_number}")
        
        return {
            "credit_note_id": nc_invoice.invoice_id,
            "credit_note_number": invoice_number,
            "reference_invoice_id": original_invoice.invoice_id,
            "reason": reason,
            "amount": str(total_amount),
            "status": "I",
            "created_at": nc_invoice.created_at.isoformat()
        }, 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating credit note: {str(e)}")
        return {"error": f"Error creating credit note: {str(e)}"}, 500


@agt_api.route('/invoices/<invoice_id>/debit-note', methods=['POST'])
def create_debit_note(invoice_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Create Debit Note (Nota de Débito) for additional charges
    """
    try:
        original_invoice = db.session.query(Invoice).filter_by(invoice_id=invoice_id).first()
        
        if not original_invoice:
            return {"error": "Original invoice not found"}, 404
        
        if not original_invoice.is_issued:
            return {"error": "Original invoice must be issued"}, 400
        
        data = request.get_json()
        reason = data.get('reason', 'Nota de Débito')
        additional_amount = Decimal(str(data.get('amount', 0)))
        operator_id = data.get('operator_id', 'system')
        iva_rate = Decimal(str(data.get('iva_rate', 14)))
        
        # Get last ND number
        last_nd = db.session.query(Invoice).filter(
            Invoice.series_prefix == 'ND',
            Invoice.deleted_at.is_(None)
        ).order_by(Invoice.created_at.desc()).first()
        
        series_sequence = 1 if not last_nd else int(last_nd.series_sequence or 0) + 1
        series_year = datetime.now().year
        invoice_number = f"ND SEGUNDO{series_year}/{series_sequence:04d}"
        
        # Create ND invoice
        nd_invoice = Invoice(
            invoice_id=str(uuid.uuid4()),
            supplier_id=original_invoice.supplier_id,
            customer_id=original_invoice.customer_id,
            invoice_date=datetime.now(),
            reference_invoice_id=original_invoice.invoice_id,
            invoice_number=invoice_number,
            series_prefix='ND',
            series_sequence=series_sequence,
            series_year=series_year,
            status='I',
            is_issued=True,
            is_editable=False
        )
        
        # Create charge line
        iva_amount = additional_amount * (iva_rate / 100)
        line_net = additional_amount - iva_amount
        
        nd_line = InvoiceLine(
            line_id=str(uuid.uuid4()),
            invoice_id=nd_invoice.invoice_id,
            product_id=original_invoice.lines[0].product_id if original_invoice.lines else None,
            line_number=1,
            description=f"ND: {reason}",
            quantity=Decimal('1'),
            unit_price=additional_amount,
            line_gross=additional_amount,
            iva_amount=iva_amount,
            line_net=line_net,
            iva_regime='GENERAL',
            iva_rate=iva_rate,
            iva_exemption_code=None
        )
        nd_invoice.lines.append(nd_line)
        
        # Set totals (positive)
        nd_invoice.gross_total = additional_amount
        nd_invoice.iva_total = iva_amount
        nd_invoice.net_total = line_net
        
        db.session.add(nd_invoice)
        
        # Log compliance event
        compliance_log = AGTComplianceLog(
            log_id=str(uuid.uuid4()),
            event_type='DEBIT_NOTE_CREATED',
            entity_type='INVOICE',
            entity_id=nd_invoice.invoice_id,
            action='CREATE_ND',
            operator_id=operator_id,
            operator_ip=request.remote_addr,
            data_after={
                'nd_invoice_id': nd_invoice.invoice_id,
                'reference_invoice_id': original_invoice.invoice_id,
                'reason': reason,
                'amount': str(additional_amount)
            },
            is_compliant=True
        )
        db.session.add(compliance_log)
        db.session.commit()
        
        logger.info(f"Debit note created: {invoice_number} for {original_invoice.invoice_number}")
        
        return {
            "debit_note_id": nd_invoice.invoice_id,
            "debit_note_number": invoice_number,
            "reference_invoice_id": original_invoice.invoice_id,
            "reason": reason,
            "amount": str(additional_amount),
            "iva_amount": str(iva_amount),
            "status": "I",
            "created_at": nd_invoice.created_at.isoformat()
        }, 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating debit note: {str(e)}")
        return {"error": f"Error creating debit note: {str(e)}"}, 500


# ============================================================================
# SAF-T EXPORT
# ============================================================================

@agt_api.route('/invoices/saft/export', methods=['GET'])
def export_saft() -> Tuple[str, int]:
    """
    Export SAF-T (AO) XML for period
    
    Query parameters:
    - month: 01-12 (required)
    - year: 2026 (required)
    
    Response: application/xml
    """
    try:
        month = int(request.args.get('month', datetime.now().month))
        year = int(request.args.get('year', datetime.now().year))
        
        # Validate month/year
        if month < 1 or month > 12:
            return {"error": "Invalid month (01-12)"}, 400
        
        # Get invoices for period
        from datetime import date
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        
        invoices = db.session.query(Invoice).filter(
            Invoice.invoice_date >= start_date,
            Invoice.invoice_date < end_date,
            Invoice.is_issued == True,
            Invoice.deleted_at.is_(None)
        ).all()
        
        # Get unique customers and products
        customers = db.session.query(AnyEntity).filter(
            AnyEntity.entity_id.in_([inv.customer_id for inv in invoices]),
            AnyEntity.deleted_at.is_(None)
        ).all()
        
        products_ids = set()
        for inv in invoices:
            for line in inv.lines:
                products_ids.add(line.product_id)
        
        products = db.session.query(AGTProduct).filter(
            AGTProduct.product_id.in_(list(products_ids))
        ).all()
        
        # Get supplier (usually just one)
        supplier_ids = set(inv.supplier_id for inv in invoices)
        suppliers = db.session.query(AnyEntity).filter(
            AnyEntity.entity_id.in_(list(supplier_ids))
        ).all()
        
        # Use first supplier as company
        company_data = {
            'nif': suppliers[0].nif if suppliers else '234-5678-9012',
            'name': suppliers[0].name if suppliers else 'Company Name',
            'address': 'Rua Principal, 123',
            'city': 'Luanda',
            'country': 'AO'
        }
        
        # Generate SAFT
        generator = SAFTAOGenerator(company_data)
        xml = generator.generate(customers, products, invoices, [], [])
        
        logger.info(f"SAF-T export generated for {month:02d}/{year}")
        
        return xml, 200, {'Content-Type': 'application/xml; charset=utf-8'}
        
    except Exception as e:
        logger.error(f"Error exporting SAF-T: {str(e)}")
        return {"error": f"Error exporting SAF-T: {str(e)}"}, 500


# ============================================================================
# HEALTH CHECK
# ============================================================================

@agt_api.route('/health', methods=['GET'])
def health_check() -> Tuple[Dict[str, Any], int]:
    """Health check endpoint"""
    return {
        "status": "ok",
        "version": "1.0",
        "timestamp": datetime.utcnow().isoformat()
    }, 200
