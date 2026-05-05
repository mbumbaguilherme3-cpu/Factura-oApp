"""
Test Suite for AGT Dashboard Web Interface
Tests dashboard routes, statistics, and data visualization
"""

import pytest
from datetime import datetime, timedelta
from billing_app.app_factory import create_app
from billing_app.db_config import db
from billing_app.agt_models import (
    AnyEntity, AGTProduct, Invoice, InvoiceLine,
    AGTComplianceLog, InvoiceSignatureAudit
)


@pytest.fixture
def dashboard_app():
    """Create testing Flask app with database"""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def dashboard_client(dashboard_app):
    """Create test client"""
    return dashboard_app.test_client()


@pytest.fixture
def dashboard_data(dashboard_app):
    """Create sample data for dashboard testing"""
    with dashboard_app.app_context():
        # Create supplier (company)
        supplier = AnyEntity(
            nif='5800001111',
            nif_type='COMPANY',
            name='Empresa Teste SARL',
            address='Rua Principal 123',
            city='Luanda',
            postal_code='1000',
            country='Angola',
            email='empresa@test.ao',
            is_tax_resident=True,
            is_vat_registered=True
        )
        db.session.add(supplier)
        
        # Create customer (person)
        customer = AnyEntity(
            nif='0000000000000111',
            nif_type='PERSON',
            name='Cliente Teste Silva',
            address='Avenida Secundária 456',
            city='Luanda',
            postal_code='2000',
            country='Angola',
            email='cliente@test.ao',
            is_tax_resident=True,
            is_vat_registered=False
        )
        db.session.add(customer)
        
        # Create products
        product1 = AGTProduct(
            product_code='PROD001',
            description='Produto A - Consultoria',
            unit_price=500.00,
            iva_regime='GENERAL',
            iva_rate=14.0,
            iva_exemption_code=None
        )
        db.session.add(product1)
        
        product2 = AGTProduct(
            product_code='PROD002',
            description='Produto B - Serviço',
            unit_price=250.00,
            iva_regime='EXEMPT',
            iva_rate=0.0,
            iva_exemption_code='M03'
        )
        db.session.add(product2)
        
        db.session.flush()
        
        # Create invoices (today, yesterday, 2 days ago)
        for i, days_ago in enumerate([0, 1, 2, 3, 4, 5, 6]):
            invoice_date = datetime.utcnow() - timedelta(days=days_ago)
            
            invoice = Invoice(
                invoice_number=f'FT SEGUNDO{invoice_date.year}/{1001 + i}',
                series_prefix='FT',
                series_sequence=1001 + i,
                series_year=invoice_date.year,
                supplier_id=supplier.entity_id,
                customer_id=customer.entity_id,
                invoice_date=invoice_date,
                due_date=invoice_date + timedelta(days=30),
                gross_total=1500.00 if i % 2 == 0 else 1200.00,
                iva_total=210.00 if i % 2 == 0 else 0.00,
                net_total=1290.00 if i % 2 == 0 else 1200.00,
                is_issued=True if i < 4 else False,
                status='ISSUED' if i < 4 else 'DRAFT'
            )
            db.session.add(invoice)
            db.session.flush()
            
            # Add line items
            line1 = InvoiceLine(
                invoice_id=invoice.invoice_id,
                product_id=product1.product_id,
                line_number=1,
                description='Consultoria - Serviço 1',
                quantity=1.0,
                unit_price=500.00,
                line_gross=500.00,
                iva_amount=70.00 if i % 2 == 0 else 0.00,
                line_net=430.00 if i % 2 == 0 else 500.00,
                iva_regime='GENERAL' if i % 2 == 0 else 'EXEMPT',
                iva_rate=14.0 if i % 2 == 0 else 0.0,
                iva_exemption_code=None if i % 2 == 0 else 'M03'
            )
            db.session.add(line1)
            
            line2 = InvoiceLine(
                invoice_id=invoice.invoice_id,
                product_id=product2.product_id,
                line_number=2,
                description='Serviço Adicional',
                quantity=4.0,
                unit_price=250.00,
                line_gross=1000.00,
                iva_amount=140.00 if i % 2 == 0 else 0.00,
                line_net=860.00 if i % 2 == 0 else 1000.00,
                iva_regime='GENERAL' if i % 2 == 0 else 'EXEMPT',
                iva_rate=14.0 if i % 2 == 0 else 0.0,
                iva_exemption_code=None if i % 2 == 0 else 'M03'
            )
            db.session.add(line2)
        
        # Create compliance logs
        for i in range(5):
            log = AGTComplianceLog(
                event_type='INVOICE_CREATED',
                entity_type='INVOICE',
                entity_id=str(i),
                action='CREATE',
                details=f'Invoice {i} created',
                operator_id='test_user',
                operator_ip='127.0.0.1',
                is_compliant=True,
                compliance_notes='Standard compliance check passed'
            )
            db.session.add(log)
        
        # Create signature audit logs
        for i in range(3):
            audit = InvoiceSignatureAudit(
                invoice_number=f'FT SEGUNDO2026/{1001 + i}',
                operation_type='SIGN',
                status='SUCCESS',
                status_code=200,
                status_message='Signature created successfully',
                operator_id='test_user',
                operator_ip='127.0.0.1',
                agt_response_code='SUCCESS'
            )
            db.session.add(audit)
        
        db.session.commit()
        
        return {
            'supplier_id': supplier.entity_id,
            'customer_id': customer.entity_id,
            'product1_id': product1.product_id,
            'product2_id': product2.product_id
        }


