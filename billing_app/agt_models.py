"""
AGT (Autoridade Geral Tributária) Compliance Models - Angola
Implements SAF-T (AO) requirements for e-invoicing in Angola
Compliant with 2026 regulations
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, Text, 
    Numeric, ForeignKey, CHAR, CheckConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class NIFType(Enum):
    """NIF types for entities"""
    PERSON = "1"  # Natural person
    COMPANY = "2"  # Company
    FOREIGN = "3"  # Foreign entity


class IVARegimeType(Enum):
    """IVA Regime Types according to AGT"""
    GENERAL = "1"      # Regime Geral (14%)
    SIMPLIFIED = "2"   # Regime Simplificado (alguns casos)
    EXEMPT = "3"       # Isento de IVA
    NOT_SUBJECT = "4"  # Não sujeito
    REVERSE_CHARGE = "5"  # Inversão do Sujeito Passivo


class IVAExemptionCode(Enum):
    """SAF-T AO Exemption codes when IVA rate is 0%"""
    M01 = "M01"  # Artigo 14 do CIVA
    M02 = "M02"  # Artigo 14.a CIVA
    M03 = "M03"  # Artigo 15 CIVA
    M04 = "M04"  # Artigo 40 CIVA
    M05 = "M05"  # Documentos do Estado
    M06 = "M06"  # Negócios sobre ouro
    M07 = "M07"  # Importação de bens
    M08 = "M08"  # Intracomunutário
    M09 = "M09"  # Exportação


class InvoiceStatus(Enum):
    """Invoice lifecycle status"""
    DRAFT = "D"           # Rascunho
    ISSUED = "I"          # Emitida
    CANCELLED = "C"       # Cancelada
    SUBMITTED = "S"       # Submetida à AGT
    ACKNOWLEDGED = "A"    # Reconhecida pela AGT
    REFUSED = "R"         # Rejeitada pela AGT
    CORRECTED = "T"       # Retificada


class InvoiceSignatureStatus(Enum):
    """Signature submission status to AGT API"""
    PENDING = "P"         # Aguardando assinatura
    SIGNED = "S"          # Assinada
    SUBMITTED = "M"       # Enviada para AGT
    VALIDATED = "V"       # Validada pela AGT
    REJECTED = "R"        # Rejeitada pela AGT


class AnyEntity(Base):
    """Base entity for AGT compliance - Customers/Suppliers"""
    __tablename__ = 'agt_any_entity'

    # Primary key
    entity_id = Column(String(36), primary_key=True)
    
    # Mandatory NIF fields (AGT compliance)
    nif = Column(String(14), unique=True, nullable=False, index=True)
    nif_type = Column(String(1), nullable=False)  # 1=Person, 2=Company, 3=Foreign
    
    # Entity identification
    name = Column(String(100), nullable=False)
    address_detail = Column(String(100), nullable=False)
    city = Column(String(50), nullable=False)
    postal_code = Column(String(10), nullable=False)
    country = Column(String(2), nullable=False, default="AO")  # ISO 3166-1 alpha-2
    
    # Contact information
    telephone = Column(String(20), nullable=True)
    fax = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    
    # Tax compliance fields
    is_tax_resident = Column(Boolean, default=True)
    is_vat_registered = Column(Boolean, default=True)
    vat_exempt_certificate = Column(String(50), nullable=True)  # Certificate number if exempt
    
    # Audit trail
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Soft delete for AGT compliance
    deleted_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, index=True)

    # Relationships
    invoices_issued = relationship("Invoice", foreign_keys="Invoice.customer_id", back_populates="customer")
    invoices_received = relationship("Invoice", foreign_keys="Invoice.supplier_id", back_populates="supplier")

    __table_args__ = (
        Index('idx_nif_active', 'nif', 'is_active'),
        Index('idx_country_city', 'country', 'city'),
    )


class AGTProduct(Base):
    """Product/Service master file for AGT compliance"""
    __tablename__ = 'agt_product'

    # Primary key
    product_id = Column(String(36), primary_key=True)
    
    # Product identification
    product_code = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(200), nullable=False)
    product_type = Column(String(2), nullable=False)  # "01"=Good, "02"=Service
    
    # Pricing
    unit_price = Column(Numeric(18, 2), nullable=False)
    currency = Column(String(3), default="AOA", nullable=False)  # Angolan Kwanza
    
    # IVA Configuration (mandatory for each product)
    iva_regime = Column(String(1), nullable=False)  # Use IVARegimeType values
    iva_rate = Column(Numeric(5, 2), nullable=False)  # e.g., 14.00, 0.00
    iva_exemption_code = Column(String(3), nullable=True)  # Required if iva_rate = 0
    
    # Product classification
    ncm_code = Column(String(12), nullable=True)  # Código de classificação de produtos
    
    # Audit trail
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True, index=True)

    # Relationships
    invoice_lines = relationship("InvoiceLine", back_populates="product")

    __table_args__ = (
        CheckConstraint('iva_rate >= 0 AND iva_rate <= 100', name='check_iva_rate'),
        CheckConstraint(
            "NOT (iva_rate = 0 AND iva_exemption_code IS NULL)",
            name='check_iva_exemption_required'
        ),
        Index('idx_product_code_active', 'product_code', 'is_active'),
    )


class Invoice(Base):
    """Invoice header - AGT SAF-T (AO) compliance"""
    __tablename__ = 'agt_invoice'

    # Primary key
    invoice_id = Column(String(36), primary_key=True)
    
    # Invoice identification (AGT mandatory)
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    # Example: "FT SEGUNDO2026/0001" (FT=Fatura, SEGUNDO=Sequential, 2026=Year, 0001=Number)
    series_prefix = Column(String(20), nullable=False)  # "FT", "NC", "ND"
    series_sequence = Column(Integer, nullable=False)   # Sequential number
    series_year = Column(Integer, nullable=False)       # Fiscal year
    
    # Parties involved
    supplier_id = Column(String(36), ForeignKey('agt_any_entity.entity_id'), nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey('agt_any_entity.entity_id'), nullable=False, index=True)
    
    # Invoice dates (mandatory for AGT)
    invoice_date = Column(DateTime, nullable=False, index=True)
    due_date = Column(DateTime, nullable=True)
    
    # Financial data
    gross_total = Column(Numeric(18, 2), nullable=False)
    iva_total = Column(Numeric(18, 2), nullable=False)
    net_total = Column(Numeric(18, 2), nullable=False)
    
    # Description
    description = Column(Text, nullable=True)
    
    # Invoice status (AGT compliance)
    status = Column(String(1), nullable=False, default=InvoiceStatus.DRAFT.value)
    
    # Immutability - Hash of invoice data before issuing
    data_hash_before_issue = Column(String(64), nullable=True)  # SHA256 hash
    is_issued = Column(Boolean, default=False, index=True)
    issued_at = Column(DateTime, nullable=True)
    
    # Prevent modification after issue
    is_editable = Column(Boolean, default=True)  # Set to False after issue
    locked_at = Column(DateTime, nullable=True)  # When invoice was locked
    
    # AGT Signature fields
    signature_jws = Column(Text, nullable=True)  # JWS signature for AGT
    signature_status = Column(String(1), nullable=False, default=InvoiceSignatureStatus.PENDING.value)
    signature_timestamp = Column(DateTime, nullable=True)
    
    # Public key version (versioning for key rotation)
    certificate_version = Column(Integer, nullable=True)
    certificate_subject = Column(String(255), nullable=True)
    certificate_valid_from = Column(DateTime, nullable=True)
    certificate_valid_to = Column(DateTime, nullable=True)
    
    # AGT API submission
    agt_submission_id = Column(String(100), nullable=True)  # Unique ID from AGT
    agt_validation_code = Column(String(50), nullable=True)  # AGT response code
    agt_submitted_at = Column(DateTime, nullable=True)
    agt_acknowledged_at = Column(DateTime, nullable=True)
    
    # Audit trail
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Soft delete
    deleted_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, index=True)

    # Relationships
    customer = relationship("AnyEntity", foreign_keys=[customer_id], back_populates="invoices_issued")
    supplier = relationship("AnyEntity", foreign_keys=[supplier_id], back_populates="invoices_received")
    lines = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")
    signatures = relationship("InvoiceSignatureAudit", back_populates="invoice", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint('net_total > 0', name='check_net_total_positive'),
        CheckConstraint('is_editable = FALSE OR is_issued = FALSE', name='check_editable_only_before_issue'),
        Index('idx_invoice_number_supplier', 'invoice_number', 'supplier_id'),
        Index('idx_invoice_date_status', 'invoice_date', 'status'),
        Index('idx_signature_status', 'signature_status'),
    )


class InvoiceLine(Base):
    """Invoice line items - AGT SAF-T (AO) compliance"""
    __tablename__ = 'agt_invoice_line'

    # Primary key
    line_id = Column(String(36), primary_key=True)
    
    # Foreign keys
    invoice_id = Column(String(36), ForeignKey('agt_invoice.invoice_id'), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey('agt_product.product_id'), nullable=False, index=True)
    
    # Line sequence
    line_number = Column(Integer, nullable=False)
    
    # Line details
    description = Column(String(200), nullable=False)
    unit_price = Column(Numeric(18, 2), nullable=False)
    quantity = Column(Numeric(15, 2), nullable=False)
    
    # Calculation fields (audit trail)
    line_gross = Column(Numeric(18, 2), nullable=False)
    iva_rate = Column(Numeric(5, 2), nullable=False)
    iva_amount = Column(Numeric(18, 2), nullable=False)
    line_net = Column(Numeric(18, 2), nullable=False)
    
    # IVA regime and exemption (replicated from product at invoice time)
    iva_regime = Column(String(1), nullable=False)
    iva_exemption_code = Column(String(3), nullable=True)
    
    # Settlement information
    settlement_amount = Column(Numeric(18, 2), nullable=True)
    discount_percentage = Column(Numeric(5, 2), default=0)
    
    # Audit trail
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    invoice = relationship("Invoice", back_populates="lines")
    product = relationship("AGTProduct", back_populates="invoice_lines")

    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_line_quantity_positive'),
        CheckConstraint('line_gross > 0', name='check_line_gross_positive'),
        Index('idx_invoice_line_number', 'invoice_id', 'line_number'),
    )


class InvoiceSignatureAudit(Base):
    """Audit trail for signature operations - compliance requirement"""
    __tablename__ = 'agt_invoice_signature_audit'

    # Primary key
    audit_id = Column(String(36), primary_key=True)
    
    # References
    invoice_id = Column(String(36), ForeignKey('agt_invoice.invoice_id'), nullable=False, index=True)
    
    # Signature operation details
    operation_type = Column(String(20), nullable=False)  # "SIGN", "VERIFY", "SUBMIT", "REJECT"
    signature_hash = Column(String(64), nullable=True)  # SHA256 hash of signature
    
    # Status and result
    status = Column(String(1), nullable=False)  # "S"=Success, "F"=Failure
    status_code = Column(String(50), nullable=True)
    status_message = Column(Text, nullable=True)
    
    # Operator information (who signed)
    operator_id = Column(String(36), nullable=False)
    operator_ip = Column(String(45), nullable=True)  # IPv4 or IPv6
    
    # Response from AGT (if applicable)
    agt_response_code = Column(String(50), nullable=True)
    agt_response_body = Column(Text, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    invoice = relationship("Invoice", back_populates="signatures")

    __table_args__ = (
        Index('idx_invoice_audit_date', 'invoice_id', 'created_at'),
        Index('idx_operation_status', 'operation_type', 'status'),
    )


class AGTComplianceLog(Base):
    """System-wide AGT compliance log for regulatory audits"""
    __tablename__ = 'agt_compliance_log'

    # Primary key
    log_id = Column(String(36), primary_key=True)
    
    # Event details
    event_type = Column(String(50), nullable=False)  # "INVOICE_CREATED", "INVOICE_LOCKED", "SIGNATURE_FAILED", etc.
    entity_type = Column(String(50), nullable=False)  # "INVOICE", "CUSTOMER", "SIGNATURE"
    entity_id = Column(String(36), nullable=False, index=True)
    
    # Action details
    action = Column(String(20), nullable=False)  # "CREATE", "UPDATE", "DELETE", "LOCK", "SIGN"
    details = Column(Text, nullable=True)
    
    # Who performed the action
    operator_id = Column(String(36), nullable=False)
    operator_ip = Column(String(45), nullable=True)
    
    # Data before/after (for audit trail)
    data_before = Column(Text, nullable=True)  # JSON
    data_after = Column(Text, nullable=True)   # JSON
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Regulatory fields
    is_compliant = Column(Boolean, default=True)
    compliance_notes = Column(Text, nullable=True)

    __table_args__ = (
        Index('idx_event_type_date', 'event_type', 'created_at'),
        Index('idx_entity_type_id', 'entity_type', 'entity_id'),
    )


class AGTCertificateKey(Base):
    """Secure storage of AGT certificate information and key metadata"""
    __tablename__ = 'agt_certificate_key'

    # Primary key
    key_id = Column(String(36), primary_key=True)
    
    # Certificate information
    certificate_version = Column(Integer, nullable=False, unique=True)
    subject = Column(String(255), nullable=False)  # Certificate subject name
    issuer = Column(String(255), nullable=False)   # CA issuer
    
    # Validity period
    valid_from = Column(DateTime, nullable=False)
    valid_to = Column(DateTime, nullable=False)
    
    # Key storage location (reference, actual key is in secure storage)
    key_path = Column(String(255), nullable=False)  # /etc/ssl/private/agt/key_v{version}.pem
    key_fingerprint = Column(String(64), nullable=False)  # SHA256 fingerprint
    
    # Key protection metadata
    key_protected_with = Column(String(50), nullable=False)  # "AES256-GCM", "HSM"
    key_rotation_date = Column(DateTime, nullable=True)
    key_retirement_date = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    
    # Audit trail
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(36), nullable=False)  # System/operator ID

    __table_args__ = (
        Index('idx_certificate_valid', 'valid_from', 'valid_to', 'is_active'),
    )


# SQL Constraints for AGT compliance
# These are enforced at database level for regulatory compliance

__all__ = [
    'NIFType',
    'IVARegimeType',
    'IVAExemptionCode',
    'InvoiceStatus',
    'InvoiceSignatureStatus',
    'AnyEntity',
    'AGTProduct',
    'Invoice',
    'InvoiceLine',
    'InvoiceSignatureAudit',
    'AGTComplianceLog',
    'AGTCertificateKey',
    'Base'
]
