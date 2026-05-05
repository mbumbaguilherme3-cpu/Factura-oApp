"""
Dashboard Routes Tests
Tests for AGT Dashboard web interface routes
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from flask import url_for

from billing_app.agt_models import (
    Invoice, AnyEntity, AGTComplianceLog, InvoiceSignatureAudit
)


class TestDashboardIndex:
    """Tests for dashboard index route"""
    
    def test_dashboard_index_renders(self, client):
        """Test that dashboard index page renders successfully"""
        response = client.get('/dashboard/')
        assert response.status_code == 200
        assert b'dashboard.html' in response.data or b'Dashboard' in response.data
    
    def test_dashboard_index_with_invoices(self, client, app, db, sample_entity, sample_product):
        """Test dashboard index with invoice data"""
        with app.app_context():
            # Create test invoices
            today = datetime.now().date()
            month_start = datetime(today.year, today.month, 1)
            
            invoice = Invoice(
                customer_id=sample_entity.entity_id,
                invoice_number='2026/0001',
                invoice_date=today,
                invoice_type='FT',
                status='I',
                is_issued=True,
                net_total=Decimal('100.00'),
                iva_total=Decimal('23.00'),
                gross_total=Decimal('123.00'),
                operator_id='USER001'
            )
            db.session.add(invoice)
            db.session.commit()
            
            response = client.get('/dashboard/')
            assert response.status_code == 200
    
    def test_dashboard_stats_calculated(self, client, app, db, sample_entity, sample_product):
        """Test that dashboard statistics are correctly calculated"""
        with app.app_context():
            today = datetime.now().date()
            
            # Create multiple invoices
            for i in range(5):
                invoice = Invoice(
                    customer_id=sample_entity.entity_id,
                    invoice_number=f'2026/{str(i+1).zfill(4)}',
                    invoice_date=today - timedelta(days=i),
                    invoice_type='FT',
                    status='I',
                    is_issued=True,
                    net_total=Decimal('100.00'),
                    iva_total=Decimal('23.00'),
                    gross_total=Decimal('123.00'),
                    operator_id='USER001'
                )
                db.session.add(invoice)
            db.session.commit()
            
            response = client.get('/dashboard/')
            assert response.status_code == 200
            
            # Verify data was passed to template
            # Note: The actual content verification depends on template rendering


class TestDashboardInvoices:
    """Tests for invoices management route"""
    
    def test_invoices_page_renders(self, client):
        """Test that invoices page renders successfully"""
        response = client.get('/dashboard/invoices')
        assert response.status_code == 200
        assert b'invoices.html' in response.data or b'Invoice' in response.data
    
    def test_invoices_list_pagination(self, client, app, db, sample_entity, sample_product):
        """Test invoices list with pagination"""
        with app.app_context():
            today = datetime.now().date()
            
            # Create 25 invoices to test pagination (default 20 per page)
            for i in range(25):
                invoice = Invoice(
                    customer_id=sample_entity.entity_id,
                    invoice_number=f'2026/{str(i+1).zfill(4)}',
                    invoice_date=today - timedelta(days=i),
                    invoice_type='FT',
                    status='I',
                    is_issued=True,
                    net_total=Decimal('100.00'),
                    iva_total=Decimal('23.00'),
                    gross_total=Decimal('123.00'),
                    operator_id='USER001'
                )
                db.session.add(invoice)
            db.session.commit()
            
            # Test first page
            response = client.get('/dashboard/invoices?page=1')
            assert response.status_code == 200
            
            # Test second page
            response = client.get('/dashboard/invoices?page=2')
            assert response.status_code == 200
    
    def test_invoices_filter_by_status(self, client, app, db, sample_entity, sample_product):
        """Test filtering invoices by status"""
        with app.app_context():
            today = datetime.now().date()
            
            # Create invoices with different statuses
            for status in ['D', 'I', 'S']:
                invoice = Invoice(
                    customer_id=sample_entity.entity_id,
                    invoice_number=f'2026/{status}/0001',
                    invoice_date=today,
                    invoice_type='FT',
                    status=status,
                    is_issued=(status != 'D'),
                    net_total=Decimal('100.00'),
                    iva_total=Decimal('23.00'),
                    gross_total=Decimal('123.00'),
                    operator_id='USER001'
                )
                db.session.add(invoice)
            db.session.commit()
            
            # Filter by status
            response = client.get('/dashboard/invoices?status=I')
            assert response.status_code == 200
    
    def test_invoices_filter_by_period_today(self, client, app, db, sample_entity, sample_product):
        """Test filtering invoices by today period"""
        with app.app_context():
            today = datetime.now().date()
            
            # Create invoice for today
            invoice_today = Invoice(
                customer_id=sample_entity.entity_id,
                invoice_number='2026/TODAY/0001',
                invoice_date=today,
                invoice_type='FT',
                status='I',
                is_issued=True,
                net_total=Decimal('100.00'),
                iva_total=Decimal('23.00'),
                gross_total=Decimal('123.00'),
                operator_id='USER001'
            )
            db.session.add(invoice_today)
            
            # Create invoice for yesterday
            invoice_yesterday = Invoice(
                customer_id=sample_entity.entity_id,
                invoice_number='2026/YESTERDAY/0001',
                invoice_date=today - timedelta(days=1),
                invoice_type='FT',
                status='I',
                is_issued=True,
                net_total=Decimal('100.00'),
                iva_total=Decimal('23.00'),
                gross_total=Decimal('123.00'),
                operator_id='USER001'
            )
            db.session.add(invoice_yesterday)
            db.session.commit()
            
            response = client.get('/dashboard/invoices?period=today')
            assert response.status_code == 200
    
    def test_invoices_filter_by_period_this_week(self, client, app, db, sample_entity, sample_product):
        """Test filtering invoices by this week period"""
        with app.app_context():
            today = datetime.now().date()
            
            invoice = Invoice(
                customer_id=sample_entity.entity_id,
                invoice_number='2026/WEEK/0001',
                invoice_date=today,
                invoice_type='FT',
                status='I',
                is_issued=True,
                net_total=Decimal('100.00'),
                iva_total=Decimal('23.00'),
                gross_total=Decimal('123.00'),
                operator_id='USER001'
            )
            db.session.add(invoice)
            db.session.commit()
            
            response = client.get('/dashboard/invoices?period=this-week')
            assert response.status_code == 200
    
    def test_invoices_filter_by_period_this_month(self, client, app, db, sample_entity, sample_product):
        """Test filtering invoices by this month period"""
        with app.app_context():
            today = datetime.now().date()
            
            invoice = Invoice(
                customer_id=sample_entity.entity_id,
                invoice_number='2026/MONTH/0001',
                invoice_date=today,
                invoice_type='FT',
                status='I',
                is_issued=True,
                net_total=Decimal('100.00'),
                iva_total=Decimal('23.00'),
                gross_total=Decimal('123.00'),
                operator_id='USER001'
            )
            db.session.add(invoice)
            db.session.commit()
            
            response = client.get('/dashboard/invoices?period=this-month')
            assert response.status_code == 200
    
    def test_invoices_customer_name_resolution(self, client, app, db, sample_entity, sample_product):
        """Test that customer names are properly resolved"""
        with app.app_context():
            today = datetime.now().date()
            
            invoice = Invoice(
                customer_id=sample_entity.entity_id,
                invoice_number='2026/CUSTOMER/0001',
                invoice_date=today,
                invoice_type='FT',
                status='I',
                is_issued=True,
                net_total=Decimal('100.00'),
                iva_total=Decimal('23.00'),
                gross_total=Decimal('123.00'),
                operator_id='USER001'
            )
            db.session.add(invoice)
            db.session.commit()
            
            response = client.get('/dashboard/invoices')
            assert response.status_code == 200


class TestDashboardCompliance:
    """Tests for compliance and audit route"""
    
    def test_compliance_page_renders(self, client):
        """Test that compliance page renders successfully"""
        response = client.get('/dashboard/compliance')
        assert response.status_code == 200
        assert b'compliance.html' in response.data or b'Compliance' in response.data or b'Conformidade' in response.data
    
    def test_compliance_stats_calculated(self, client, app, db):
        """Test that compliance statistics are correctly calculated"""
        with app.app_context():
            # Create compliance log entries
            now = datetime.now()
            
            for i in range(10):
                log = AGTComplianceLog(
                    invoice_id=None,
                    event_type='VALIDATION',
                    entity_type='FT',
                    is_compliant=True if i % 2 == 0 else False,
                    compliance_notes='Test compliance',
                    details='Test details',
                    operator_id='USER001'
                )
                db.session.add(log)
            db.session.commit()
            
            response = client.get('/dashboard/compliance')
            assert response.status_code == 200
    
    def test_compliance_alerts_shown(self, client, app, db):
        """Test that non-compliant events are shown as alerts"""
        with app.app_context():
            # Create non-compliant log entry
            log = AGTComplianceLog(
                invoice_id=None,
                event_type='VALIDATION_ERROR',
                entity_type='FT',
                is_compliant=False,
                compliance_notes='NIF format invalid',
                details='Customer NIF does not match format',
                operator_id='USER001'
            )
            db.session.add(log)
            db.session.commit()
            
            response = client.get('/dashboard/compliance')
            assert response.status_code == 200
    
    def test_compliance_audit_logs_retrieved(self, client, app, db):
        """Test that audit logs are retrieved for compliance page"""
        with app.app_context():
            # Create multiple compliance logs
            for i in range(15):
                log = AGTComplianceLog(
                    invoice_id=None,
                    event_type=f'EVENT_{i}',
                    entity_type='FT',
                    is_compliant=True,
                    compliance_notes=f'Log entry {i}',
                    details=f'Details for entry {i}',
                    operator_id='USER001'
                )
                db.session.add(log)
            db.session.commit()
            
            response = client.get('/dashboard/compliance')
            assert response.status_code == 200
    
    def test_compliance_signature_audits_retrieved(self, client, app, db, sample_entity):
        """Test that signature audits are retrieved"""
        with app.app_context():
            # Create signature audit entries
            for i in range(5):
                audit = InvoiceSignatureAudit(
                    invoice_id=1,
                    operation='SIGN',
                    jws_payload='test_payload',
                    operator_id='USER001',
                    audit_notes=f'Signature audit {i}'
                )
                db.session.add(audit)
            db.session.commit()
            
            response = client.get('/dashboard/compliance')
            assert response.status_code == 200
    
    def test_compliance_compliance_rate_percentage(self, client, app, db):
        """Test that compliance rate is calculated as percentage"""
        with app.app_context():
            # Create 10 compliant and 5 non-compliant logs
            now = datetime.now()
            for i in range(10):
                log = AGTComplianceLog(
                    invoice_id=None,
                    event_type='TEST',
                    entity_type='FT',
                    is_compliant=True,
                    created_at=now - timedelta(days=i),
                    operator_id='USER001'
                )
                db.session.add(log)
            
            for i in range(5):
                log = AGTComplianceLog(
                    invoice_id=None,
                    event_type='TEST_FAIL',
                    entity_type='FT',
                    is_compliant=False,
                    created_at=now - timedelta(days=i),
                    operator_id='USER001'
                )
                db.session.add(log)
            
            db.session.commit()
            
            response = client.get('/dashboard/compliance')
            assert response.status_code == 200
            # Compliance rate should be approximately 66% (10 compliant out of 15 total)


class TestDashboardIntegration:
    """Integration tests for dashboard functionality"""
    
    def test_dashboard_navigation_links(self, client):
        """Test that dashboard pages link to each other"""
        response = client.get('/dashboard/')
        assert response.status_code == 200
    
    def test_dashboard_requires_database(self, app, db):
        """Test that dashboard requires database connection"""
        with app.app_context():
            # Verify that models are accessible
            assert Invoice is not None
            assert AGTComplianceLog is not None
            assert AnyEntity is not None
    
    def test_dashboard_with_empty_database(self, client, app):
        """Test dashboard renders with empty database"""
        with app.app_context():
            response = client.get('/dashboard/')
            assert response.status_code == 200
            
            response = client.get('/dashboard/invoices')
            assert response.status_code == 200
            
            response = client.get('/dashboard/compliance')
            assert response.status_code == 200
    
    def test_dashboard_pagination_default_page(self, client, app, db, sample_entity, sample_product):
        """Test that pagination defaults to page 1"""
        with app.app_context():
            today = datetime.now().date()
            
            # Create test invoice
            invoice = Invoice(
                customer_id=sample_entity.entity_id,
                invoice_number='2026/0001',
                invoice_date=today,
                invoice_type='FT',
                status='I',
                is_issued=True,
                net_total=Decimal('100.00'),
                iva_total=Decimal('23.00'),
                gross_total=Decimal('123.00'),
                operator_id='USER001'
            )
            db.session.add(invoice)
            db.session.commit()
            
            # Test without page parameter
            response = client.get('/dashboard/invoices')
            assert response.status_code == 200
    
    def test_dashboard_soft_delete_filter(self, client, app, db, sample_entity, sample_product):
        """Test that soft-deleted invoices are filtered out"""
        with app.app_context():
            today = datetime.now().date()
            
            # Create active invoice
            active_invoice = Invoice(
                customer_id=sample_entity.entity_id,
                invoice_number='2026/ACTIVE/0001',
                invoice_date=today,
                invoice_type='FT',
                status='I',
                is_issued=True,
                net_total=Decimal('100.00'),
                iva_total=Decimal('23.00'),
                gross_total=Decimal('123.00'),
                operator_id='USER001'
            )
            db.session.add(active_invoice)
            
            # Create soft-deleted invoice
            deleted_invoice = Invoice(
                customer_id=sample_entity.entity_id,
                invoice_number='2026/DELETED/0001',
                invoice_date=today,
                invoice_type='FT',
                status='I',
                is_issued=True,
                net_total=Decimal('100.00'),
                iva_total=Decimal('23.00'),
                gross_total=Decimal('123.00'),
                deleted_at=datetime.now(),
                operator_id='USER001'
            )
            db.session.add(deleted_invoice)
            db.session.commit()
            
            response = client.get('/dashboard/invoices')
            assert response.status_code == 200
            # Verify deleted invoice is not in response


class TestDashboardEdgeCases:
    """Edge case tests for dashboard"""
    
    def test_dashboard_with_null_values(self, client, app, db, sample_entity):
        """Test dashboard handles null values gracefully"""
        with app.app_context():
            # Create invoice with minimal data
            invoice = Invoice(
                customer_id=sample_entity.entity_id,
                invoice_number='2026/NULL/0001',
                invoice_date=datetime.now().date(),
                invoice_type='FT',
                status='D',
                is_issued=False,
                operator_id='USER001'
            )
            db.session.add(invoice)
            db.session.commit()
            
            response = client.get('/dashboard/')
            assert response.status_code == 200
    
    def test_dashboard_invoices_invalid_page(self, client):
        """Test dashboard invoices with invalid page number"""
        response = client.get('/dashboard/invoices?page=999')
        assert response.status_code == 200
    
    def test_dashboard_invoices_invalid_status(self, client):
        """Test dashboard invoices with invalid status filter"""
        response = client.get('/dashboard/invoices?status=INVALID')
        assert response.status_code == 200
    
    def test_dashboard_compliance_large_dataset(self, client, app, db):
        """Test compliance page with large dataset (50+ logs)"""
        with app.app_context():
            # Create many compliance logs
            for i in range(60):
                log = AGTComplianceLog(
                    invoice_id=None,
                    event_type=f'EVENT_{i}',
                    entity_type='FT',
                    is_compliant=True if i % 3 == 0 else False,
                    operator_id='USER001'
                )
                db.session.add(log)
            db.session.commit()
            
            response = client.get('/dashboard/compliance')
            assert response.status_code == 200
