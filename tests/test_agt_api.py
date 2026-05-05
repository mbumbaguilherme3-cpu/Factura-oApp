"""
AGT API Tests - Flask endpoints
Testa todos os endpoints da API REST
"""

import pytest
import json
from decimal import Decimal
from datetime import datetime, timedelta
from uuid import uuid4

from billing_app.app_factory import create_app
from billing_app.db_config import db


@pytest.fixture
def app():
    """Create app for testing"""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client"""
    return app.test_client()


@pytest.fixture
def setup_entities(app):
    """Create test entities (customers, suppliers, products)"""
    from billing_app.agt_models import AnyEntity, AGTProduct
    
    with app.app_context():
        # Supplier
        supplier = AnyEntity(
            entity_id=str(uuid4()),
            nif='234-5678-9012',
            nif_type='COMPANY',
            name='Empresa Test SA',
            is_vat_registered=True
        )
        db.session.add(supplier)
        
        # Customer
        customer = AnyEntity(
            entity_id=str(uuid4()),
            nif='123-4567-8901',
            nif_type='COMPANY',
            name='Cliente Test Lda',
            is_vat_registered=True
        )
        db.session.add(customer)
        
        # Product
        product = AGTProduct(
            product_id=str(uuid4()),
            product_code='PROD-001',
            description='Serviço de Consultoria',
            unit_price=Decimal('1000.00'),
            iva_regime='GENERAL',
            iva_rate=Decimal('14.00')
        )
        db.session.add(product)
        db.session.commit()
        
        return {
            'supplier_id': supplier.entity_id,
            'supplier_nif': supplier.nif,
            'customer_id': customer.entity_id,
            'customer_nif': customer.nif,
            'product_id': product.product_id
        }


# ============================================================================
# INVOICE CREATION TESTS
# ============================================================================

def test_create_invoice_success(client, setup_entities):
    """Test creating an invoice successfully"""
    data = {
        "customer_nif": setup_entities['customer_nif'],
        "supplier_nif": setup_entities['supplier_nif'],
        "invoice_date": "2026-05-03",
        "due_date": "2026-06-03",
        "lines": [
            {
                "product_id": setup_entities['product_id'],
                "quantity": 1,
                "unit_price": "1000.00",
                "iva_regime": "GENERAL"
            }
        ]
    }
    
    response = client.post('/api/invoices', json=data)
    
    assert response.status_code == 201
    result = json.loads(response.data)
    assert result['status'] == 'D'
    assert result['invoice_id']
    assert result['gross_total'] == '1000.00'
    assert result['iva_total'] == '140.00'


def test_create_invoice_invalid_nif(client):
    """Test creating invoice with invalid NIF"""
    data = {
        "customer_nif": "invalid-nif",
        "supplier_nif": "234-5678-9012",
        "invoice_date": "2026-05-03",
        "lines": []
    }
    
    response = client.post('/api/invoices', json=data)
    assert response.status_code == 400


def test_create_invoice_exempt_iva_no_code(client, setup_entities):
    """Test creating invoice with exempt IVA but no exemption code"""
    from billing_app.agt_models import AGTProduct
    from decimal import Decimal
    
    # Create product with EXEMPT IVA without code
    with client.application.app_context():
        product = AGTProduct(
            product_id=str(uuid4()),
            product_code='EXEMPT-001',
            description='Serviço Isento',
            unit_price=Decimal('500.00'),
            iva_regime='EXEMPT',
            iva_rate=Decimal('0.00')
        )
        db.session.add(product)
        db.session.commit()
        
        data = {
            "customer_nif": setup_entities['customer_nif'],
            "supplier_nif": setup_entities['supplier_nif'],
            "invoice_date": "2026-05-03",
            "lines": [
                {
                    "product_id": product.product_id,
                    "quantity": 1,
                    "unit_price": "500.00",
                    "iva_regime": "EXEMPT",
                    "iva_exemption_code": None
                }
            ]
        }
        
        response = client.post('/api/invoices', json=data)
        # Should fail - requires exemption code
        assert response.status_code == 400


def test_get_invoice(client, setup_entities):
    """Test retrieving invoice details"""
    # Create invoice
    create_data = {
        "customer_nif": setup_entities['customer_nif'],
        "supplier_nif": setup_entities['supplier_nif'],
        "invoice_date": "2026-05-03",
        "lines": [
            {
                "product_id": setup_entities['product_id'],
                "quantity": 2,
                "unit_price": "500.00"
            }
        ]
    }
    
    create_response = client.post('/api/invoices', json=create_data)
    invoice_id = json.loads(create_response.data)['invoice_id']
    
    # Get invoice
    response = client.get(f'/api/invoices/{invoice_id}')
    
    assert response.status_code == 200
    result = json.loads(response.data)
    assert result['invoice_id'] == invoice_id
    assert result['status'] == 'D'
    assert len(result['lines']) == 1


def test_list_invoices(client, setup_entities):
    """Test listing invoices"""
    # Create 2 invoices
    create_data = {
        "customer_nif": setup_entities['customer_nif'],
        "supplier_nif": setup_entities['supplier_nif'],
        "invoice_date": "2026-05-03",
        "lines": [
            {
                "product_id": setup_entities['product_id'],
                "quantity": 1,
                "unit_price": "1000.00"
            }
        ]
    }
    
    client.post('/api/invoices', json=create_data)
    client.post('/api/invoices', json=create_data)
    
    # List invoices
    response = client.get('/api/invoices')
    
    assert response.status_code == 200
    result = json.loads(response.data)
    assert result['total'] == 2
    assert len(result['invoices']) == 2


# ============================================================================
# INVOICE OPERATIONS TESTS
# ============================================================================

def test_issue_invoice(client, setup_entities):
    """Test issuing an invoice (DRAFT -> ISSUED)"""
    # Create invoice
    create_data = {
        "customer_nif": setup_entities['customer_nif'],
        "supplier_nif": setup_entities['supplier_nif'],
        "invoice_date": "2026-05-03",
        "lines": [
            {
                "product_id": setup_entities['product_id'],
                "quantity": 1,
                "unit_price": "1000.00"
            }
        ]
    }
    
    create_response = client.post('/api/invoices', json=create_data)
    invoice_id = json.loads(create_response.data)['invoice_id']
    
    # Issue invoice
    response = client.post(f'/api/invoices/{invoice_id}/issue')
    
    assert response.status_code == 200
    result = json.loads(response.data)
    assert result['status'] == 'I'
    assert result['is_editable'] == False
    assert result['invoice_number']
    assert 'data_hash' in result


def test_issue_already_issued_invoice(client, setup_entities):
    """Test issuing an invoice that's already issued"""
    # Create and issue
    create_data = {
        "customer_nif": setup_entities['customer_nif'],
        "supplier_nif": setup_entities['supplier_nif'],
        "invoice_date": "2026-05-03",
        "lines": [
            {
                "product_id": setup_entities['product_id'],
                "quantity": 1,
                "unit_price": "1000.00"
            }
        ]
    }
    
    create_response = client.post('/api/invoices', json=create_data)
    invoice_id = json.loads(create_response.data)['invoice_id']
    
    client.post(f'/api/invoices/{invoice_id}/issue')
    
    # Try to issue again
    response = client.post(f'/api/invoices/{invoice_id}/issue')
    assert response.status_code == 400