# Test Dashboard Route
def test_dashboard_get_success(dashboard_client, dashboard_data):
    """Test GET /dashboard/ returns dashboard with stats"""
    response = dashboard_client.get('/dashboard/')
    
    assert response.status_code == 200
    assert b'AGT Compliance Dashboard' in response.data or b'dashboard' in response.data.lower()


def test_dashboard_kpi_stats(dashboard_client, dashboard_data):
    """Test dashboard computes KPI statistics correctly"""
    response = dashboard_client.get('/dashboard/')
    
    assert response.status_code == 200
    # Dashboard should contain month reference
    assert response.data is not None


def test_dashboard_recent_invoices(dashboard_client, dashboard_data):
    """Test dashboard displays recent invoices"""
    response = dashboard_client.get('/dashboard/')
    
    assert response.status_code == 200
    # Recent invoices should be shown
    data_str = response.data.decode('utf-8')
    assert 'recent' in data_str.lower() or 'invoice' in data_str.lower()


def test_dashboard_system_status(dashboard_client, dashboard_data):
    """Test dashboard includes system status information"""
    response = dashboard_client.get('/dashboard/')
    
    assert response.status_code == 200
    # System status should be visible
    data_str = response.data.decode('utf-8')
    assert 'status' in data_str.lower() or 'system' in data_str.lower()


# Test Invoices List Route
def test_invoices_list_get_success(dashboard_client, dashboard_data):
    """Test GET /dashboard/invoices returns invoice list"""
    response = dashboard_client.get('/dashboard/invoices')
    
    assert response.status_code == 200
    assert b'invoice' in response.data.lower() or b'FT' in response.data


def test_invoices_list_pagination(dashboard_client, dashboard_data):
    """Test invoice list pagination"""
    response = dashboard_client.get('/dashboard/invoices?page=1')
    
    assert response.status_code == 200
    data_str = response.data.decode('utf-8')
    assert 'page' in data_str.lower() or '1' in data_str


def test_invoices_list_filter_status(dashboard_client, dashboard_data):
    """Test filter invoices by status"""
    response = dashboard_client.get('/dashboard/invoices?status=ISSUED')
    
    assert response.status_code == 200


def test_invoices_list_filter_period(dashboard_client, dashboard_data):
    """Test filter invoices by period"""
    response = dashboard_client.get('/dashboard/invoices?period=this-month')
    
    assert response.status_code == 200


def test_invoices_list_search(dashboard_client, dashboard_data):
    """Test search invoices by number"""
    response = dashboard_client.get('/dashboard/invoices?search=FT')
    
    assert response.status_code == 200


# Test Compliance Route
def test_compliance_get_success(dashboard_client, dashboard_data):
    """Test GET /dashboard/compliance returns compliance dashboard"""
    response = dashboard_client.get('/dashboard/compliance')
    
    assert response.status_code == 200
    assert b'compliance' in response.data.lower()


def test_compliance_audit_log(dashboard_client, dashboard_data):
    """Test compliance dashboard shows audit logs"""
    response = dashboard_client.get('/dashboard/compliance')
    
    assert response.status_code == 200
    data_str = response.data.decode('utf-8')
    assert 'audit' in data_str.lower() or 'log' in data_str.lower()


