"""
Initial AGT Compliance Schema

Revision ID: 001_initial_agt_schema
Revises: 
Create Date: 2026-05-03 10:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_initial_agt_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial AGT schema"""
    
    # AnyEntity table (Customers/Suppliers)
    op.create_table(
        'agt_any_entity',
        sa.Column('entity_id', sa.String(36), nullable=False),
        sa.Column('nif', sa.String(14), nullable=False, unique=True),
        sa.Column('nif_type', sa.String(20), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('address', sa.String(255), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('postal_code', sa.String(20), nullable=True),
        sa.Column('country', sa.String(3), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('telephone', sa.String(20), nullable=True),
        sa.Column('is_tax_resident', sa.Boolean(), default=True),
        sa.Column('is_vat_registered', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('entity_id'),
        sa.Index('idx_nif', 'nif'),
        sa.Index('idx_entity_type', 'nif_type')
    )
    
    # AGTProduct table
    op.create_table(
        'agt_product',
        sa.Column('product_id', sa.String(36), nullable=False),
        sa.Column('product_code', sa.String(50), nullable=False, unique=True),
        sa.Column('description', sa.String(255), nullable=False),
        sa.Column('unit_price', sa.Numeric(15, 2), nullable=False),
        sa.Column('iva_regime', sa.String(20), nullable=False),
        sa.Column('iva_rate', sa.Numeric(5, 2), nullable=False),
        sa.Column('iva_exemption_code', sa.String(3), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('product_id'),
        sa.Index('idx_product_code', 'product_code'),
        sa.Index('idx_iva_regime', 'iva_regime')
    )
    
    # Invoice table
    op.create_table(
        'agt_invoice',
        sa.Column('invoice_id', sa.String(36), nullable=False),
        sa.Column('invoice_number', sa.String(50), nullable=True, unique=True),
        sa.Column('series_prefix', sa.String(10), nullable=True),
        sa.Column('series_sequence', sa.Integer(), nullable=True),
        sa.Column('series_year', sa.Integer(), nullable=True),
        sa.Column('supplier_id', sa.String(36), nullable=False),
        sa.Column('customer_id', sa.String(36), nullable=False),
        sa.Column('invoice_date', sa.DateTime(), nullable=False),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('gross_total', sa.Numeric(15, 2), nullable=True),
        sa.Column('iva_total', sa.Numeric(15, 2), nullable=True),
        sa.Column('net_total', sa.Numeric(15, 2), nullable=True),
        sa.Column('data_hash_before_issue', sa.String(64), nullable=True),
        sa.Column('is_issued', sa.Boolean(), default=False),
        sa.Column('is_editable', sa.Boolean(), default=True),
        sa.Column('status', sa.String(1), default='D'),
        sa.Column('signature_jws', sa.Text(), nullable=True),
        sa.Column('certificate_version', sa.Integer(), nullable=True),
        sa.Column('agt_submission_id', sa.String(50), nullable=True),
        sa.Column('agt_validation_code', sa.String(100), nullable=True),
        sa.Column('issued_at', sa.DateTime(), nullable=True),
        sa.Column('signed_at', sa.DateTime(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('locked_at', sa.DateTime(), nullable=True),
        sa.Column('reference_invoice_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('invoice_id'),
        sa.ForeignKeyConstraint(['supplier_id'], ['agt_any_entity.entity_id']),
        sa.ForeignKeyConstraint(['customer_id'], ['agt_any_entity.entity_id']),
        sa.Index('idx_invoice_number', 'invoice_number'),
        sa.Index('idx_status', 'status'),
        sa.Index('idx_invoice_date', 'invoice_date'),
        sa.Index('idx_is_issued', 'is_issued')
    )
    
    # InvoiceLine table
    op.create_table(
        'agt_invoice_line',
        sa.Column('line_id', sa.String(36), nullable=False),
        sa.Column('invoice_id', sa.String(36), nullable=False),
        sa.Column('product_id', sa.String(36), nullable=False),
        sa.Column('line_number', sa.Integer(), nullable=False),
        sa.Column('description', sa.String(255), nullable=False),
        sa.Column('quantity', sa.Numeric(10, 2), nullable=False),
        sa.Column('unit_price', sa.Numeric(15, 2), nullable=False),
        sa.Column('line_gross', sa.Numeric(15, 2), nullable=False),
        sa.Column('iva_amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('line_net', sa.Numeric(15, 2), nullable=False),
        sa.Column('iva_regime', sa.String(20), nullable=False),
        sa.Column('iva_rate', sa.Numeric(5, 2), nullable=False),
        sa.Column('iva_exemption_code', sa.String(3), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.PrimaryKeyConstraint('line_id'),
        sa.ForeignKeyConstraint(['invoice_id'], ['agt_invoice.invoice_id']),
        sa.ForeignKeyConstraint(['product_id'], ['agt_product.product_id']),
        sa.Index('idx_invoice_line', 'invoice_id', 'line_number')
    )
    
    # InvoiceSignatureAudit table
    op.create_table(
        'agt_invoice_signature_audit',
        sa.Column('audit_id', sa.String(36), nullable=False),
        sa.Column('invoice_id', sa.String(36), nullable=False),
        sa.Column('invoice_number', sa.String(50), nullable=False),
        sa.Column('operation_type', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('status_code', sa.String(20), nullable=False),
        sa.Column('status_message', sa.Text(), nullable=True),
        sa.Column('operator_id', sa.String(50), nullable=False),
        sa.Column('operator_ip', sa.String(45), nullable=False),
        sa.Column('agt_response_code', sa.String(10), nullable=True),
        sa.Column('agt_response_body', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.PrimaryKeyConstraint('audit_id'),
        sa.ForeignKeyConstraint(['invoice_id'], ['agt_invoice.invoice_id']),
        sa.Index('idx_operation_type', 'operation_type'),
        sa.Index('idx_operator', 'operator_id')
    )
    
    # AGTComplianceLog table
    op.create_table(
        'agt_compliance_log',
        sa.Column('log_id', sa.String(36), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', sa.String(36), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('operator_id', sa.String(50), nullable=False),
        sa.Column('operator_ip', sa.String(45), nullable=False),
        sa.Column('data_before', sa.Text(), nullable=True),
        sa.Column('data_after', sa.Text(), nullable=True),
        sa.Column('is_compliant', sa.Boolean(), default=True),
        sa.Column('compliance_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.PrimaryKeyConstraint('log_id'),
        sa.Index('idx_event_type', 'event_type'),
        sa.Index('idx_entity', 'entity_type', 'entity_id'),
        sa.Index('idx_compliance', 'is_compliant')
    )
    
    # AGTCertificateKey table
    op.create_table(
        'agt_certificate_key',
        sa.Column('key_id', sa.String(36), nullable=False),
        sa.Column('certificate_version', sa.Integer(), nullable=False, unique=True),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('issuer', sa.String(255), nullable=False),
        sa.Column('valid_from', sa.DateTime(), nullable=False),
        sa.Column('valid_to', sa.DateTime(), nullable=False),
        sa.Column('key_path', sa.String(500), nullable=False),
        sa.Column('certificate_path', sa.String(500), nullable=True),
        sa.Column('key_fingerprint', sa.String(64), nullable=False),
        sa.Column('key_protected_with', sa.String(50), nullable=False),
        sa.Column('key_rotation_date', sa.DateTime(), nullable=True),
        sa.Column('key_retirement_date', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('created_by', sa.String(50), nullable=False),
        sa.PrimaryKeyConstraint('key_id'),
        sa.Index('idx_certificate_valid', 'valid_from', 'valid_to', 'is_active')
    )


def downgrade() -> None:
    """Drop all AGT tables"""
    op.drop_index('idx_certificate_valid', 'agt_certificate_key')
    op.drop_table('agt_certificate_key')
    
    op.drop_index('idx_compliance', 'agt_compliance_log')
    op.drop_index('idx_entity', 'agt_compliance_log')
    op.drop_index('idx_event_type', 'agt_compliance_log')
    op.drop_table('agt_compliance_log')
    
    op.drop_index('idx_operator', 'agt_invoice_signature_audit')
    op.drop_index('idx_operation_type', 'agt_invoice_signature_audit')
    op.drop_table('agt_invoice_signature_audit')
    
    op.drop_index('idx_invoice_line', 'agt_invoice_line')
    op.drop_table('agt_invoice_line')
    
    op.drop_index('idx_is_issued', 'agt_invoice')
    op.drop_index('idx_invoice_date', 'agt_invoice')
    op.drop_index('idx_status', 'agt_invoice')
    op.drop_index('idx_invoice_number', 'agt_invoice')
    op.drop_table('agt_invoice')
    
    op.drop_index('idx_iva_regime', 'agt_product')
    op.drop_index('idx_product_code', 'agt_product')
    op.drop_table('agt_product')
    
    op.drop_index('idx_entity_type', 'agt_any_entity')
    op.drop_index('idx_nif', 'agt_any_entity')
    op.drop_table('agt_any_entity')