# ============================================================================
# CORRECTION NOTES TESTS
# ============================================================================

def test_create_credit_note_full_reversal(client, setup_entities):
    """Test creating credit note for full reversal"""
    # Create and issue invoice
    create_data = {
        "customer_nif": setup_entities['customer_nif'],
        "supplier_nif": setup_entities['supplier_nif'],
        "invoice_date": "2026-05-03",
        "lines": [
            {
                "product_id": setup_entities['product_id'],
                "quantity": 1,
                "unit_price": "1000.00"
            }
        ]
    }
    
    create_response = client.post('/api/invoices', json=create_data)
    invoice_id = json.loads(create_response.data)['invoice_id']
    client.post(f'/api/invoices/{invoice_id}/issue')
    
    # Create credit note
    nc_data = {
        "reason": "Desconto total",
        "operator_id": "user_001"
    }
    
    response = client.post(f'/api/invoices/{invoice_id}/credit-note', json=nc_data)
    
    assert response.status_code == 201
    result = json.loads(response.data)
    assert result['credit_note_number']
    assert 'NC' in result['credit_note_number']


def test_create_debit_note(client, setup_entities):
    """Test creating debit note for additional charges"""
    # Create and issue invoice
    create_data = {
        "customer_nif": setup_entities['customer_nif'],
        "supplier_nif": setup_entities['supplier_nif'],
        "invoice_date": "2026-05-03",
        "lines": [
            {
                "product_id": setup_entities['product_id'],
                "quantity": 1,
                "unit_price": "1000.00"
            }
        ]
    }
    
    create_response = client.post('/api/invoices', json=create_data)
    invoice_id = json.loads(create_response.data)['invoice_id']
    client.post(f'/api/invoices/{invoice_id}/issue')
    
    # Create debit note
    nd_data = {
        "reason": "Taxa administrativa",
        "amount": "50.00",
        "iva_rate": 14,
        "operator_id": "user_001"
    }
    
    response = client.post(f'/api/invoices/{invoice_id}/debit-note', json=nd_data)
    
    assert response.status_code == 201
    result = json.loads(response.data)
    assert result['debit_note_number']
    assert 'ND' in result['debit_note_number']
    assert result['amount'] == '50.00'


# ============================================================================
# SAF-T EXPORT TESTS
# ============================================================================

def test_saft_export(client, setup_entities):
    """Test SAF-T XML export"""
    # Create and issue invoice
    create_data = {
        "customer_nif": setup_entities['customer_nif'],
        "supplier_nif": setup_entities['supplier_nif'],
        "invoice_date": "2026-05-03",
        "lines": [
            {
                "product_id": setup_entities['product_id'],
                "quantity": 1,
                "unit_price": "1000.00"
            }
        ]
    }
    
    create_response = client.post('/api/invoices', json=create_data)
    invoice_id = json.loads(create_response.data)['invoice_id']
    client.post(f'/api/invoices/{invoice_id}/issue')
    
    # Export SAF-T
    response = client.get('/api/invoices/saft/export?month=5&year=2026')
    
    assert response.status_code == 200
    assert response.content_type == 'application/xml; charset=utf-8'
    assert b'<?xml' in response.data
    assert b'AuditFile' in response.data
    assert b'urn:OECD:StandardAuditFile-Tax:AO_1.05_01' in response.data


# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get('/api/health')
    
    assert response.status_code == 200
    result = json.loads(response.data)
    assert result['status'] == 'ok'
    assert result['version'] == '1.0'