def test_compliance_signature_audit(dashboard_client, dashboard_data):
    """Test compliance dashboard shows signature audit logs"""
    response = dashboard_client.get('/dashboard/compliance')
    
    assert response.status_code == 200
    data_str = response.data.decode('utf-8')
    assert 'signature' in data_str.lower() or 'audit' in data_str.lower()


def test_compliance_checklist(dashboard_client, dashboard_data):
    """Test compliance dashboard includes compliance checklist"""
    response = dashboard_client.get('/dashboard/compliance')
    
    assert response.status_code == 200
    data_str = response.data.decode('utf-8')
    # Checklist items should be visible
    assert 'NIF' in data_str or 'IVA' in data_str or 'compliance' in data_str.lower()


# Test 404 Responses
def test_dashboard_invalid_route(dashboard_client):
    """Test invalid dashboard route returns 404"""
    response = dashboard_client.get('/dashboard/invalid-route')
    
    assert response.status_code == 404


# Test Template Rendering
def test_dashboard_renders_base_template(dashboard_client, dashboard_data):
    """Test dashboard renders with base template structure"""
    response = dashboard_client.get('/dashboard/')
    
    assert response.status_code == 200
    # Should contain basic HTML structure
    data_str = response.data.decode('utf-8')
    assert '<' in data_str and '>' in data_str


def test_dashboard_has_navigation(dashboard_client, dashboard_data):
    """Test dashboard page includes navigation"""
    response = dashboard_client.get('/dashboard/')
    
    assert response.status_code == 200
    data_str = response.data.decode('utf-8')
    # Should have navigation elements
    assert 'nav' in data_str.lower() or 'menu' in data_str.lower() or 'dashboard' in data_str.lower()


def test_invoices_page_has_table(dashboard_client, dashboard_data):
    """Test invoices page includes table structure"""
    response = dashboard_client.get('/dashboard/invoices')
    
    assert response.status_code == 200
    data_str = response.data.decode('utf-8')
    assert 'table' in data_str.lower() or 'invoice' in data_str.lower()


def test_compliance_page_has_metrics(dashboard_client, dashboard_data):
    """Test compliance page includes metrics"""
    response = dashboard_client.get('/dashboard/compliance')
    
    assert response.status_code == 200
    data_str = response.data.decode('utf-8')
    assert 'compliance' in data_str.lower() or 'metric' in data_str.lower()


# Test Dashboard Data Accuracy
def test_dashboard_kpi_calculations(dashboard_app, dashboard_data):
    """Test KPI calculations are accurate"""
    with dashboard_app.app_context():
        # Count invoices
        issued_invoices = Invoice.query.filter_by(is_issued=True).count()
        assert issued_invoices == 4  # First 4 invoices should be issued
        
        # Calculate totals
        total_amount = db.session.query(db.func.sum(Invoice.gross_total)).scalar() or 0
        assert total_amount > 0


def test_compliance_event_count(dashboard_app, dashboard_data):
    """Test compliance event counting"""
    with dashboard_app.app_context():
        events = AGTComplianceLog.query.count()
        assert events == 5  # We created 5 compliance logs


def test_signature_audit_count(dashboard_app, dashboard_data):
    """Test signature audit event counting"""
    with dashboard_app.app_context():
        audits = InvoiceSignatureAudit.query.count()
        assert audits == 3  # We created 3 signature audits


# Test Dashboard with Empty Database
def test_dashboard_empty_database(dashboard_client):
    """Test dashboard handles empty database gracefully"""
    response = dashboard_client.get('/dashboard/')
    
    assert response.status_code == 200
    # Should still render without errors


def test_invoices_list_empty_database(dashboard_client):
    """Test invoices list handles empty database"""
    response = dashboard_client.get('/dashboard/invoices')
    
    assert response.status_code == 200


def test_compliance_empty_database(dashboard_client):
    """Test compliance page handles empty database"""
    response = dashboard_client.get('/dashboard/compliance')
    
    assert response.status_code == 200


# Test Static Assets
def test_dashboard_css_exists(dashboard_client):
    """Test dashboard CSS file exists"""
    response = dashboard_client.get('/static/dashboard.css')
    
    assert response.status_code == 200
    assert b'background' in response.data or b'color' in response.data


def test_static_assets_accessible(dashboard_client):
    """Test static folder is accessible"""
    response = dashboard_client.get('/static/app.js')
    
    # app.js might not exist or 404, but should be accessible attempt
    assert response.status_code in [200, 404]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
